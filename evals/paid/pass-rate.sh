#!/usr/bin/env bash
#
# pass-rate.sh RESULTS.json [--floor F] [--min-runs N] — statistical gate for a
# repeated promptfoo run.
#
# The behavioral tier runs each scenario ONCE, so a green is uninterpretable: a
# stochastic model that passes a scenario 55% of the time shows green or red on
# the flip of a coin, and any optimization loop built on that signal selects
# noise (gap #4, docs/research/gap-analysis.md). The fix is to run each scenario
# N times (promptfoo `repeat: N`) and require a per-scenario pass RATE at or above
# a floor — so a scenario that squeaked one lucky pass can no longer stay green.
#
# This script reads a promptfoo results.json in which each test appears N times
# (repeat expands each test into N result rows sharing the same description), and
# for EACH distinct scenario:
#   * counts runs and passes,
#   * FAILS the scenario if its pass rate < floor (default 0.8),
#   * FAILS the whole run if any scenario has fewer than --min-runs rows
#     (default 2 — a run that did not actually repeat is not a statistical
#     result and must not read as one; fail-closed, never a silent single-shot).
#
# Exit: 0 every scenario at/above floor with enough runs; 1 any scenario below
# floor or under-repeated; 2 usage / unreadable results.
#
# It reads the SAME result shape the behavioral job's jq already relies on
# (.results.results[].success + .description/.vars), so it stays valid as long as
# that shape does. Grouping key precedence: testCase.description, else description,
# else the request var — whatever is stable across a scenario's N repeats.
set -uo pipefail

FLOOR="0.8"; MIN_RUNS="2"; FILE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --floor)    FLOOR="${2:?}"; shift 2 ;;
    --min-runs) MIN_RUNS="${2:?}"; shift 2 ;;
    -*)         echo "pass-rate: unknown flag $1" >&2; exit 2 ;;
    *)          FILE="$1"; shift ;;
  esac
done
[ -n "$FILE" ] || { echo "usage: pass-rate.sh RESULTS.json [--floor F] [--min-runs N]" >&2; exit 2; }
[ -f "$FILE" ] || { echo "pass-rate: no such file: $FILE" >&2; exit 2; }

python3 - "$FILE" "$FLOOR" "$MIN_RUNS" <<'PY'
import json, sys
path, floor, min_runs = sys.argv[1], float(sys.argv[2]), int(sys.argv[3])
try:
    doc = json.load(open(path))
except Exception as e:
    print(f"pass-rate: cannot parse {path}: {e}", file=sys.stderr); sys.exit(2)

# The behavioral job already treats results as (.results.results // .results // []).
# `results` may be an object holding a `results` list (promptfoo's usual shape)
# or itself be the list — handle both without assuming a dict.
res = doc.get("results")
if isinstance(res, dict):
    rows = res.get("results") or []
elif isinstance(res, list):
    rows = res
else:
    rows = []
if not rows:
    print("pass-rate: no result rows found — the run produced nothing to score", file=sys.stderr)
    sys.exit(2)

def key(r):
    tc = r.get("testCase") or {}
    for cand in (tc.get("description"), r.get("description")):
        if cand:
            return str(cand)
    v = (r.get("vars") or {}) or (tc.get("vars") or {})
    return str(v.get("request") or v.get("question") or "<unlabeled>")

agg = {}
for r in rows:
    k = key(r)
    a = agg.setdefault(k, {"runs": 0, "pass": 0})
    a["runs"] += 1
    if r.get("success") is True:
        a["pass"] += 1

fail = 0
under = 0
print(f"pass-rate: floor={floor:.2f}  min-runs={min_runs}  scenarios={len(agg)}")
for k in sorted(agg):
    runs, passes = agg[k]["runs"], agg[k]["pass"]
    rate = passes / runs if runs else 0.0
    tag = "OK"
    if runs < min_runs:
        tag = "UNDER-REPEATED"; under += 1
    elif rate < floor:
        tag = "BELOW-FLOOR"; fail += 1
    print(f"  [{tag}] {passes}/{runs} = {rate:.2f}  {k[:90]}")

if under:
    print(f"pass-rate: FAIL — {under} scenario(s) ran fewer than {min_runs} times; this was not a repeated run (fail-closed)", file=sys.stderr)
    sys.exit(1)
if fail:
    print(f"pass-rate: FAIL — {fail} scenario(s) below the {floor:.2f} floor; a green here would be noise", file=sys.stderr)
    sys.exit(1)
print("pass-rate: PASS — every scenario at or above floor with enough runs")
PY
