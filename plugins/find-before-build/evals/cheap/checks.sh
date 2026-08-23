# Cheap eval pack for the 'find-before-build' plugin — SOURCED by
# evals/cheap/run.sh with cwd = repo root; inherits ok/bad/group/has/hasE/lacksE
# and $PLUGIN_NAME / $PLUGIN_DIR.
#
# What this defends: no new abstraction without named searches and their shown
# results first — and never a parallel version of a found, usable equivalent.

SKILL="$PLUGIN_DIR/skills/find-before-build/SKILL.md"
AGENTS="$PLUGIN_DIR/AGENTS.md"
CMD="$PLUGIN_DIR/commands/find-before-build.md"

group "find-before-build — structure"
for f in "$PLUGIN_DIR/.claude-plugin/plugin.json" "$SKILL" "$AGENTS" "$PLUGIN_DIR/README.md" "$CMD"; do
  if [ -f "$f" ]; then ok "present: $f"; else bad "MISSING: $f"; fi
done

group "find-before-build — invariant survives verbatim"
INV='NEVER introduced when an existing equivalent was found and usable'
has "$SKILL"  "$INV" "SKILL.md carries the never-parallel-build invariant verbatim" "SKILL.md lost the never-parallel-build invariant"
has "$AGENTS" "$INV" "AGENTS.md carries the never-parallel-build invariant verbatim" "AGENTS.md lost the never-parallel-build invariant"
hasE "$SKILL" 'by named searches for an existing equivalent' "SKILL.md requires named searches before building" "SKILL.md no longer requires named searches first"
hasE "$SKILL" 'results shown' "SKILL.md requires search results be shown, not just claimed" "SKILL.md no longer requires shown results"

group "find-before-build — the gate is four ordered steps"
hasE "$SKILL" '1\..*[Nn]ame what you.re about to build' "step 1 (name the thing) present" "step 1 (name the thing) missing"
hasE "$SKILL" '2\..*[Rr]un at least two searches from different angles' "step 2 (two+ searches, different angles) present" "step 2 (two+ searches) missing"
hasE "$SKILL" '3\..*[Ss]how the receipt' "step 3 (show the receipt) present" "step 3 (show the receipt) missing"
hasE "$SKILL" '4\..*[Dd]ecide by the receipt' "step 4 (decide by the receipt) present" "step 4 (decide by the receipt) missing"
hasE "$SKILL" 'empty is not looking' "SKILL.md rejects a single empty grep as a real search" "SKILL.md no longer rejects the single-empty-grep dodge"

group "find-before-build — usability is not taste"
hasE "$SKILL" 'not-invented-here is not unusability|Preference,[[:space:]]*style' "SKILL.md excludes preference/NIH from 'unusable'" "SKILL.md no longer excludes preference/NIH from 'unusable'"
hasE "$SKILL" 'do not write the parallel version' "found-and-usable forbids the parallel implementation" "the parallel-implementation prohibition is gone"
hasE "$SKILL" 'unusable.*say why|say why.*unusable' "declaring a found equivalent unusable requires a stated reason" "the stated-reason requirement for 'unusable' is gone"

group "find-before-build — receipt lands where work is reported"
hasE "$SKILL" 'receipt appears wherever the work is reported' "SKILL.md requires the receipt in the reported output" "SKILL.md no longer requires the receipt in reported output"
hasE "$CMD" 'searches verbatim' "command requires searches be quoted verbatim in the receipt" "command lost the verbatim-searches requirement"

group "find-before-build — disambiguated from siblings"
has "$SKILL" 'codebase-design' "SKILL.md hands off to codebase-design only after an empty search" "SKILL.md lost the codebase-design handoff"
has "$SKILL" 'verify-before-claim' "SKILL.md positions the receipt as a verify-before-claim claim shape" "SKILL.md lost the verify-before-claim disambiguation"
