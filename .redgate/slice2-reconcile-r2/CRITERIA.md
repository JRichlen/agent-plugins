# CRITERIA — slice 2 round 2: drift detection, properly coupled

<!-- Round 1 shipped reconcile.sh, but its mutation control demoted #3 and #4
     to UNVERIFIABLE: both used a fixture whose criteria fail anyway, so
     "reconcile exits nonzero" was satisfied by the ordinary FAIL path rather
     than by drift detection, and the drift string matched a warning that
     fires whether or not the gate acts.

     Round 1's contract is pinned and is NOT edited. This is a fresh contract.

     The fix in the criteria (not the code): every drift fixture now uses a
     run whose criteria PASS. Then the ONLY thing that can make reconcile
     fail is the drift gate itself — removing the gate makes these criteria
     go red, which is what coupling means. Each carries its own positive
     control: the same fixture WITHOUT tampering must come back green. -->

## #1 POSITIVE CONTROL — an untampered passing run verifies green
layers: script, protocol
red-because: present-but-wrong — round 1 never proved the clean path on a passing fixture
check_cmd: R=../../plugins/redgate/skills; d=$(mktemp -d); $R/criteria-contract/scripts/scaffold-run.sh --slug t --root "$d" >/dev/null 2>&1; printf '## #1 passes\nlayers: x\nred-because: n/a\ncheck_cmd: true\n' > "$d/.redgate/t/CRITERIA.md"; $R/criteria-contract/scripts/scaffold-run.sh --pin t --root "$d" >/dev/null 2>&1; $R/reconcile/scripts/reconcile.sh --slug t --root "$d" >/dev/null 2>&1; rc=$?; rm -rf "$d"; [ "$rc" -eq 0 ]

## #2 CHECKER drift on an otherwise-PASSING run fails the run
layers: script, protocol
red-because: present-but-wrong — round 1's fixture could not distinguish drift from ordinary failure
check_cmd: R=../../plugins/redgate/skills; d=$(mktemp -d); $R/criteria-contract/scripts/scaffold-run.sh --slug t --root "$d" >/dev/null 2>&1; printf '## #1 passes\nlayers: x\nred-because: n/a\ncheck_cmd: true\n' > "$d/.redgate/t/CRITERIA.md"; $R/criteria-contract/scripts/scaffold-run.sh --pin t --root "$d" >/dev/null 2>&1; echo '# tampered' >> "$d/.redgate/t/check.sh"; out=$($R/reconcile/scripts/reconcile.sh --slug t --root "$d" 2>&1); rc=$?; rm -rf "$d"; [ "$rc" -ne 0 ] && printf '%s' "$out" | grep -qi 'CHECKER drift'

## #3 CRITERIA drift on an otherwise-PASSING run fails the run
layers: script, protocol
red-because: present-but-wrong — same uncoupled fixture as #2 in round 1
check_cmd: R=../../plugins/redgate/skills; d=$(mktemp -d); $R/criteria-contract/scripts/scaffold-run.sh --slug t --root "$d" >/dev/null 2>&1; printf '## #1 passes\nlayers: x\nred-because: n/a\ncheck_cmd: true\n' > "$d/.redgate/t/CRITERIA.md"; $R/criteria-contract/scripts/scaffold-run.sh --pin t --root "$d" >/dev/null 2>&1; printf '## #2 also passes\nlayers: x\nred-because: n/a\ncheck_cmd: true\n' >> "$d/.redgate/t/CRITERIA.md"; out=$($R/reconcile/scripts/reconcile.sh --slug t --root "$d" 2>&1); rc=$?; rm -rf "$d"; [ "$rc" -ne 0 ] && printf '%s' "$out" | grep -qi 'CRITERIA drift'

## #4 The drift verdict is distinguishable from an ordinary unmet criterion
layers: protocol, report
red-because: present-but-wrong — round 1 could not tell the two verdicts apart
check_cmd: R=../../plugins/redgate/skills; d=$(mktemp -d); $R/criteria-contract/scripts/scaffold-run.sh --slug t --root "$d" >/dev/null 2>&1; $R/criteria-contract/scripts/scaffold-run.sh --pin t --root "$d" >/dev/null 2>&1; out=$($R/reconcile/scripts/reconcile.sh --slug t --root "$d" 2>&1); rm -rf "$d"; printf '%s' "$out" | grep -qi 'unmet' && ! printf '%s' "$out" | grep -qi 'drift'
