# Cheap eval pack for the 'semver-gate' plugin — SOURCED by evals/cheap/run.sh
# with cwd = repo root; inherits ok/bad/group/has/hasE/lacksE and
# $PLUGIN_NAME / $PLUGIN_DIR.
#
# What this defends: semver-gate's whole reason to exist is the invariant that
# a MAJOR-classified action never proceeds without explicit, specific human
# sign-off. These checks are deliberately paranoid about that ONE rule and
# comparatively loose about everything else the skill's prose says — a
# regression that silently weakens the MAJOR gate is the failure mode that
# matters; wording drift elsewhere is not what this tier exists to catch.
#
# This pack also defends the plugin's second skill, prove-the-undo (folded in
# from the former standalone prove-the-undo plugin, whose checks are carried
# over below under their original group names): an irreversible action is
# never justified by an unverified backup — the restore path must be named AND
# exercised in-session before the action proceeds. Same posture: paranoid about
# that one rule, loose about wording drift elsewhere.

SKILL="$PLUGIN_DIR/skills/semver-gate/SKILL.md"
RUBRIC="$PLUGIN_DIR/skills/semver-gate/references/rubric.md"
AGENTS="$PLUGIN_DIR/AGENTS.md"
UNDO_SKILL="$PLUGIN_DIR/skills/prove-the-undo/SKILL.md"
UNDO_CMD="$PLUGIN_DIR/commands/prove-the-undo.md"

# --- structure: the plugin's advertised surface actually exists ------------
group "semver-gate — structure"
for f in \
  "$PLUGIN_DIR/.claude-plugin/plugin.json" \
  "$SKILL" \
  "$RUBRIC" \
  "$AGENTS" \
  "$PLUGIN_DIR/README.md" \
  "$PLUGIN_DIR/commands/semver-gate.md"; do
  if [ -f "$f" ]; then ok "present: $f"; else bad "MISSING: $f"; fi
done

# --- all three tiers are named and distinct ---------------------------------
# The whole classifier is useless if a tier goes missing or two tiers collapse
# into synonyms. Assert each tier name appears in both SKILL.md and the rubric,
# and that the rubric's decision table carries three distinct tier columns.
group "semver-gate — three tiers named and distinct"
for tier in PATCH MINOR MAJOR; do
  if grep -q "$tier" "$SKILL"; then
    ok "SKILL.md names tier: $tier"
  else
    bad "SKILL.md is missing tier: $tier"
  fi
  if grep -q "$tier" "$RUBRIC"; then
    ok "rubric.md names tier: $tier"
  else
    bad "rubric.md is missing tier: $tier"
  fi
done
# Distinctness: the decision table's header row must carry all three tier
# names on one line (a table with a collapsed/merged column would drop one).
if grep -E '^\| Property \| PATCH \| MINOR \| MAJOR \|' "$RUBRIC" >/dev/null; then
  ok "rubric.md decision table header carries all three tiers as distinct columns"
else
  bad "rubric.md decision table header does not carry PATCH, MINOR, and MAJOR as three distinct columns"
fi

# --- MAJOR is never described as proceeding without a stop -----------------
# This is the load-bearing check. It fails closed two ways:
#   (a) the required "stop / ask / sign-off" language for MAJOR must be present
#   (b) no sentence may pair MAJOR with language that skips or waives the ask
group "semver-gate — MAJOR never proceeds without a stop"

# (a) required affirmative language: MAJOR must be tied to stopping and asking.
if grep -qiE 'MAJOR.{0,400}(stop before acting|stop.{0,20}ask|explicit.{0,20}(human )?sign-off)' "$SKILL"; then
  ok "SKILL.md ties MAJOR to an explicit stop-and-ask requirement"
else
  bad "SKILL.md does not clearly tie MAJOR to a stop-and-ask requirement"
fi
if grep -qiE '\| Stop before acting \|' "$RUBRIC"; then
  ok "rubric.md behavior-lookup table has MAJOR mapped to 'Stop before acting'"
else
  bad "rubric.md behavior-lookup table is missing the MAJOR -> 'Stop before acting' mapping"
fi

# (b) negation guard: reject phrasings that let MAJOR skip the ask. Scans the
# whole file for any MAJOR-tier action description paired with skip/bypass
# language within a short span, which would gut the invariant even if the
# affirmative language above is still technically present elsewhere.
BYPASS_RE='(skip|bypass|without asking|no need to ask|proceed without (confirmation|sign-off|approval)|do(es)? not (need|require) (sign-off|approval|confirmation))'
if grep -qiE "MAJOR.{0,200}$BYPASS_RE" "$SKILL" "$RUBRIC"; then
  bad "found MAJOR paired with skip/bypass language — the stop-before-acting invariant may have been weakened"
else
  ok "no MAJOR + skip/bypass phrasing found in SKILL.md or rubric.md"
fi

# The canonical skill carries the invariant; AGENTS is a discovery pointer.
INVARIANT_MARKER='must never be taken without explicit, specific prior'
if grep -qF "$INVARIANT_MARKER" "$SKILL"; then
  ok "SKILL.md carries the MAJOR sign-off invariant verbatim"
else
  bad "SKILL.md is missing the MAJOR sign-off invariant text"
fi
has "$AGENTS" "skills/semver-gate/SKILL.md" "AGENTS.md points to the canonical classifier" "AGENTS.md lost its classifier pointer"

# A prior adjacent "yes" must not be described as sufficient for MAJOR.
if grep -qiE 'adjacent.{0,100}(does not|doesn.t) transfer' "$SKILL"; then
  ok "SKILL.md states that an adjacent confirmation does not transfer to a MAJOR mechanism"
else
  bad "SKILL.md does not state that an adjacent/general confirmation fails to authorize a MAJOR action"
fi

# A structural block firing after sign-off must not be routed around.
if grep -qiE 'do not route around' "$SKILL"; then
  ok "SKILL.md forbids routing around a structural block that fires after sign-off"
else
  bad "SKILL.md does not forbid routing around a structural block after sign-off"
fi

# --- progressive disclosure: rubric exists AND is actually referenced ------
# Not enough for the file to exist — SKILL.md must link to it, or progressive
# disclosure is claimed but not wired.
group "semver-gate — progressive disclosure wired"
if [ -f "$RUBRIC" ]; then
  ok "rubric.md exists at skills/semver-gate/references/rubric.md"
else
  bad "rubric.md is missing"
fi
if grep -qF 'references/rubric.md' "$SKILL"; then
  ok "SKILL.md references references/rubric.md"
else
  bad "SKILL.md does not reference references/rubric.md — progressive disclosure not wired"
fi

# --- tie-break rule is present and matches the Conventional Commits borrow -
group "semver-gate — tie-break rule present"
if grep -qiE 'any single property.{0,80}MAJOR.{0,80}(whole action|makes the whole)' "$RUBRIC"; then
  ok "rubric.md states the tie-break rule (any MAJOR property -> whole action MAJOR)"
else
  bad "rubric.md is missing or has weakened the tie-break rule"
fi
if grep -qi 'Conventional Commits' "$SKILL" && grep -qi 'Conventional Commits' "$RUBRIC"; then
  ok "the Conventional Commits BREAKING CHANGE precedent is cited in both SKILL.md and rubric.md"
else
  bad "the Conventional Commits precedent for the tie-break rule is missing from SKILL.md or rubric.md"
fi

# --- precedence: settings.json autoMode and the system prompt are named ----
# The design brief is explicit that this skill sits BELOW two existing
# mechanisms and must name them, not gesture vaguely. Assert both are named
# with enough specificity to be greppable, not paraphrased into vagueness.
group "semver-gate — precedence over existing mechanisms is named, not vague"
if grep -qi 'autoMode' "$SKILL" && grep -qE 'hard_deny|soft_deny' "$SKILL"; then
  ok "SKILL.md names settings.json's autoMode hard_deny/soft_deny mechanism specifically"
else
  bad "SKILL.md does not specifically name autoMode's hard_deny/soft_deny mechanism"
fi
if grep -qi 'Executing actions with care' "$SKILL"; then
  ok "SKILL.md names the system prompt's 'Executing actions with care' section specifically"
else
  bad "SKILL.md does not specifically name the 'Executing actions with care' system-prompt section"
fi
if grep -qi 'always wins' "$SKILL"; then
  ok "SKILL.md states that a coded autoMode match always wins over this skill's table"
else
  bad "SKILL.md does not state that a coded autoMode match always wins"
fi

# Note: the scaffold's red-by-default sentinel is already checked globally by
# evals/cheap/run.sh section 8 (across all shipped plugins) — not duplicated
# here, since a self-referential grep for that literal inside this file would
# trip on its own pattern text.

# =============================================================================
# prove-the-undo — the plugin's second skill (folded in from the standalone
# prove-the-undo plugin; checks, patterns and messages carried over verbatim
# apart from the variable names and the shared AGENTS.md).
# =============================================================================

group "prove-the-undo — structure"
for f in "$UNDO_SKILL" "$UNDO_CMD"; do
  if [ -f "$f" ]; then ok "present: $f"; else bad "MISSING: $f"; fi
done

group "prove-the-undo — invariant survives verbatim"
INV='NEVER justified by the mere existence of an unverified backup'
has "$UNDO_SKILL"  "$INV" "SKILL.md carries the unverified-backup invariant verbatim" "SKILL.md lost the unverified-backup invariant"
has "$AGENTS" "skills/prove-the-undo/SKILL.md" "AGENTS.md points to the canonical restoration method" "AGENTS.md lost its restoration pointer"
hasE "$UNDO_SKILL" 'ALWAYS preceded by a named restore path' "SKILL.md requires a NAMED restore path before the action" "SKILL.md no longer requires a named restore path"
hasE "$UNDO_SKILL" 'exercised.*(restored, diffed, or dry-run-verified)' "SKILL.md requires the restore path be EXERCISED, not just named" "SKILL.md no longer requires exercising the restore path"

group "prove-the-undo — the rehearsal is three mandatory steps in order"
hasE "$UNDO_SKILL" '1\..*[Nn]ame the restore path' "step 1 (name the restore path) present" "step 1 (name the restore path) missing"
hasE "$UNDO_SKILL" '2\..*[Ee]xercise it now, in this session' "step 2 (exercise it in-session) present" "step 2 (exercise it in-session) missing"
hasE "$UNDO_SKILL" '3\..*[Aa]ttach the evidence' "step 3 (attach the evidence) present" "step 3 (attach the evidence) missing"
hasE "$UNDO_SKILL" 'Only after all three does the irreversible action proceed' "SKILL.md gates the action on all three steps" "SKILL.md no longer gates the action on all three steps"

group "prove-the-undo — verification failure blocks, never downgrades"
hasE "$UNDO_SKILL" 'If step 2 fails|fails or can.t be run' "SKILL.md handles the verification-failure branch" "SKILL.md is missing the verification-failure branch"
hasE "$UNDO_SKILL" 'the action is blocked' "verification failure blocks the action" "verification failure no longer blocks the action"
hasE "$UNDO_SKILL" 'never downgrade' "SKILL.md forbids downgrading to an assumed-good backup" "SKILL.md no longer forbids downgrading"

group "prove-the-undo — delegated scripts must self-gate"
hasE "$UNDO_SKILL" 'gate the destructive step on the verification' "SKILL.md requires generated scripts to gate deletion on verification" "SKILL.md no longer requires generated scripts to self-gate"
hasE "$UNDO_CMD" 'destructive step on the verification inside the script' "command restates the script self-gating rule" "command lost the script self-gating rule"

group "prove-the-undo — disambiguated from siblings"
has "$UNDO_SKILL" 'semver-gate' "SKILL.md disambiguates vs semver-gate (classify vs rehearse)" "SKILL.md lost the semver-gate disambiguation"
has "$UNDO_SKILL" 'graveyard' "SKILL.md names graveyard as the concrete instance of this discipline" "SKILL.md lost the graveyard lineage note"
hasE "$UNDO_SKILL" 'human sign-off does not substitute' "SKILL.md states human sign-off never substitutes for the rehearsal" "SKILL.md no longer states sign-off does not substitute for rehearsal"
