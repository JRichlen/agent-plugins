#!/usr/bin/env bash
# Real acceptance-kernel controls. Offline; isolated from user work.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN="$(cd "$HERE/../.." && pwd)"
SCAF="$PLUGIN/skills/criteria-contract/scripts/scaffold-run.sh"
RECON="$PLUGIN/skills/reconcile/scripts/reconcile.sh"
GUARD="$PLUGIN/hooks/hooks-handlers/guard-acceptance-paths.sh"
INDEX="$PLUGIN/skills/criteria-contract/scripts/criteria-index.sh"
D="$(mktemp -d "${TMPDIR:-/tmp}/acceptance-controls.XXXXXX")"
case "$D" in "${TMPDIR:-/tmp}"/acceptance-controls.*) ;; *) echo 'unsafe test directory' >&2; exit 2 ;; esac
pass=0; failures=0
expect() {
  local want="$1" label="$2"; shift 2
  "$@" >"$D/last.out" 2>&1; rc=$?
  if [ "$rc" -eq "$want" ]; then pass=$((pass+1)); echo "PASS $label"
  else failures=$((failures+1)); echo "FAIL $label: got $rc, wanted $want"; cat "$D/last.out"; fi
}
payload() { printf '{"tool_name":"Edit","tool_input":{"file_path":"%s"}}' "$1"; }
expect 0 'create case' bash "$SCAF" --slug controls --root "$D"
RUN="$D/.redgate/controls"
expect 1 'fresh checker rejects absent target' bash "$RUN/check.sh"
expect 2 'unpinned case refused' bash "$RECON" --slug controls --root "$D"
cat >"$RUN/CRITERIA.md" <<EOF
## #1 first output exists
check_cmd: test -f "$D/one"
## #2 second output exists
check_cmd: test -f "$D/two"
EOF
expect 1 'agreed checks reject negative state' bash "$RUN/check.sh"
expect 0 'pin contract' bash "$SCAF" --pin controls --root "$D"
expect 2 're-pin refused' bash "$SCAF" --pin controls --root "$D"
expect 1 'unmet contract rejected' bash "$RECON" --slug controls --root "$D"
touch "$D/one" "$D/two"
expect 0 'green contract produces fresh evidence' bash "$RECON" --slug controls --root "$D"
expect 1 'missing evidence rejects reported pass' env RG_TEST_DROP_EVIDENCE=1 bash "$RECON" --slug controls --root "$D"
cp "$RUN/CRITERIA.md" "$D/criteria.saved"
printf '\nchanged\n' >>"$RUN/CRITERIA.md"
expect 1 'criteria tampering rejected' bash "$RECON" --slug controls --root "$D"
cp "$D/criteria.saved" "$RUN/CRITERIA.md"
cp "$RUN/check.sh" "$D/check.saved"
printf '\n# tamper\n' >>"$RUN/check.sh"
expect 1 'checker tampering rejected' bash "$RECON" --slug controls --root "$D"
cp "$D/check.saved" "$RUN/check.sh"
for name in CRITERIA.md check.sh manifest; do
  payload "$RUN/$name" >"$D/payload.json"
  expect 2 "pinned $name write denied" bash -c 'bash "$1" <"$2"' _ "$GUARD" "$D/payload.json"
done
payload "$D/unrelated.md" >"$D/payload.json"
expect 0 'unrelated write allowed' bash -c 'bash "$1" <"$2"' _ "$GUARD" "$D/payload.json"

expect 0 'create fault control' bash "$SCAF" --slug fault --root "$D"
F="$D/.redgate/fault"
printf '#!/usr/bin/env bash\nexit 99\n' >"$F/check.sh"
expect 0 'pin fault control' bash "$SCAF" --pin fault --root "$D"
expect 1 'harness fault never becomes acceptance' bash "$RECON" --slug fault --root "$D"
grep -q FAULT "$D/last.out" || { echo 'FAIL fault must remain distinguishable'; failures=$((failures+1)); }

expect 0 'create empty-verdict control' bash "$SCAF" --slug empty --root "$D"
E="$D/.redgate/empty"
printf '#!/usr/bin/env bash\nexit 0\n' >"$E/check.sh"
expect 0 'pin empty-verdict control' bash "$SCAF" --pin empty --root "$D"
expect 1 'zero executable verdicts cannot pass' bash "$RECON" --slug empty --root "$D"

expect 0 'create misleading-exit control' bash "$SCAF" --slug misleading --root "$D"
M="$D/.redgate/misleading"
printf '#!/usr/bin/env bash\ncd "$(dirname "$0")"\ntouch evidence/1.out\necho "#1 PASS"\nexit 1\n' >"$M/check.sh"
expect 0 'pin misleading-exit control' bash "$SCAF" --pin misleading --root "$D"
expect 1 'nonzero checker exit cannot pass' bash "$RECON" --slug misleading --root "$D"
expect 0 'build pointer index' bash "$INDEX" --root "$D"
expect 0 'pointer index reproduces' bash "$INDEX" --check --root "$D"
echo "acceptance controls: $pass passed, $failures failed"
# The directory was allocated above and remains inside the checked temp root.
case "$D" in "${TMPDIR:-/tmp}"/acceptance-controls.*) rm -rf -- "$D" ;; *) exit 2 ;; esac
[ "$failures" -eq 0 ]
