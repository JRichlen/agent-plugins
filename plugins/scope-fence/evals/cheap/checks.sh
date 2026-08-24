# Cheap eval pack for the 'scope-fence' plugin — SOURCED by evals/cheap/run.sh
# with cwd = repo root; inherits ok/bad/group/has/hasE/lacksE and
# $PLUGIN_NAME / $PLUGIN_DIR.
#
# What this defends: every hunk traces to the stated task, and out-of-scope
# discoveries become recorded findings — never same-change fixes, never
# silent drops. Paranoid about that rule; loose about everything else.

SKILL="$PLUGIN_DIR/skills/scope-fence/SKILL.md"
AGENTS="$PLUGIN_DIR/AGENTS.md"
CMD="$PLUGIN_DIR/commands/scope-fence.md"

group "scope-fence — structure"
for f in "$PLUGIN_DIR/.claude-plugin/plugin.json" "$SKILL" "$AGENTS" "$PLUGIN_DIR/README.md" "$CMD"; do
  if [ -f "$f" ]; then ok "present: $f"; else bad "MISSING: $f"; fi
done

group "scope-fence — invariant survives verbatim"
INV='ALWAYS recorded as findings and NEVER folded'
has "$SKILL"  "$INV" "SKILL.md carries the never-folded-in invariant verbatim" "SKILL.md lost the never-folded-in invariant"
has "$AGENTS" "$INV" "AGENTS.md carries the never-folded-in invariant verbatim" "AGENTS.md lost the never-folded-in invariant"
hasE "$SKILL" 'ALWAYS traces to the stated task' "SKILL.md requires every hunk trace to the stated task" "SKILL.md no longer requires hunk-to-task tracing"
hasE "$SKILL" 'ALWAYS recorded as findings' "SKILL.md requires discoveries be recorded as findings" "SKILL.md no longer requires recording findings"

group "scope-fence — the fence workflow is complete and ordered"
hasE "$SKILL" '1\..*[Ss]tate the fence before the first edit' "step 1 (state the fence first) present" "step 1 (state the fence first) missing"
hasE "$SKILL" '2\..*[Rr]oute discoveries' "step 2 (route discoveries) present" "step 2 (route discoveries) missing"
hasE "$SKILL" '3\..*[Aa]udit the diff before declaring done' "step 3 (audit the diff) present" "step 3 (audit the diff) missing"
hasE "$SKILL" '4\..*[Ww]idening is the user.s move' "step 4 (only the user widens) present" "step 4 (only the user widens) missing"

group "scope-fence — silent drops are as forbidden as silent fixes"
hasE "$SKILL" 'silently ignoring a discovery is as much a violation' "SKILL.md makes recording mandatory" "SKILL.md no longer makes recording mandatory"
hasE "$SKILL" 'Recording is' "SKILL.md makes recording mandatory (lead-in present)" "SKILL.md lost the recording-mandatory lead-in"

group "scope-fence — the audit has teeth (revert-and-convert)"
hasE "$SKILL" 'revert it and convert it to a finding' "audit failure means revert + convert, not keep" "audit failure no longer requires revert + convert"
hasE "$SKILL" 'fence moves only by explicit instruction' "the fence widens only on explicit user instruction" "the explicit-instruction widening rule is gone"
hasE "$CMD" 'revert hunks that trace only to discoveries' "command restates the revert rule for existing diffs" "command lost the revert rule"

group "scope-fence — disambiguated from siblings"
has "$SKILL" 'semver-gate' "SKILL.md disambiguates vs semver-gate (risk vs belonging)" "SKILL.md lost the semver-gate disambiguation"
has "$SKILL" 'wayfinder' "SKILL.md names wayfinder tickets as a findings destination" "SKILL.md lost the wayfinder disambiguation"
