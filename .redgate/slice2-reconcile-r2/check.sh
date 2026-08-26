#!/usr/bin/env bash
# Red Gate verifier harness. Exit: 0 all checkable green; 1 any FAIL (red);
# 99 harness failure (preflight dirty / internal error) — 99 is NOT red.
# Each check_cmd runs under timeout, stdin closed, output teed to
# evidence/<n>.out. A check_cmd exiting non-zero for ANY reason (127
# included) is a FAIL — only the harness's own breakage is exit 99.
set -u
cd "$(dirname "$0")"

# ---- preflight: HARNESS prerequisites only; never the subject under test ----
for bin in bash timeout tee sha256sum grep sed; do
  command -v "$bin" >/dev/null 2>&1 || { echo "HARNESS-ERROR: missing $bin" >&2; exit 99; }
done
[ -d evidence ] && [ -w evidence ] || { echo "HARNESS-ERROR: evidence/ not writable" >&2; exit 99; }
[ -f CRITERIA.md ] || { echo "HARNESS-ERROR: CRITERIA.md missing" >&2; exit 99; }

fails=0; checked=0
n=0
while IFS= read -r line; do
  case "$line" in
    "## #"*) n=$(printf '%s' "$line" | sed 's/^## #\([0-9]*\).*/\1/') ;;
    "check_cmd: "*)
      cmd=${line#check_cmd: }
      checked=$((checked+1))
      if timeout 120 bash -c "$cmd" </dev/null >"evidence/$n.out" 2>&1; then
        echo "#$n PASS"
      else
        echo "#$n FAIL"; fails=$((fails+1))
      fi ;;
    "UNVERIFIABLE:"*) echo "#$n UNVERIFIABLE" ;;
  esac
done < CRITERIA.md

[ "$checked" -gt 0 ] || { echo "HARNESS-ERROR: no checkable criteria parsed" >&2; exit 99; }
[ "$fails" -eq 0 ] && exit 0 || exit 1
