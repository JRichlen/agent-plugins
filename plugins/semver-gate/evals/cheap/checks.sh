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

SKILL="$PLUGIN_DIR/skills/semver-gate/SKILL.md"
RUBRIC="$PLUGIN_DIR/skills/semver-gate/references/rubric.md"
AGENTS="$PLUGIN_DIR/AGENTS.md"

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

# Explicit invariant text must survive verbatim in both SKILL.md and AGENTS.md
# (the scaffold wrote it into both at generation time from --invariant).
INVARIANT_MARKER='must never be taken without explicit, specific prior'
if grep -qF "$INVARIANT_MARKER" "$SKILL"; then
  ok "SKILL.md carries the MAJOR sign-off invariant verbatim"
else
  bad "SKILL.md is missing the MAJOR sign-off invariant text"
fi
if grep -qF "$INVARIANT_MARKER" "$AGENTS"; then
  ok "AGENTS.md carries the MAJOR sign-off invariant verbatim"
else
  bad "AGENTS.md is missing the MAJOR sign-off invariant text"
fi

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
