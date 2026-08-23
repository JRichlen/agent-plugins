# Cheap eval pack for the 'prove-the-undo' plugin — SOURCED by evals/cheap/run.sh
# with cwd = repo root; inherits ok/bad/group/has/hasE/lacksE and
# $PLUGIN_NAME / $PLUGIN_DIR.
#
# What this defends: the invariant that an irreversible action is never
# justified by an unverified backup — the restore path must be named AND
# exercised in-session before the action proceeds. These checks are paranoid
# about that one rule; wording drift elsewhere is not what this tier catches.

SKILL="$PLUGIN_DIR/skills/prove-the-undo/SKILL.md"
AGENTS="$PLUGIN_DIR/AGENTS.md"
CMD="$PLUGIN_DIR/commands/prove-the-undo.md"

group "prove-the-undo — structure"
for f in "$PLUGIN_DIR/.claude-plugin/plugin.json" "$SKILL" "$AGENTS" "$PLUGIN_DIR/README.md" "$CMD"; do
  if [ -f "$f" ]; then ok "present: $f"; else bad "MISSING: $f"; fi
done

group "prove-the-undo — invariant survives verbatim"
INV='NEVER justified by the mere existence of an unverified backup'
has "$SKILL"  "$INV" "SKILL.md carries the unverified-backup invariant verbatim" "SKILL.md lost the unverified-backup invariant"
has "$AGENTS" "$INV" "AGENTS.md carries the unverified-backup invariant verbatim" "AGENTS.md lost the unverified-backup invariant"
hasE "$SKILL" 'ALWAYS preceded by a named restore path' "SKILL.md requires a NAMED restore path before the action" "SKILL.md no longer requires a named restore path"
hasE "$SKILL" 'exercised.*(restored, diffed, or dry-run-verified)' "SKILL.md requires the restore path be EXERCISED, not just named" "SKILL.md no longer requires exercising the restore path"

group "prove-the-undo — the rehearsal is three mandatory steps in order"
hasE "$SKILL" '1\..*[Nn]ame the restore path' "step 1 (name the restore path) present" "step 1 (name the restore path) missing"
hasE "$SKILL" '2\..*[Ee]xercise it now, in this session' "step 2 (exercise it in-session) present" "step 2 (exercise it in-session) missing"
hasE "$SKILL" '3\..*[Aa]ttach the evidence' "step 3 (attach the evidence) present" "step 3 (attach the evidence) missing"
hasE "$SKILL" 'Only after all three does the irreversible action proceed' "SKILL.md gates the action on all three steps" "SKILL.md no longer gates the action on all three steps"

group "prove-the-undo — verification failure blocks, never downgrades"
hasE "$SKILL" 'If step 2 fails|fails or can.t be run' "SKILL.md handles the verification-failure branch" "SKILL.md is missing the verification-failure branch"
hasE "$SKILL" 'the action is blocked' "verification failure blocks the action" "verification failure no longer blocks the action"
hasE "$SKILL" 'never downgrade' "SKILL.md forbids downgrading to an assumed-good backup" "SKILL.md no longer forbids downgrading"

group "prove-the-undo — delegated scripts must self-gate"
hasE "$SKILL" 'gate the destructive step on the verification' "SKILL.md requires generated scripts to gate deletion on verification" "SKILL.md no longer requires generated scripts to self-gate"
hasE "$CMD" 'destructive step on the verification inside the script' "command restates the script self-gating rule" "command lost the script self-gating rule"

group "prove-the-undo — disambiguated from siblings"
has "$SKILL" 'semver-gate' "SKILL.md disambiguates vs semver-gate (classify vs rehearse)" "SKILL.md lost the semver-gate disambiguation"
has "$SKILL" 'graveyard' "SKILL.md names graveyard as the concrete instance of this discipline" "SKILL.md lost the graveyard lineage note"
hasE "$SKILL" 'human sign-off does not substitute' "SKILL.md states human sign-off never substitutes for the rehearsal" "SKILL.md no longer states sign-off does not substitute for rehearsal"
