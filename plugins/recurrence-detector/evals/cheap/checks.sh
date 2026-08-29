# Cheap eval pack for 'recurrence-detector' — SOURCED by evals/cheap/run.sh.
# What this defends: DETECT proposes and never disposes. A detector that
# scaffolds is the growth loop skipping its own eval gate.

SKILL="$PLUGIN_DIR/skills/recurrence-detector/SKILL.md"
AGENTS="$PLUGIN_DIR/AGENTS.md"

group "recurrence-detector — structure"
for f in "$PLUGIN_DIR/.claude-plugin/plugin.json" "$SKILL" "$AGENTS" "$PLUGIN_DIR/README.md" "$PLUGIN_DIR/commands/recurrence-detector.md"; do
  if [ -f "$f" ]; then ok "present: $f"; else bad "MISSING: $f"; fi
done

group "recurrence-detector — invariant survives verbatim"
INV='NEVER auto-scaffolded into a skill'
has "$SKILL"  "$INV" "SKILL.md carries the never-auto-scaffold invariant" "SKILL.md lost the never-auto-scaffold invariant"
has "$AGENTS" "$INV" "AGENTS.md carries the never-auto-scaffold invariant" "AGENTS.md lost the never-auto-scaffold invariant"
hasE "$SKILL" 'at least N times' "the sighting threshold is required" "the sighting threshold is gone"
hasE "$SKILL" 'every sighting is cited' "citations are required per sighting" "the citation requirement is gone"

group "recurrence-detector — proposes, never disposes"
hasE "$SKILL" 'Never scaffold, never edit a skill' "the three prohibitions are explicit" "the propose-only prohibitions are gone"
hasE "$SKILL" 'human picks' "the human disposes" "the human-disposes clause is gone"
lacksE "$SKILL" '(auto-?scaffold|automatically (create|scaffold|build)) (the |a )?skill' "no auto-scaffolding language" "found auto-scaffolding language — the propose-only invariant is weakened"

group "recurrence-detector — the threshold is defended, not decorative"
hasE "$SKILL" 'N = 3|N=3' "a concrete default threshold is stated" "no concrete threshold"
hasE "$SKILL" 'incident.*coincidence.*shape|memorizing noise' "the rationale for N>1 is stated" "the threshold rationale is gone"
hasE "$SKILL" 'watched' "sub-threshold candidates are watched, not promoted" "sub-threshold handling is gone"

group "recurrence-detector — clusters by mechanism, not symptom"
hasE "$SKILL" 'failure shape, not by surface|not by surface' "clustering is by mechanism" "the mechanism-not-symptom rule is gone"
has "$SKILL" 'find-before-build' "already-covered candidates are disqualified" "the already-covered disqualifier is gone"

group "recurrence-detector — the growth-loop amendments it depends on"
for f in plugins/dev-diary/skills/dev-diary/references/consolidate-delta.md \
         plugins/fleet-playbook-curator/skills/fleet-playbook-curator/references/consolidate-delta.md \
         plugins/plugin-factory/skills/plugin-factory/references/judge-calibration.md; do
  if [ -f "$f" ]; then ok "present: $f"; else bad "MISSING: $f"; fi
done
hasE plugins/dev-diary/skills/dev-diary/references/consolidate-delta.md 'A new tag for the' "reused shape tags are required (a new tag defeats the count)" "the tag-reuse rule is gone"
hasE plugins/plugin-factory/skills/plugin-factory/references/judge-calibration.md 'six scenarios, six rejections' "the measured discrimination bar is cited" "the measured bar citation is gone"
hasE plugins/plugin-factory/skills/plugin-factory/references/judge-calibration.md 'never a silencing|never deletes|Do not delete the control' "a failing calibration is a finding, not a silencing" "the never-silence rule is gone"
