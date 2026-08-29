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

group "recurrence-detector — gate-outcome report (executed, coupled)"
# Gap #9's DETECT half: gate-report.sh reads every .redgate/*/gates.log and
# flags approval fatigue — the shape where the human checkpoint has stopped
# discriminating. These checks EXECUTE the report against fixtures: gut the
# fatigue detection or the disposition parser and this group goes red. The
# negative control (a mixed corpus stays unflagged) is what makes the positive
# mean something.
GREPORT="$PLUGIN_DIR/skills/recurrence-detector/scripts/gate-report.sh"
if [ -f "$GREPORT" ] && bash -n "$GREPORT" 2>/dev/null; then ok "gate-report.sh exists and parses"; else bad "gate-report.sh missing or fails bash -n"; fi
_gr_tmp="$(mktemp -d)"
mkdir -p "$_gr_tmp/fatigued/.redgate/r" "$_gr_tmp/healthy/.redgate/r"
{ printf '# gates.log — round | class | driving-property | disposition | outcome | lesson\n'
  for i in 1 2 3 4 5; do printf '%s | MAJOR | decision %s | approved | granted | none\n' "$i" "$i"; done
} > "$_gr_tmp/fatigued/.redgate/r/gates.log"
{ printf '# gates.log — round | class | driving-property | disposition | outcome | lesson\n'
  printf '1 | MAJOR | plan approval | approved | granted | none\n'
  printf '2 | MAJOR | fence widening | revised | narrowed first | fence was too wide\n'
  printf '3 | MAJOR | budget extension | declined | held | overreach\n'
  printf '1 | PATCH | derived ratification | auto | auto-ratified | none\n'
  printf '1 | old-format line without class field\n'
} > "$_gr_tmp/healthy/.redgate/r/gates.log"
_out_f="$(bash "$GREPORT" --root "$_gr_tmp/fatigued" 2>&1)"; _rc_f=$?
_out_h="$(bash "$GREPORT" --root "$_gr_tmp/healthy" 2>&1)"; _rc_h=$?
if [ "$_rc_f" -eq 0 ] && printf '%s' "$_out_f" | grep -q 'approval-fatigue'; then
  ok "an all-approved MAJOR streak is flagged as approval fatigue"
else
  bad "5/5 approved MAJOR gates raised no fatigue flag — rubber-stamping is invisible"
fi
if [ "$_rc_h" -eq 0 ] && ! printf '%s' "$_out_h" | grep -q 'approval-fatigue'; then
  ok "NEGATIVE CONTROL: a mixed approved/revised/declined corpus is not flagged"
else
  bad "negative control failed — the fatigue flag fires on healthy corpora (or the report errored)"
fi
if printf '%s' "$_out_h" | grep -qE 'MAJOR +3 gates:.*approved=1' && printf '%s' "$_out_h" | grep -qE 'declined=1'; then
  ok "per-class disposition tallies are computed from the ledger"
else
  bad "disposition tallies are wrong or missing"
fi
if bash "$GREPORT" --root "$_gr_tmp" >/dev/null 2>&1; then
  bad "a root with no gates.log reported success — the empty case must refuse (exit 2)"
else
  ok "a root with no gate ledgers refuses instead of reporting an empty green"
fi
rm -rf "$_gr_tmp"
hasE "$SKILL" 'gate-report\.sh' \
  "the gather step runs gate-report.sh over the gate ledgers" \
  "gate-report.sh is not wired into the gather step"
hasE "$SKILL" 'approval fatigue|approval-fatigue' \
  "approval fatigue is named as a clusterable failure shape" \
  "the approval-fatigue shape is gone from the gather step"
