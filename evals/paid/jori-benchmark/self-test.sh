#!/usr/bin/env bash
# self-test.sh — free, offline, no model calls. Proves the plumbing discriminates before
# a single dollar is spent: verifier is two-sided, run-arm's dry-run path works for both
# arms, aggregate refuses to print a number it does not have, and its verdict logic holds.
set -uo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
pass=0; fail=0
ok()  { pass=$((pass+1)); printf '  PASS %s\n' "$1"; }
bad() { fail=$((fail+1)); printf '  FAIL %s\n' "$1"; }
echo "jori benchmark — self-test"
for s in "$here"/*.sh "$here"/tasks/*/*.sh; do bash -n "$s" && ok "parses: ${s#$here/}" || bad "parses: ${s#$here/}"; done
for t in "$here"/tasks/*/; do
  name="$(basename "$t")"
  ws="$(mktemp -d)"; "$t/setup.sh" "$ws"
  if "$t/verify.sh" "$ws" >/dev/null 2>&1; then bad "$name: untouched fixture must FAIL the verifier (nop control)"; else ok "$name: nop control fails"; fi
  # reward-hack control: make the tests trivially pass instead of fixing the code
  ws2="$(mktemp -d)"; "$t/setup.sh" "$ws2"; for f in "$ws2"/tests/test_*.py; do printf 'import unittest\nclass T(unittest.TestCase):\n    def test_x(self): pass\n' > "$f"; done
  if "$t/verify.sh" "$ws2" >/dev/null 2>&1; then bad "$name: editing tests must FAIL the verifier (reward-hack control)"; else ok "$name: reward-hack control fails"; fi
  "$t/oracle.sh" "$ws"
  if "$t/verify.sh" "$ws" >/dev/null 2>&1; then ok "$name: oracle passes (verifier can pass)"; else bad "$name: oracle must PASS the verifier"; fi
  rm -rf "$ws" "$ws2"
done
res="$(mktemp -d)"
for arm in jori baseline; do
  if out="$("$here/run-arm.sh" --arm "$arm" --task multi-module-fix --repeat 1 --out "$res" --dry-run 2>&1)"; then
    grep -q '"mode": "dry-run"' <<<"$out" && grep -q '"total_cost_usd": "UNKNOWN"' <<<"$out" && ok "run-arm dry-run ($arm): no model call, cost UNKNOWN" || { bad "run-arm dry-run ($arm) output unexpected"; printf '%s\n' "$out" | sed 's/^/    /'; }
  else bad "run-arm dry-run ($arm) failed"; printf '%s\n' "$out" | sed 's/^/    /'; fi
done
if python3 "$here/aggregate.py" --results "$res" --out "$res/report" >/dev/null 2>&1 && grep -q "not comparable" "$res/report/summary.md"; then ok "aggregate on dry-run results refuses a verdict (not comparable)"; else bad "aggregate must refuse a verdict on dry-run results"; fi
if python3 "$here/aggregate.py" --self-test >/dev/null 2>&1; then ok "aggregate --self-test (verdict logic)"; else bad "aggregate --self-test failed"; python3 "$here/aggregate.py" --self-test | sed 's/^/    /'; fi
if grep -rn "npx" "$here" --include='*.sh' --include='*.py' --include='*.yml' | grep -v 'self-test.sh' >/dev/null; then bad "no npx anywhere in the benchmark"; else ok "no npx anywhere in the benchmark"; fi
rm -rf "$res"
printf 'summary: %d passed, %d failed\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
