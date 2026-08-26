# Cheap eval pack for the 'redgate' plugin — SOURCED by evals/cheap/run.sh
# with cwd = repo root; inherits ok/bad/group/has/hasE/lacksE and
# $PLUGIN_NAME / $PLUGIN_DIR.
#
# What this defends: the red gate itself. A freshly scaffolded run's
# verifier must be RED and both artifacts must pin; harness failure must be
# exit 99 and never counted as red; a missing subject binary (127) must be a
# legitimate FAIL. These are executed, not grepped — the scaffold dogfood is
# the pack's core.

DRIVER="$PLUGIN_DIR/skills/redgate/SKILL.md"
CONTRACT="$PLUGIN_DIR/skills/criteria-contract/SKILL.md"
SCAFFOLD="$PLUGIN_DIR/skills/criteria-contract/scripts/scaffold-run.sh"
AGENTS="$PLUGIN_DIR/AGENTS.md"

group "redgate — structure"
for f in "$PLUGIN_DIR/.claude-plugin/plugin.json" "$DRIVER" "$CONTRACT" "$SCAFFOLD" "$AGENTS" "$PLUGIN_DIR/README.md" "$PLUGIN_DIR/commands/redgate.md"; do
  if [ -f "$f" ]; then ok "present: $f"; else bad "MISSING: $f"; fi
done
if bash -n "$SCAFFOLD" 2>/dev/null; then ok "scaffold-run.sh parses (bash -n)"; else bad "scaffold-run.sh fails bash -n"; fi

group "redgate — invariant survives verbatim"
INV='no criterion is ever marked green except by that same pinned verifier'
has "$DRIVER" "$INV" "driver SKILL.md carries the pinned-verifier invariant" "driver SKILL.md lost the pinned-verifier invariant"
has "$AGENTS" "$INV" "AGENTS.md carries the pinned-verifier invariant" "AGENTS.md lost the pinned-verifier invariant"
hasE "$DRIVER" 'Criteria that cannot be rejected are not criteria' "the one-sentence design survives" "the one-sentence design is gone"

group "redgate — red-gate semantics stated"
hasE "$CONTRACT" '127 included, is a legitimate FAIL' "127-is-FAIL is stated" "127-is-FAIL rule lost"
hasE "$CONTRACT" 'It never probes' "preflight scoped to harness only" "preflight scope rule lost"
hasE "$CONTRACT" 'sha256 of BOTH files' "both-files pinning stated" "both-files pinning lost"
hasE "$CONTRACT" 'at most 1 UNVERIFIABLE' "UNVERIFIABLE cap stated" "UNVERIFIABLE cap lost"
hasE "$DRIVER" 'never crosses a round' "rounds-vs-recursion boundary stated" "rounds-vs-recursion boundary lost"

group "redgate — scaffold dogfood: the gate is actually red"
_rg_tmp="$(mktemp -d)"
if "$SCAFFOLD" --slug ci-dogfood --root "$_rg_tmp" >/dev/null 2>&1; then
  ok "scaffold-run.sh creates a run"
  bash "$_rg_tmp/.redgate/ci-dogfood/check.sh" >/dev/null 2>&1; _rc=$?
  if [ "$_rc" -eq 1 ]; then ok "fresh scaffold's check.sh exits 1 (RED) — never green from birth"; else bad "fresh scaffold's check.sh exited $_rc, expected 1 (red)"; fi
  if [ -s "$_rg_tmp/.redgate/ci-dogfood/evidence/1.out" ] || [ -f "$_rg_tmp/.redgate/ci-dogfood/evidence/1.out" ]; then ok "evidence file written by the harness"; else bad "no evidence file written"; fi
  _crit="$_rg_tmp/.redgate/ci-dogfood/CRITERIA.md"
  mv "$_crit" "$_crit.bak"
  bash "$_rg_tmp/.redgate/ci-dogfood/check.sh" >/dev/null 2>&1; _rc=$?
  mv "$_crit.bak" "$_crit"
  if [ "$_rc" -eq 99 ]; then ok "harness failure is exit 99, not red"; else bad "harness failure exited $_rc, expected 99"; fi
  printf '\n## #9 missing subject binary\nlayers: cli\nred-because: absent\ncheck_cmd: rg-ci-not-a-binary --version\n' >> "$_crit"
  _out="$(bash "$_rg_tmp/.redgate/ci-dogfood/check.sh" 2>/dev/null || true)"
  if printf '%s' "$_out" | grep -q '^#9 FAIL$'; then ok "a 127 check_cmd is a FAIL, not a harness error"; else bad "127 check_cmd was not reported as FAIL"; fi
  if "$SCAFFOLD" --pin ci-dogfood --root "$_rg_tmp" >/dev/null 2>&1 && grep -q '^phase=MIDDLE$' "$_rg_tmp/.redgate/ci-dogfood/manifest" && [ "$(grep -c '^[a-z_]*sha256=[0-9a-f]\{64\}$' "$_rg_tmp/.redgate/ci-dogfood/manifest")" -eq 2 ]; then
    ok "pin writes both sha256s and flips phase to MIDDLE"
  else
    bad "pin did not record both sha256s + phase=MIDDLE"
  fi
  if "$SCAFFOLD" --pin ci-dogfood --root "$_rg_tmp" >/dev/null 2>&1; then bad "re-pin was allowed — a pinned contract must never re-pin"; else ok "re-pin refused"; fi
  if grep -q '^autonomy=classified$' "$_rg_tmp/.redgate/ci-dogfood/manifest"; then ok "manifest declares autonomy=classified"; else bad "manifest missing autonomy=classified"; fi
  if [ -f "$_rg_tmp/.redgate/ci-dogfood/gates.log" ]; then ok "gate ledger (gates.log) created at scaffold"; else bad "gates.log not created"; fi
else
  bad "scaffold-run.sh failed to create a run"
fi
rm -rf "$_rg_tmp"

group "redgate — reconcile: the independent END (executed, coupled)"
RECON="$PLUGIN_DIR/skills/reconcile/scripts/reconcile.sh"
SCAF="$PLUGIN_DIR/skills/criteria-contract/scripts/scaffold-run.sh"
if [ -f "$RECON" ] && bash -n "$RECON" 2>/dev/null; then
  ok "reconcile.sh present and parses"
  # Fixture helper: a run whose criteria PASS, so the ONLY thing that can make
  # reconcile fail is the gate under test. This coupling is what round 1's
  # criteria lacked — see .redgate/slice2-reconcile-r2/gates.log.
  _mkpass() { _d="$(mktemp -d)"; "$SCAF" --slug t --root "$_d" >/dev/null 2>&1;
    printf '## #1 passes\nlayers: x\nred-because: n/a\ncheck_cmd: true\n' > "$_d/.redgate/t/CRITERIA.md";
    "$SCAF" --pin t --root "$_d" >/dev/null 2>&1; printf '%s' "$_d"; }

  _d="$(_mkpass)"
  if "$RECON" --slug t --root "$_d" >/dev/null 2>&1; then ok "positive control: untampered passing run verifies green"; else bad "positive control failed — a clean passing run did not verify"; fi
  rm -rf "$_d"

  _d="$(_mkpass)"; echo '# tampered' >> "$_d/.redgate/t/check.sh"
  _out="$("$RECON" --slug t --root "$_d" 2>&1)"; _rc=$?
  rm -rf "$_d"
  # rc, not just the message: on a fixture whose criteria PASS, a non-zero exit
  # can ONLY come from the drift gate acting. Grepping the warning text alone
  # passes even when the gate is reverted — that was the round-1 defect.
  if [ "$_rc" -ne 0 ] && printf '%s' "$_out" | grep -qi 'CHECKER drift'; then ok "checker drift on a passing run FAILS the run (exit-coupled)"; else bad "checker drift did not fail a passing run (rc=$_rc)"; fi

  _d="$(_mkpass)"; printf '## #2 also passes\nlayers: x\nred-because: n/a\ncheck_cmd: true\n' >> "$_d/.redgate/t/CRITERIA.md"
  _out="$("$RECON" --slug t --root "$_d" 2>&1)"; _rc=$?
  rm -rf "$_d"
  if [ "$_rc" -ne 0 ] && printf '%s' "$_out" | grep -qi 'CRITERIA drift'; then ok "criteria drift on a passing run FAILS the run (exit-coupled)"; else bad "criteria drift did not fail a passing run (rc=$_rc)"; fi

  _d="$(mktemp -d)"; "$SCAF" --slug t --root "$_d" >/dev/null 2>&1
  _out="$("$RECON" --slug t --root "$_d" 2>&1 || true)"
  if printf '%s' "$_out" | grep -qi 'not pinned\|unpinned'; then ok "an unpinned run is refused — never ratified, never graded"; else bad "unpinned run was not refused"; fi
  "$SCAF" --pin t --root "$_d" >/dev/null 2>&1
  _out="$("$RECON" --slug t --root "$_d" 2>&1 || true)"
  if printf '%s' "$_out" | grep -qi 'unmet' && ! printf '%s' "$_out" | grep -qi 'drift'; then ok "an ordinary unmet criterion reads as unmet, never as drift"; else bad "unmet and drift verdicts are not distinguishable"; fi
  _d2="$_d"
  _out="$(RG_TEST_DROP_EVIDENCE=1 "$RECON" --slug t --root "$_d2" 2>&1)"; _rc=$?
  rm -rf "$_d"
  if [ "$_rc" -ne 0 ] && printf '%s' "$_out" | grep -qi 'evidence'; then ok "a PASS without fresh evidence is REJECTED (exit-coupled)"; else bad "evidence-freshness gate did not fail the run (rc=$_rc)"; fi
else
  bad "reconcile.sh missing or does not parse"
fi

group "redgate — graduated autonomy (semver-gate classified gates)"
has "$DRIVER" 'semver-gate' "driver imports semver-gate as the gate classifier" "driver lost the semver-gate wiring"
hasE "$DRIVER" 'any property\s*$|any property' "tie-break inherited (any property MAJOR)" "tie-break rule lost"
hasE "$DRIVER" 'Always MAJOR' "the always-MAJOR escalator list exists" "the always-MAJOR escalator list is gone"
hasE "$DRIVER" 'orientation' "orientation decisions are an escalator" "orientation escalator lost"
hasE "$DRIVER" 'UNVERIFIABLE countersignature' "UNVERIFIABLE countersignatures stay human" "UNVERIFIABLE escalator lost"
hasE "$DRIVER" 'never auto-passed, never softened' "MAJOR can never be auto-passed" "the never-auto-pass clause is gone"
hasE "$DRIVER" 'byte-derivable' "derived ratification requires strict plan derivation" "derived-ratification rule lost"
hasE "$DRIVER" 'self-ratification' "self-ratification guard stated" "self-ratification guard lost"
hasE "$DRIVER" 'qualifying conditions is a protocol violation' "unjustified auto-pass is a violation, not judgment" "the auto-pass justification rule is gone"
lacksE "$DRIVER" 'MAJOR (may|can|should|will) (auto-pass|proceed without|be skipped)|MAJOR.{0,60}skip the (question|ask)' "no MAJOR-may-auto-pass phrasing anywhere" "found MAJOR paired with auto-pass language — the gate has been weakened"

group "redgate — cross-harness claims are wired"
has "$DRIVER" 'apm compile -t copilot' "driver names the Copilot compile path" "driver lost the Copilot compile path"
hasE "$AGENTS" 'Codex|codex' "AGENTS.md addresses Codex" "AGENTS.md does not address Codex"
has "$PLUGIN_DIR/README.md" 'apm install' "README documents the APM install path" "README lost the APM install path"

group "redgate — disambiguated from siblings"
has "$DRIVER" 'wayfinder' "driver disambiguates vs wayfinder" "wayfinder disambiguation lost"
has "$DRIVER" 'orchestrate' "driver disambiguates vs orchestrate" "orchestrate disambiguation lost"
has "$DRIVER" 'tracer-bullets' "driver disambiguates vs tracer-bullets" "tracer-bullets disambiguation lost"
