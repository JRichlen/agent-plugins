# Cheap eval pack for the 'stop-rule' plugin — SOURCED by evals/cheap/run.sh
# with cwd = repo root; inherits ok/bad/group/has/hasE/lacksE and
# $PLUGIN_NAME / $PLUGIN_DIR.
#
# What this defends: a bound declared up front, honest per-objective counting,
# and a mandatory stop-and-report at the bound — never attempt N+1 on momentum.

SKILL="$PLUGIN_DIR/skills/stop-rule/SKILL.md"
AGENTS="$PLUGIN_DIR/AGENTS.md"
CMD="$PLUGIN_DIR/commands/stop-rule.md"

group "stop-rule — structure"
for f in "$PLUGIN_DIR/.claude-plugin/plugin.json" "$SKILL" "$AGENTS" "$PLUGIN_DIR/README.md" "$CMD"; do
  if [ -f "$f" ]; then ok "present: $f"; else bad "MISSING: $f"; fi
done

group "stop-rule — invariant survives verbatim"
INV='NEVER a further attempt on momentum'
has "$SKILL"  "$INV" "SKILL.md carries the never-on-momentum invariant verbatim" "SKILL.md lost the never-on-momentum invariant"
has "$AGENTS" "$INV" "AGENTS.md carries the never-on-momentum invariant verbatim" "AGENTS.md lost the never-on-momentum invariant"
hasE "$SKILL" 'counted against a bound declared up' "SKILL.md requires the bound be declared up front" "SKILL.md no longer requires an up-front bound"
hasE "$SKILL" 'ALWAYS produces a stop-and-report' "SKILL.md makes the stop-report mandatory at the bound" "SKILL.md no longer mandates the stop-report"

group "stop-rule — the rule is four ordered steps"
hasE "$SKILL" '1\..*[Dd]eclare the bound at attempt one' "step 1 (declare the bound at attempt one) present" "step 1 (declare the bound) missing"
hasE "$SKILL" '2\..*[Cc]ount honestly, per objective' "step 2 (count honestly) present" "step 2 (count honestly) missing"
hasE "$SKILL" '3\..*[Dd]iagnosis resets; momentum doesn.t' "step 3 (diagnosis resets, momentum doesn't) present" "step 3 (reset rule) missing"
hasE "$SKILL" '4\..*[Aa]t the bound: stop and report' "step 4 (stop and report at the bound) present" "step 4 (stop and report) missing"

group "stop-rule — default bounds are concrete numbers"
hasE "$SKILL" 'Default bound.*\*\*3\*\*.*pushes' "default bound of 3 for externally visible attempts is stated" "the default bound of 3 for pushes is gone"
hasE "$SKILL" '\*\*5\*\*[[:space:]]*for purely local retries' "default bound of 5 for local retries is stated" "the default bound of 5 for local retries is gone"
hasE "$SKILL" 'bound chosen while at the limit is a rationalization' "SKILL.md forbids picking the bound at the limit" "SKILL.md lost the no-retroactive-bound rule"

group "stop-rule — counter-reset cheats are named and blocked"
hasE "$SKILL" 'Reframing the objective to reset the counter' "SKILL.md names the reframe-to-reset cheat" "SKILL.md lost the reframe-to-reset prohibition"
hasE "$SKILL" 'root cause was actually established' "the counter resets only on a confirmed root cause" "the confirmed-root-cause reset condition is gone"
hasE "$SKILL" 'resets nothing' "a better feeling explicitly resets nothing" "the feelings-reset-nothing line is gone"

group "stop-rule — the stop-report has required contents"
hasE "$SKILL" 'literal failure output, not paraphrase' "the report requires literal failure output" "the literal-output requirement is gone"
hasE "$SKILL" 'ranked hypotheses' "the report requires ranked hypotheses" "the ranked-hypotheses requirement is gone"
hasE "$SKILL" 'what evidence would confirm or kill it' "each hypothesis carries its confirming/killing evidence" "the per-hypothesis evidence requirement is gone"
hasE "$CMD" 'instead of making attempt N\+1' "command ends the loop at the bound, not after one more try" "command lost the no-attempt-N+1 rule"

group "stop-rule — disambiguated from siblings"
has "$SKILL" 'diagnosing-bugs' "SKILL.md hands off to diagnosing-bugs at the stop" "SKILL.md lost the diagnosing-bugs handoff"
has "$SKILL" 'verify-before-claim' "SKILL.md names the verify-before-claim overlap" "SKILL.md lost the verify-before-claim disambiguation"
