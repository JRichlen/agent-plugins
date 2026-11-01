# Verification methods: structure plus real executable kernel controls.
SKILL="$PLUGIN_DIR/skills/verify-before-claim/SKILL.md"
group "verification methods and shared owner"
for rel in .claude-plugin/plugin.json AGENTS.md README.md commands/verify-before-claim.md commands/verify-work.md skills/verify-before-claim/SKILL.md skills/verify-work/SKILL.md skills/criteria-contract/SKILL.md skills/reconcile/SKILL.md hooks/hooks.json hooks/hooks-handlers/guard-acceptance-paths.sh; do
  if [ -f "$PLUGIN_DIR/$rel" ]; then ok "present: $rel"; else bad "missing: $rel"; fi
done
for name in pre-claim-reproduction.md uncertainty-flagging.md primary-source-research.md skill-behavior-verification.md; do
  if [ -f "$PLUGIN_DIR/skills/verify-before-claim/references/$name" ] && grep -qF "references/$name" "$SKILL"; then ok "claim procedure links $name"; else bad "broken claim procedure reference: $name"; fi
done
for rel in skills/verify-before-claim/SKILL.md skills/verify-work/SKILL.md; do
  has "$PLUGIN_DIR/$rel" 'context/OPERATING.md' "$rel references shared core" "$rel duplicates or omits the core owner"
done
has "$PLUGIN_DIR/skills/verify-work/SKILL.md" 'not a default task workflow' "formal acceptance is conditional" "formal acceptance became a default workflow"
has "$PLUGIN_DIR/skills/verify-work/SKILL.md" 'actual reviewer' "independent review requires an actual reviewer" "review provenance was lost"
has "$PLUGIN_DIR/skills/reconcile/SKILL.md" 'script cannot mechanically establish reviewer independence' "script limitations remain explicit" "script overclaims reviewer identity"
if [ ! -f plugins/redgate/.claude-plugin/plugin.json ] && [ ! -f plugins/redgate/skills/redgate/SKILL.md ]; then ok "retired product has no manifest or driver"; else bad "retired product remains live"; fi
for rel in skills/criteria-contract/scripts/scaffold-run.sh skills/criteria-contract/scripts/criteria-index.sh skills/reconcile/scripts/reconcile.sh; do
  if [ -f "plugins/redgate/$rel" ] && grep -q 'exec bash' "plugins/redgate/$rel"; then ok "thin source adapter: $rel"; else bad "missing thin compatibility adapter: $rel"; fi
done
group "acceptance kernel positive and negative controls"
if out="$(bash "$PLUGIN_DIR/evals/cheap/check-acceptance.sh" 2>&1)"; then
  ok "acceptance controls reject unpinned, drifted, stale, empty and nonzero verdicts"
else
  bad "acceptance kernel controls failed"
  printf '%s\n' "$out"
fi

group "behavioral exposure includes the canonical core"
has "$PLUGIN_DIR/evals/promptfoo/promptfooconfig.yaml" 'core: file://../../context/OPERATING.md' "paid pack supplies packaged core" "paid pack omits canonical core context"
has "$PLUGIN_DIR/evals/promptfoo/prompt.txt" '{{core}}' "paid prompt actually includes core variable" "paid prompt never exposes core"
