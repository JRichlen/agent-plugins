# CRITERIA — slice 2: reconcile, the independent END

<!-- Round 3 of the Red Gate build (build round). Criteria derived from the
     approved plan's slice 2: "reconcile: the independent END — re-hash both
     pinned files, run the verifier fresh, reject PASS without an evidence
     file newer than run start, mutation-control procedure, verdict table."
     Every check_cmd runs from this run directory; ../.. is the repo root. -->

## #1 reconcile.sh exists and is a parseable bash program
layers: script
red-because: absent — the file does not exist yet
check_cmd: bash -n ../../plugins/redgate/skills/reconcile/scripts/reconcile.sh

## #2 An UNPINNED run is refused — you cannot verify what was never ratified
layers: script, protocol
red-because: absent — nothing implements the refusal
check_cmd: R=../../plugins/redgate/skills; d=$(mktemp -d); $R/criteria-contract/scripts/scaffold-run.sh --slug t --root "$d" >/dev/null 2>&1; out=$($R/reconcile/scripts/reconcile.sh --slug t --root "$d" 2>&1); rc=$?; rm -rf "$d"; [ "$rc" -ne 0 ] && printf '%s' "$out" | grep -qi 'not pinned\|unpinned'

## #3 check.sh drift after pinning fails the run
layers: script, protocol
red-because: absent — no re-hash of the checker exists
check_cmd: R=../../plugins/redgate/skills; d=$(mktemp -d); $R/criteria-contract/scripts/scaffold-run.sh --slug t --root "$d" >/dev/null 2>&1; $R/criteria-contract/scripts/scaffold-run.sh --pin t --root "$d" >/dev/null 2>&1; echo '# tampered' >> "$d/.redgate/t/check.sh"; out=$($R/reconcile/scripts/reconcile.sh --slug t --root "$d" 2>&1); rc=$?; rm -rf "$d"; [ "$rc" -ne 0 ] && printf '%s' "$out" | grep -qi drift

## #4 CRITERIA.md drift after pinning fails the run
layers: script, protocol
red-because: absent — no re-hash of the criteria exists
check_cmd: R=../../plugins/redgate/skills; d=$(mktemp -d); $R/criteria-contract/scripts/scaffold-run.sh --slug t --root "$d" >/dev/null 2>&1; $R/criteria-contract/scripts/scaffold-run.sh --pin t --root "$d" >/dev/null 2>&1; echo '## #9 injected' >> "$d/.redgate/t/CRITERIA.md"; out=$($R/reconcile/scripts/reconcile.sh --slug t --root "$d" 2>&1); rc=$?; rm -rf "$d"; [ "$rc" -ne 0 ] && printf '%s' "$out" | grep -qi drift

## #5 A clean pinned run yields a per-criterion verdict table with evidence proof
layers: script, protocol, report
red-because: absent — nothing emits a verdict table or checks evidence freshness
check_cmd: R=../../plugins/redgate/skills; d=$(mktemp -d); $R/criteria-contract/scripts/scaffold-run.sh --slug t --root "$d" >/dev/null 2>&1; printf '## #1 always true\nlayers: x\nred-because: n/a\ncheck_cmd: true\n' > "$d/.redgate/t/CRITERIA.md"; $R/criteria-contract/scripts/scaffold-run.sh --pin t --root "$d" >/dev/null 2>&1; out=$($R/reconcile/scripts/reconcile.sh --slug t --root "$d" 2>&1); rc=$?; rm -rf "$d"; [ "$rc" -eq 0 ] && printf '%s' "$out" | grep -qE '^#1[[:space:]]+PASS' && printf '%s' "$out" | grep -qi 'evidence'

## #6 A PASS whose evidence file is missing or stale is rejected, not trusted
layers: script, protocol
red-because: absent — no evidence-freshness gate exists
check_cmd: R=../../plugins/redgate/skills; d=$(mktemp -d); $R/criteria-contract/scripts/scaffold-run.sh --slug t --root "$d" >/dev/null 2>&1; printf '## #1 always true\nlayers: x\nred-because: n/a\ncheck_cmd: true\n' > "$d/.redgate/t/CRITERIA.md"; $R/criteria-contract/scripts/scaffold-run.sh --pin t --root "$d" >/dev/null 2>&1; out=$(RG_TEST_DROP_EVIDENCE=1 $R/reconcile/scripts/reconcile.sh --slug t --root "$d" 2>&1); rc=$?; rm -rf "$d"; [ "$rc" -ne 0 ] && printf '%s' "$out" | grep -qi 'evidence'
