#!/usr/bin/env bash
#
# Mutant of plugins/redgate/hooks/hooks-handlers/guard-redgate-paths.sh with
# the phase gate removed: it denies a write to CRITERIA.md/check.sh/manifest
# on PATH MATCH ALONE, regardless of phase.
#
# Negative control for T21's explicitly named failure mode: "A handler that
# denies on path match alone, ignoring phase and ratification — it would
# block legitimate ARM authoring." The real handler's "ARM-phase write is
# allowed" test only proves something if THIS mutant would get it wrong.
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

# MUTATION: the real handler checks `phase` here (TRACE|MIDDLE) before
# denying; this mutant skips straight to the filename check.
case "${path##*/}" in
  CRITERIA.md|check.sh|manifest)
    echo "mutant: DENY — $path (path match alone, phase not checked)" >&2
    exit 2 ;;
esac
exit 0
