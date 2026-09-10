#!/usr/bin/env bash
# Red Gate verifier harness. Exit: 0 all checkable green; 1 any FAIL (red);
# 99 FAULT: the harness itself broke (preflight dirty / internal error) — never red.
# Each check_cmd runs under timeout, stdin closed, output teed to
# evidence/<n>.out. A check_cmd exiting non-zero for ANY reason (127
# included) is a FAIL — only the harness's own breakage is exit 99.
set -u
cd "$(dirname "$0")"

# ---- preflight: HARNESS prerequisites only; never the subject under test ----
for bin in bash grep sed; do
  command -v "$bin" >/dev/null 2>&1 || { echo "FAULT: missing $bin" >&2; exit 99; }
done
# timeout is GNU coreutils; stock macOS has neither `timeout` nor `gtimeout`
# unless coreutils is installed. Use whichever exists, else run uncapped rather
# than declaring a FAULT — a missing convenience is not a broken harness.
if command -v timeout >/dev/null 2>&1; then RG_TIMEOUT="timeout 120"
elif command -v gtimeout >/dev/null 2>&1; then RG_TIMEOUT="gtimeout 120"
else RG_TIMEOUT=""; fi
[ -d evidence ] && [ -w evidence ] || { echo "FAULT: evidence/ not writable" >&2; exit 99; }
[ -f CRITERIA.md ] || { echo "FAULT: CRITERIA.md missing" >&2; exit 99; }

fails=0; checked=0
n=0
# `|| [ -n "$line" ]` is load-bearing: without it a final line with no trailing
# newline is silently DROPPED, so a failing criterion written last simply
# vanishes and the gate reports green. That defeats the whole invariant.
while IFS= read -r line || [ -n "$line" ]; do
  case "$line" in
    "## #"*) n=$(printf '%s' "$line" | sed 's/^## #\([0-9]*\).*/\1/') ;;
    "check_cmd: "*)
      cmd=${line#check_cmd: }
      checked=$((checked+1))
      if $RG_TIMEOUT bash -c "$cmd" </dev/null >"evidence/$n.out" 2>&1; then
        echo "#$n PASS"
      else
        echo "#$n FAIL"; fails=$((fails+1))
      fi ;;
    "WITNESS:"*|"UNVERIFIABLE:"*) echo "#$n WITNESS" ;;
  esac
done < CRITERIA.md

[ "$checked" -gt 0 ] || { echo "FAULT: no checkable criteria parsed" >&2; exit 99; }
[ "$fails" -eq 0 ] && exit 0 || exit 1
