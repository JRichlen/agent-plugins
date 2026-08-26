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
hasE "$DRIVER" 'recursion is vertical and never crosses a round boundary' "rounds-vs-recursion boundary stated" "rounds-vs-recursion boundary lost"

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
else
  bad "scaffold-run.sh failed to create a run"
fi
rm -rf "$_rg_tmp"

group "redgate — cross-harness claims are wired"
has "$DRIVER" 'apm compile -t copilot' "driver names the Copilot compile path" "driver lost the Copilot compile path"
hasE "$AGENTS" 'Codex|codex' "AGENTS.md addresses Codex" "AGENTS.md does not address Codex"
has "$PLUGIN_DIR/README.md" 'apm install' "README documents the APM install path" "README lost the APM install path"

group "redgate — disambiguated from siblings"
has "$DRIVER" 'wayfinder' "driver disambiguates vs wayfinder" "wayfinder disambiguation lost"
has "$DRIVER" 'orchestrate' "driver disambiguates vs orchestrate" "orchestrate disambiguation lost"
has "$DRIVER" 'tracer-bullets' "driver disambiguates vs tracer-bullets" "tracer-bullets disambiguation lost"
