# Cheap eval pack for the 'egress-gate' plugin — SOURCED by evals/cheap/run.sh
# with cwd = repo root; inherits ok/bad/group/has/hasE/lacksE and
# $PLUGIN_NAME / $PLUGIN_DIR.
#
# What this defends: outbound content is enumerated (what, to whom) BEFORE the
# transmitting call, and secrets/out-of-scope content never ride in a payload.

SKILL="$PLUGIN_DIR/skills/egress-gate/SKILL.md"
AGENTS="$PLUGIN_DIR/AGENTS.md"
CMD="$PLUGIN_DIR/commands/egress-gate.md"

group "egress-gate — structure"
for f in "$PLUGIN_DIR/.claude-plugin/plugin.json" "$SKILL" "$AGENTS" "$PLUGIN_DIR/README.md" "$CMD"; do
  if [ -f "$f" ]; then ok "present: $f"; else bad "MISSING: $f"; fi
done

group "egress-gate — invariant survives verbatim"
INV='NEVER included in an outbound payload'
has "$SKILL"  "$INV" "SKILL.md carries the never-in-payload invariant verbatim" "SKILL.md lost the never-in-payload invariant"
has "$AGENTS" "$INV" "AGENTS.md carries the never-in-payload invariant verbatim" "AGENTS.md lost the never-in-payload invariant"
hasE "$SKILL" 'ALWAYS enumerated \(what, to whom\) before the' "SKILL.md requires enumeration BEFORE the transmitting call" "SKILL.md no longer requires pre-call enumeration"

group "egress-gate — the gate is three ordered steps"
hasE "$SKILL" '1\..*[Ee]numerate before transmitting' "step 1 (enumerate first) present" "step 1 (enumerate first) missing"
hasE "$SKILL" '2\..*[Ss]weep the payload' "step 2 (sweep the payload) present" "step 2 (sweep the payload) missing"
hasE "$SKILL" '3\..*[Uu]nnamed destination.*ask first' "step 3 (unnamed destination asks first) present" "step 3 (unnamed destination asks first) missing"

group "egress-gate — the sweep blocks, with no probably-fine branch"
hasE "$SKILL" 'the call until the payload is cleaned' "a sweep hit blocks the call until cleaned" "a sweep hit no longer blocks the call"
hasE "$SKILL" 'there is no .it.s probably' "SKILL.md forbids the probably-fine escape hatch" "SKILL.md lost the no-probably-fine rule"
hasE "$SKILL" 'keys, tokens' "the sweep names concrete secret shapes (keys, tokens)" "the sweep no longer names concrete secret shapes"

group "egress-gate — precedence: permission rules win, this gates content"
hasE "$SKILL" 'outright, that rule wins' "SKILL.md states a blocking permission rule always wins" "SKILL.md no longer cedes precedence to permission rules"
hasE "$SKILL" 'never argues a blocked call' "SKILL.md forbids arguing a blocked call back open" "SKILL.md lost the never-reopen rule"
hasE "$SKILL" 'payload of an already-permitted call' "SKILL.md scopes itself to content of permitted calls" "SKILL.md lost its content-not-calls scoping"

group "egress-gate — unnamed destinations wait for the user"
hasE "$SKILL" 'question rather than an announcement' "unnamed destination turns the manifest into a question" "the ask-first behavior for unnamed destinations is gone"
hasE "$CMD" 'manifest into a question and wait' "command restates ask-and-wait for unnamed destinations" "command lost the ask-and-wait rule"

group "egress-gate — disambiguated from siblings"
has "$SKILL" 'semver-gate' "SKILL.md disambiguates vs semver-gate (risk vs content)" "SKILL.md lost the semver-gate disambiguation"
has "$SKILL" 'scope-fence' "SKILL.md disambiguates vs scope-fence (diff vs payload)" "SKILL.md lost the scope-fence disambiguation"
