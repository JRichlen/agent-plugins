# Cheap eval pack for the 'consolidation-map' plugin — SOURCED by
# evals/cheap/run.sh with cwd = repo root; inherits ok/bad/group/has/hasE/lacksE
# and $PLUGIN_NAME / $PLUGIN_DIR.
#
# What this defends: every entity gets exactly one disposition, the counts
# reconcile, and a map that does not reconcile is reported as failing — never
# presented as done and never filled in with an invented decision. Checks are
# scoped to the section that owns each rule, so a restatement elsewhere in the
# file cannot stand in for the operative text.

SKILL="$PLUGIN_DIR/skills/consolidation-map/SKILL.md"
AGENTS="$PLUGIN_DIR/AGENTS.md"
CMD="$PLUGIN_DIR/commands/consolidation-map.md"

# section FILE HEADING — print the body of a `## HEADING` section (to the next
# `## ` heading), anchored on the heading line itself.
section() { awk -v h="## $2" '$0==h{on=1;next} /^## /{on=0} on' "$1"; }
# in_section FILE HEADING REGEX OK FAIL — regex must match inside that section.
in_section() { if section "$1" "$2" | grep -qE "$3"; then ok "$4"; else bad "$5"; fi; }

group "consolidation-map — structure"
for f in "$PLUGIN_DIR/.claude-plugin/plugin.json" "$SKILL" "$AGENTS" "$PLUGIN_DIR/README.md" "$CMD"; do
  if [ -f "$f" ]; then ok "present: $f"; else bad "MISSING: $f"; fi
done
for h in "Invariant" "Not this" "When to use this" "Inputs" "The verbs" "The map" "Reconciliation" "Delegation"; do
  if grep -qxF "## $h" "$SKILL"; then ok "SKILL.md has the '## $h' section"; else bad "SKILL.md lost the '## $h' section"; fi
done

group "consolidation-map — invariant survives verbatim"
INV='appears in exactly one disposition row'
in_section "$SKILL" "Invariant" "$INV" "SKILL.md Invariant section carries the one-row-per-entity rule" "SKILL.md Invariant lost the one-row-per-entity rule"
in_section "$SKILL" "Invariant" 'NEVER presented as done' "SKILL.md Invariant forbids presenting a failed map as done" "SKILL.md Invariant lost the never-presented-as-done clause"
in_section "$SKILL" "Invariant" 'NEVER filled in with a' "SKILL.md Invariant forbids inventing decisions" "SKILL.md Invariant lost the never-invent-a-decision clause"
has "$AGENTS" 'NEVER presented as done, and NEVER filled in with a decision the user did not make' "AGENTS.md carries the invariant's NEVER clauses verbatim" "AGENTS.md lost the invariant's NEVER clauses"

group "consolidation-map — the verbs are the closed set of six"
for v in keep new absorb merge-into deprecate retire; do
  if section "$SKILL" "The verbs" | grep -qE "^\| $v \|"; then ok "verb table has a '$v' row"; else bad "verb table lost the '$v' row"; fi
done
rows="$(section "$SKILL" "The verbs" | grep -cE '^\| (keep|new|absorb|merge-into|deprecate|retire) \|')"
total="$(section "$SKILL" "The verbs" | grep -E '^\| ' | grep -vcE '^\| (Verb|---)')"
if [ "$rows" = 6 ] && [ "$total" = 6 ]; then ok "verb table has exactly the six verbs and no others"; else bad "verb table is not exactly the six verbs (named $rows, total $total)"; fi
in_section "$SKILL" "The verbs" '^\| deprecate \|.*\| kept \|' "deprecate counts as kept (still present in the after-list)" "deprecate no longer counts as kept"
in_section "$SKILL" "The verbs" '^\| absorb \|.*\| kept \|' "absorb counts as kept" "absorb no longer counts as kept"
in_section "$SKILL" "The verbs" '^\| merge-into \|.*\| merged-away \|' "merge-into counts as merged-away" "merge-into no longer counts as merged-away"

group "consolidation-map — missing decisions are asked for, never invented"
in_section "$SKILL" "Inputs" 'If a decision is missing for any entity, ask' "Inputs requires asking for a missing decision" "Inputs lost the ask-for-missing-decisions rule"
in_section "$SKILL" "Inputs" 'never infer it from' "Inputs forbids inferring a disposition from the diff" "Inputs lost the never-infer-from-the-diff rule"
in_section "$SKILL" "Inputs" 'UNDECIDED' "Inputs names undecided entities as UNDECIDED" "Inputs lost the UNDECIDED marker"

group "consolidation-map — the map is grouped by unit of work"
in_section "$SKILL" "The map" 'Group by \*\*unit of work\*\*' "The map groups by unit of work" "The map no longer groups by unit of work"
in_section "$SKILL" "The map" 'Omit empty groups' "The map omits empty groups" "The map lost the omit-empty-groups rule"
in_section "$SKILL" "The map" "What's lost:" "each unit carries a What's lost line" "units lost the What's lost line"
in_section "$SKILL" "The map" '\*\*Why:\*\*' "each unit carries a Why line" "units lost the Why line"
in_section "$SKILL" "The map" 'If you cannot say, say that' "'nothing' may not be written when the loss is unknown" "lost the no-reflexive-'nothing' rule"
in_section "$SKILL" "The map" 'Before N \| After M' "the map leads with the Before/After counts line" "the map lost its counts line"

in_section "$SKILL" "The map" 'write "not recorded" rather than supply one' "a Why that was never recorded is marked, not invented" "the not-recorded rule for Why lines is gone"

group "consolidation-map — reconciliation fails loudly"
in_section "$SKILL" "Reconciliation" 'Before = kept \+ merged-away \+ retired' "before = kept + merged-away + retired" "the before formula is gone"
in_section "$SKILL" "Reconciliation" 'After = kept \+ new' "after = kept + new" "the after formula is gone"
in_section "$SKILL" "Reconciliation" 'no entity in two rows, none in' "rows are checked, not only totals (no entity in two rows)" "the per-row check is gone"
in_section "$SKILL" "Reconciliation" 'merge-into target is itself in the after-list' "every merge-into target must survive" "the surviving-target check is gone"
in_section "$SKILL" "Reconciliation" '`RECONCILIATION FAILED`, list the offending' "a mismatch prints RECONCILIATION FAILED" "the loud-failure marker is gone"
in_section "$SKILL" "Reconciliation" 'while any entity is .UNDECIDED.' "an UNDECIDED entity fails reconciliation" "an UNDECIDED entity no longer fails reconciliation"
in_section "$SKILL" "Reconciliation" 'Do not adjust' "counts may not be adjusted to balance" "the no-adjusting-counts rule is gone"
has "$CMD" 'RECONCILIATION FAILED' "command restates the loud failure" "command lost the loud failure"

group "consolidation-map — delegation names tiers, not other plugins"
in_section "$SKILL" "Delegation" 'cheapest, fastest tier' "bulk reading goes to the cheapest tier" "bulk-reading tier is gone"
in_section "$SKILL" "Delegation" 'mid tier' "judgment goes to a mid tier" "judgment tier is gone"
in_section "$SKILL" "Delegation" 'strongest tier available' "verification goes to the strongest tier" "verification tier is gone"
in_section "$SKILL" "Delegation" 'different run from the one that wrote' "verification is a different run from the author's" "verifier-independence is gone"
in_section "$SKILL" "Delegation" 'Only the parent asks the user' "only the parent asks the user" "the parent-only-asks rule is gone"
# Every plugins/<name> path the skill cites must exist in THIS marketplace.
for n in $(grep -oE 'plugins/[a-z0-9-]+' "$SKILL" | sort -u | sed 's#plugins/##'); do
  if [ -d "plugins/$n" ]; then ok "SKILL.md cites plugins/$n, which exists"; else bad "SKILL.md cites plugins/$n, which is not in this marketplace"; fi
done

group "consolidation-map — disambiguated from neighbours"
for n in docs-hygiene graveyard semver-gate; do
  in_section "$SKILL" "Not this" "\*\*$n\*\* \(\`plugins/$n\`\)" "'Not this' points at $n" "'Not this' lost the $n pointer"
  if [ -d "plugins/$n" ]; then ok "$n exists in this marketplace"; else bad "'Not this' names $n, which is not installed"; fi
done
in_section "$SKILL" "Not this" 'never removes, moves or archives' "the skill never removes, moves or archives anything" "the describes-only guarantee is gone"
