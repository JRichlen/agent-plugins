#!/usr/bin/env bash
#
# pass-rate.sh RESULTS.json [--floor F] [--min-runs N] [--min-valid M] —
# statistical gate for a repeated promptfoo run.
#
# The behavioral tier runs each scenario ONCE, so a green is uninterpretable: a
# stochastic model that passes a scenario 55% of the time shows green or red on
# the flip of a coin, and any optimization loop built on that signal selects
# noise (gap #4, docs/research/gap-analysis.md). The fix is to run each scenario
# N times (promptfoo `repeat: N`) and require a per-scenario pass RATE at or above
# a floor — so a scenario that squeaked one lucky pass can no longer stay green.
#
# FAULTs are not failures. A promptfoo row can be red for two very different
# reasons: the grader judged the answer wrong (a real FAIL), or the subject-model
# CALL itself never completed — a 504, an aborted request, an empty/truncated
# body (a FAULT, in the redgate lexicon: a harness/transport error, not evidence
# about the skill). Counting a 504 as a FAIL is exactly the n=1 fragility this
# gate exists to remove: it makes a required check red on the weather. So this
# script classifies each row as PASS / FAIL / INVALID(FAULT) and scores the floor
# over VALID samples only (pass + fail), excluding FAULTs — while still failing
# CLOSED when a scenario produced too few valid samples to judge at all (an
# all-504 scenario is not "green", it is "never tested").
#
# For EACH distinct scenario it:
#   * counts runs, valid samples, passes, and FAULTs,
#   * FAILS the scenario if valid pass rate < floor (default 0.6 = majority of 3),
#   * FAILS the whole run if any scenario has fewer than --min-valid valid samples
#     (default 2) or fewer than --min-runs total rows (default 2) — either means
#     this was not a real repeated measurement and must not read as one.
#
# Exit: 0 every scenario at/above floor with enough valid samples; 1 any scenario
# below floor / under-repeated / starved of valid samples; 2 usage / unreadable.
#
# It reads the SAME result shape the behavioral job's jq already relies on
# (.results.results[].success + .description/.vars). FAULT classification keys
# on .failureReason — the reliable discriminator: 1/"assert" = assertion failure
# (a real FAIL, scored against the floor), 2/"error" = provider/transport error
# (a FAULT, excluded). .error ALONE marks a FAULT only when the row carries no
# failureReason at all (legacy shapes that predate the field): under promptfoo
# >= 0.122 EVERY assertion-failed row also carries .error (the assertion
# message), so .error must never override failureReason == 1 — doing so scored
# real failures as transport faults and let a failing run read green (fail-open).
# Grouping key precedence: testCase.description, else description, else the
# request var — whatever is stable across a scenario's N repeats.
set -uo pipefail

FLOOR="0.6"; MIN_RUNS="2"; MIN_VALID="2"; FILE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --floor)     FLOOR="${2:?}"; shift 2 ;;
    --min-runs)  MIN_RUNS="${2:?}"; shift 2 ;;
    --min-valid) MIN_VALID="${2:?}"; shift 2 ;;
    -*)          echo "pass-rate: unknown flag $1" >&2; exit 2 ;;
    *)           FILE="$1"; shift ;;
  esac
done
[ -n "$FILE" ] || { echo "usage: pass-rate.sh RESULTS.json [--floor F] [--min-runs N] [--min-valid M]" >&2; exit 2; }
[ -f "$FILE" ] || { echo "pass-rate: no such file: $FILE" >&2; exit 2; }

python3 - "$FILE" "$FLOOR" "$MIN_RUNS" "$MIN_VALID" <<'PY'
import json, sys, re
path, floor, min_runs, min_valid = sys.argv[1], float(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
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

def output_text(r):
    resp = r.get("response") or {}
    out = resp.get("output")
    if out is None:
        out = r.get("output")
    if out is None:
        return ""
    return out if isinstance(out, str) else json.dumps(out)

# A row is a FAULT (INVALID sample) when the model CALL did not yield a usable
# answer — not when the grader disliked a real answer. .failureReason is the
# discriminator (promptfoo enum: 0 none, 1 assertion failed, 2 error):
#   * .failureReason == 2 or "error" — a provider/transport error (504, aborted
#     request): FAULT;
#   * .failureReason == 1 or "assert" — the grader judged a real answer wrong:
#     a REAL FAIL, scored against the floor. Under promptfoo >= 0.122 these rows
#     ALSO carry .error (the assertion message), so .error must never promote
#     them to FAULT — that scored real failures as weather and let a failing run
#     read green (fail-open, the dangerous direction; observed on PR #93);
#   * .error set with NO failureReason recorded — legacy fallback for result
#     shapes that predate the field: FAULT;
#   * the row did not pass AND its body is nothing but repeated <think>/</think>
#     control tokens (the truncation-degeneracy we actually observed, gap #4
#     evidence table) — a 200 that returned no real answer: FAULT.
# Deliberately NOT here: a non-pass with an empty-but-untagged body and no error.
# With no error signal we must not GUESS infra — an empty answer the grader failed
# is a real FAIL, and excusing it would let a broken model launder failures as
# FAULTs. Only explicit error signals or the narrow degeneracy shape count.
_DEGEN = re.compile(r'^(?:\s*</?think>\s*)+$', re.IGNORECASE)
def is_fault(r):
    fr = r.get("failureReason")
    if fr == 2 or (isinstance(fr, str) and fr.strip().lower() == "error"):
        return True
    assertion_fail = fr == 1 or (isinstance(fr, str) and fr.strip().lower() == "assert")
    if not assertion_fail:
        # Legacy fallback: only a row with no failureReason recorded may be
        # classified FAULT on .error alone.
        err = r.get("error")
        if isinstance(err, str) and err.strip():
            return True
    if r.get("success") is not True:
        body = output_text(r).strip()
        if body and _DEGEN.match(body):
            return True
    return False

agg = {}
for r in rows:
    k = key(r)
    a = agg.setdefault(k, {"runs": 0, "valid": 0, "pass": 0, "fault": 0})
    a["runs"] += 1
    if is_fault(r):
        a["fault"] += 1
    else:
        a["valid"] += 1
        if r.get("success") is True:
            a["pass"] += 1

below = 0
under_runs = 0
starved = 0
print(f"pass-rate: floor={floor:.2f}  min-runs={min_runs}  min-valid={min_valid}  scenarios={len(agg)}")
for k in sorted(agg):
    runs, valid, passes, fault = agg[k]["runs"], agg[k]["valid"], agg[k]["pass"], agg[k]["fault"]
    rate = passes / valid if valid else 0.0
    if runs < min_runs:
        tag = "UNDER-REPEATED"; under_runs += 1
    elif valid < min_valid:
        tag = "STARVED"; starved += 1
    elif rate < floor:
        tag = "BELOW-FLOOR"; below += 1
    else:
        tag = "OK"
    fnote = f"  ({fault} FAULT excluded)" if fault else ""
    print(f"  [{tag}] {passes}/{valid} valid = {rate:.2f}  [{runs} rows]{fnote}  {k[:90]}")

if under_runs:
    print(f"pass-rate: FAIL — {under_runs} scenario(s) ran fewer than {min_runs} times; this was not a repeated run (fail-closed)", file=sys.stderr)
    sys.exit(1)
if starved:
    print(f"pass-rate: FAIL — {starved} scenario(s) had fewer than {min_valid} VALID samples after excluding FAULTs; the model call kept erroring, so the scenario was never actually tested (fail-closed — a 504 storm is not a green)", file=sys.stderr)
    sys.exit(1)
if below:
    print(f"pass-rate: FAIL — {below} scenario(s) below the {floor:.2f} floor; a green here would be noise", file=sys.stderr)
    sys.exit(1)
print("pass-rate: PASS — every scenario at or above floor with enough valid samples")
PY
