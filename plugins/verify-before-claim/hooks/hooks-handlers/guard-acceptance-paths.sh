#!/usr/bin/env bash
#
# guard-acceptance-paths.sh — the out-of-bounds ledger, enforced.
#
# Reads a PreToolUse payload on stdin. Denies any write that targets a acceptance
# case's ratified contract (CRITERIA.md, check.sh, manifest) while that
# run's phase is TRACE (legacy: MIDDLE). Before ratification the contract is
# still being written, so ARM-phase writes are allowed.
#
# The rule it compiles: nothing a round can write may gate that round.
#
# PORTABILITY: hooks are Claude-Code-only. On another harness the same rule
# holds as prose discipline — this handler is enforcement, not the rule.
#
# Exit 0 allow · 2 deny (message on stderr).
set -u
payload="$(cat 2>/dev/null || true)"

path="$(printf '%s' "$payload" | python3 -c '
import json,sys
try: d=json.load(sys.stdin)
except Exception: print(""); raise SystemExit
print((d.get("tool_input") or {}).get("file_path") or "")
' 2>/dev/null || true)"

[ -n "$path" ] || exit 0
case "$path" in (*/.redgate/*) ;; (*) exit 0 ;; esac

run="${path%%/.redgate/*}/.redgate/$(printf '%s' "${path#*/.redgate/}" | cut -d/ -f1)"
[ -f "$run/manifest" ] || exit 0

phase="$(sed -n 's/^phase=//p' "$run/manifest" | head -1)"
case "$phase" in TRACE|MIDDLE) : ;; *) exit 0 ;; esac

case "${path##*/}" in
  CRITERIA.md|check.sh|manifest)
    echo "verification: DENY — $path belongs to a pinned acceptance contract while work is in progress." >&2
    echo "Return a changed requirement to the task owner for a new contract; never edit the pinned artifacts to pass." >&2
    exit 2 ;;
esac
exit 0
