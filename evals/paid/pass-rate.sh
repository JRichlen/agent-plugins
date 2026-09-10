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
# CALL itself never completed — a 504, an aborted request, or a typed grader
# fault (a harness/transport error, not evidence
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
# on .failureReason: 1/"assert" normally means an assertion failure, while
# typed gradingResult component metadata.graderError=true identifies a failed
# grader call/parse even with failureReason=1. A separate mandatory assertion
# failure stays a valid FAIL; otherwise an incomplete grade is a FAULT.
# 2/"error" = provider/transport error
# (a FAULT, excluded). .error ALONE marks a FAULT only when the row carries no
# failureReason at all (legacy shapes that predate the field): under promptfoo
# >= 0.122 EVERY assertion-failed row also carries .error (the assertion
# message), so .error must never override failureReason == 1 — doing so scored
# real failures as transport faults and let a failing run read green (fail-open).
# Grouping key precedence: testCase.description, else description, else the
# request var — whatever is stable across a scenario's N repeats.
set -uo pipefail

FLOOR="0.6"; MIN_RUNS="2"; MIN_VALID="2"; FILE=""; BY_PROVIDER="0"; BASELINE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --floor)       FLOOR="${2:?}"; shift 2 ;;
    --min-runs)    MIN_RUNS="${2:?}"; shift 2 ;;
    --min-valid)   MIN_VALID="${2:?}"; shift 2 ;;
    # Subject-model matrix (issue #102): score each provider separately instead
    # of pooling every provider's rows into one scenario. Pooling hides the split
    # this mode exists to show — a skill that steers the baseline 3/3 and a new
    # subject 0/3 pools to 0.50 and reads as one mediocre scenario.
    --by-provider) BY_PROVIDER="1"; shift ;;
    # With --baseline ID, only that provider's scenarios decide the exit code;
    # every other provider is scored, printed and tagged ADVISORY (the promotion
    # rule is applied by a human reading the report, per #102). A baseline that
    # produced no rows fails closed: the required leg never ran. Without
    # --baseline, every provider is strict.
    --baseline)    BASELINE="${2:?}"; BY_PROVIDER="1"; shift 2 ;;
    -*)          echo "pass-rate: unknown flag $1" >&2; exit 2 ;;
    *)           FILE="$1"; shift ;;
  esac
done
[ -n "$FILE" ] || { echo "usage: pass-rate.sh RESULTS.json [--floor F] [--min-runs N] [--min-valid M] [--by-provider] [--baseline PROVIDER_ID]" >&2; exit 2; }
[ -f "$FILE" ] || { echo "pass-rate: no such file: $FILE" >&2; exit 2; }

python3 - "$FILE" "$FLOOR" "$MIN_RUNS" "$MIN_VALID" "$BY_PROVIDER" "$BASELINE" <<'PY'
import json, sys
path, floor, min_runs, min_valid = sys.argv[1], float(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
by_provider, baseline = sys.argv[5] == "1", sys.argv[6]
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

# A row is a FAULT (INVALID sample) when the model CALL did not yield a usable
# answer — not when the grader disliked a real answer. .failureReason is the
# discriminator (promptfoo enum: 0 none, 1 assertion failed, 2 error):
#   * .failureReason == 2 or "error" — a provider/transport error (504, aborted
#     request): FAULT;
#   * typed grading metadata.graderError == true — the grader itself failed;
#     FAULT unless another mandatory assertion independently proves failure;
#   * .failureReason == 1 or "assert" without a grader fault — the grader judged
#     a real answer wrong: a REAL FAIL. Under promptfoo >= 0.122 these rows
#     ALSO carry .error (the assertion message), so .error must never promote
#     them to FAULT — that scored real failures as weather and let a failing run
#     read green (fail-open, the dangerous direction; observed on PR #93);
#   * .error set with NO failureReason recorded — legacy fallback for result
#     shapes that predate the field: FAULT;
# Output shape is never an infrastructure signal: missing answers, repeated
# reasoning delimiters, and completion-budget exhaustion remain valid failures
# when their assertions fail and no typed fault establishes an invalid sample.

def has_grader_fault(result):
    """Only Promptfoo's typed grading evidence can identify a grader fault."""
    if not isinstance(result, dict):
        return False
    metadata = result.get("metadata")
    if isinstance(metadata, dict) and metadata.get("graderError") is True:
        return True
    components = result.get("componentResults")
    return isinstance(components, list) and any(has_grader_fault(c) for c in components)

def independent_assertion_failure(r):
    # Promptfoo's default contract is conjunction: one ordinary failed
    # assertion is decisive even if another grader never returned a judgment.
    # Thresholds/custom scoring can override that rule. Flattened nested sets
    # also lose which component was mandatory at the row level; do not guess.
    config = doc.get("config") or {}
    default = config.get("defaultTest") or {}
    test = r.get("testCase") or {}
    for scope in (default, test):
        if scope.get("threshold") is not None or scope.get("assertScoringFunction") is not None:
            return False
    grading = r.get("gradingResult") or {}
    components = grading.get("componentResults")
    if not isinstance(components, list) or any(
        not isinstance(c, dict) or "componentResults" in c or
        (isinstance(c.get("metadata"), dict) and "assertionSet" in c["metadata"])
        for c in components
    ):
        return False
    return r.get("success") is not True and any(
        c.get("pass") is False and not has_grader_fault(c) for c in components
    )

def is_fault(r):
    fr = r.get("failureReason")
    if fr == 2 or (isinstance(fr, str) and fr.strip().lower() == "error"):
        return True
    if has_grader_fault(r.get("gradingResult")):
        return not independent_assertion_failure(r)
    # Legacy fallback: ONLY a row with no failureReason recorded at all
    # (missing/None/blank) may be classified FAULT on .error alone. A present
    # failureReason that is neither 2/"error" nor 1/"assert" (e.g. 0 with a
    # non-pass row and a stray .error) is NOT a transport fault — it stays a
    # scored sample. Fail-closed: an unexplained non-pass is a FAIL, never
    # weather.
    no_reason = fr is None or (isinstance(fr, str) and not fr.strip())
    if no_reason:
        err = r.get("error")
        if isinstance(err, str) and err.strip():
            return True
    return False

def provider_of(r):
    p = r.get("provider")
    if isinstance(p, dict):
        return str(p.get("id") or p.get("label") or "<unknown>")
    if isinstance(p, str) and p.strip():
        return p
    return str(r.get("providerId") or "<unknown>")

# agg is keyed by (provider, scenario); in pooled mode the provider slot is "".
agg = {}
for r in rows:
    k = (provider_of(r) if by_provider else "", key(r))
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
advisory_below = 0
providers = sorted({p for p, _ in agg})
if by_provider:
    print(f"pass-rate: floor={floor:.2f}  min-runs={min_runs}  min-valid={min_valid}  providers={len(providers)}  scenarios={len({s for _, s in agg})}  by-provider" + (f"  baseline={baseline}" if baseline else "  (every provider strict)"))
    if baseline and baseline not in providers:
        print(f"pass-rate: FAIL — baseline provider '{baseline}' produced no rows; the required leg never ran (fail-closed)", file=sys.stderr)
        sys.exit(1)
else:
    print(f"pass-rate: floor={floor:.2f}  min-runs={min_runs}  min-valid={min_valid}  scenarios={len(agg)}")
for prov in providers:
    strict = (not by_provider) or (not baseline) or prov == baseline
    if by_provider:
        print(f"  provider {prov}" + ("" if strict else "  [ADVISORY — does not decide the exit code]"))
    for k in sorted(s for p, s in agg if p == prov):
        a = agg[(prov, k)]
        runs, valid, passes, fault = a["runs"], a["valid"], a["pass"], a["fault"]
        rate = passes / valid if valid else 0.0
        if runs < min_runs:
            tag = "UNDER-REPEATED"
            if strict: under_runs += 1
        elif valid < min_valid:
            tag = "STARVED"
            if strict: starved += 1
        elif rate < floor:
            tag = "BELOW-FLOOR"
            if strict: below += 1
            else: advisory_below += 1
        else:
            tag = "OK"
        if not strict and tag != "OK":
            tag = "ADVISORY " + tag
        fnote = f"  ({fault} FAULT excluded)" if fault else ""
        print(f"  [{tag}] {passes}/{valid} valid = {rate:.2f}  [{runs} rows]{fnote}  {k[:90]}")
if advisory_below:
    print(f"pass-rate: advisory — {advisory_below} scenario(s) below the floor under a non-baseline subject; read the report before promoting that subject (#102)")

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
