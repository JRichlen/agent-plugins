# grill-me — plugin-specific cheap checks.
#
# SOURCED by the shared runner (evals/cheap/run.sh), not run standalone: it
# inherits that runner's helpers (ok/bad/group/has/hasE/lacksE), its
# `set -uo pipefail`, a working directory of the repo root, and the exported
# PLUGIN_NAME / PLUGIN_DIR.
#
# grill-me ships prose, not scripts, so what the cheap tier defends is the
# INVARIANT's own load-bearing shape in that prose: the two-axis stakes table
# actually exists, every question format carries an adjacent recommendation,
# the "Not this" differentiation actually names the two adjacent plugins (so
# the three skills don't collide on triggers), the description/trigger set
# excludes the phrases that would collide with them, and the lean-file design
# budget on SKILL.md doesn't quietly regress as the skill gets edited. Each of
# these is easy to silently break (soften a table into prose, drop the
# recommendation glyph from one branch, let SKILL.md creep past its budget)
# while the file still parses and reads fine — that's exactly the kind of
# regression a grep-only "file exists" check would miss.

SKILL_DIR="$PLUGIN_DIR/skills/grill-me"
SKILL="$SKILL_DIR/SKILL.md"
REFS="$SKILL_DIR/references"

# --- structure: the plugin's advertised surface actually exists ------------
group "grill-me — structure"
for f in \
  "$PLUGIN_DIR/.claude-plugin/plugin.json" \
  "$SKILL" \
  "$REFS/technique.md" \
  "$REFS/path-consent.md" \
  "$REFS/fact-finding.md" \
  "$REFS/stakes-examples.md" \
  "$PLUGIN_DIR/README.md" \
  "$PLUGIN_DIR/commands/grill-me.md"; do
  if [ -f "$f" ]; then ok "present: $f"; else bad "MISSING: $f"; fi
done

# --- (a) two-axis stakes table: both axes named, all three tiers named -----
group "grill-me — two-axis stakes triage"
hasE "$SKILL" 'Reversibility|[Tt]wo-way door|[Oo]ne-way door' \
  "SKILL.md names reversibility (two-way/one-way door)" \
  "SKILL.md is missing the reversibility axis of the stakes table"
hasE "$SKILL" 'Blast radius|blast radius' \
  "SKILL.md names blast radius" \
  "SKILL.md is missing the blast-radius axis of the stakes table"
for tier in LIGHT STANDARD DEEP; do
  has "$SKILL" "$tier" \
    "SKILL.md defines the $tier tier" \
    "SKILL.md is missing the $tier tier — dynamic depth-scaling needs all three"
done

# --- dynamic-depth language (invariant: sized per branch, not fixed) -------
group "grill-me — dynamic-depth language"
hasE "$SKILL" 'per branch|each branch|stakes tier' \
  "SKILL.md states depth is computed per branch" \
  "SKILL.md doesn't say depth is sized per branch — invariant may be unstated"
hasE "$SKILL" 'fixed-depth|fixed-count|NEVER run a fixed' \
  "SKILL.md explicitly rules out a fixed-depth/fixed-count script" \
  "SKILL.md never explicitly rules out fixed-depth questioning"

# --- (b) recommendation glyph adjacent to the question glyph everywhere ----
group "grill-me — assistive-recommendation format"
Q_COUNT=$(grep -c '❓' "$SKILL" 2>/dev/null || echo 0)
REC_COUNT=$(grep -c '➡️' "$SKILL" 2>/dev/null || echo 0)
if [ "$Q_COUNT" -gt 0 ]; then ok "SKILL.md defines the ❓ question glyph"; else bad "SKILL.md never defines the ❓ question glyph"; fi
if [ "$REC_COUNT" -gt 0 ]; then ok "SKILL.md defines the ➡️ recommendation glyph"; else bad "SKILL.md never defines the ➡️ recommendation glyph"; fi
# The format block must show them adjacent (recommendation line directly
# follows the question line) — not just present somewhere independently.
if grep -A1 '❓ Qn' "$SKILL" 2>/dev/null | grep -q '➡️'; then
  ok "➡️ recommendation line appears directly under the ❓ question format"
else
  bad "➡️ recommendation is not shown adjacent to the ❓ question format — the assistive mechanic may have been decoupled"
fi

# --- (c) "Not this" differentiation names both adjacent plugins ------------
group "grill-me — differentiation from adjacent plugins"
has "$SKILL" "Not this" \
  "SKILL.md has an explicit 'Not this' section" \
  "SKILL.md is missing the 'Not this' differentiation section"
has "$SKILL" "second-opinion" \
  "SKILL.md names second-opinion by name" \
  "SKILL.md doesn't name second-opinion — differentiation is incomplete"
hasE "$SKILL" 'orchestrat' \
  "SKILL.md names orchestrate/orchestration-patterns by name" \
  "SKILL.md doesn't name orchestrate/orchestration-patterns — differentiation is incomplete"

# --- (e) anchor + path consent: goal before depth, consent before descent --
# The waste this stops: a deep question series fired on a branch the user
# never wanted explored, before goal/outcome were ever confirmed. Easy to
# silently drop (delete the section, SKILL.md still reads fine), so grep the
# load-bearing shape: the anchor precedes branch questioning, the consent
# routing menu exists with all four routes, and the reference is linked from
# SKILL.md (not just present on disk — an unlinked reference is inert).
group "grill-me — anchor and path consent"
hasE "$SKILL" 'No branch questioning before the \*\*anchor\*\*|anchor.*is set' \
  "SKILL.md requires the anchor before any branch questioning" \
  "SKILL.md no longer requires an anchor before branch questioning"
hasE "$SKILL" 'explore / accept / defer / out-of-scope' \
  "SKILL.md carries the four-route consent menu" \
  "SKILL.md lost the explore/accept/defer/out-of-scope consent menu"
has "$SKILL" 'references/path-consent.md' \
  "SKILL.md links references/path-consent.md" \
  "path-consent.md is not linked from SKILL.md — the mechanic is inert"
hasE "$REFS/path-consent.md" 'LIGHT branches never get a consent header' \
  "path-consent.md exempts LIGHT branches from consent headers" \
  "the LIGHT exemption is gone — consent spam on trivial branches"
hasE "$REFS/path-consent.md" 'one-way door cannot be quietly' \
  "path-consent.md keeps the irreversibility exception on defer" \
  "the irreversibility exception is gone — one-way doors can be silently deferred"

# --- frontier/round loop mechanic present -----------------------------------
group "grill-me — frontier/round loop"
has "$SKILL" "frontier" \
  "SKILL.md describes the frontier mechanic" \
  "SKILL.md never mentions the frontier — the round loop may be missing"
hasE "$SKILL" 'Qn|numbered round' \
  "SKILL.md describes numbered rounds (Q1, Q2, ...)" \
  "SKILL.md doesn't describe numbered rounds"

# --- termination: recap categories present ----------------------------------
group "grill-me — termination recap"
for cat in "Confirmed Decisions" "Open Risks Accepted As-Is" "Deferred-for-Later"; do
  has "$SKILL" "$cat" \
    "SKILL.md's recap includes '$cat'" \
    "SKILL.md's recap is missing '$cat'"
done

# --- (d) line-count budget on SKILL.md --------------------------------------
group "grill-me — SKILL.md line-count budget"
LINES=$(wc -l < "$SKILL" | tr -d ' ')
BUDGET=140
if [ "$LINES" -le "$BUDGET" ]; then
  ok "SKILL.md is $LINES lines (budget: <=$BUDGET) — stays lean/resident"
else
  bad "SKILL.md is $LINES lines, over the $BUDGET-line budget — progressive-disclosure design has regressed; move detail into references/"
fi

# --- does NOT claim to run unbidden / auto-trigger without the user --------
# grill-me is explicitly invoked (a skill trigger or /grill-me), unlike
# second-opinion's stricter "never auto-run" gate. This check guards against
# copy-pasting second-opinion's specific unbidden-safety language in a way
# that would blur the two skills' actual differentiation.
group "grill-me — does not claim second-opinion's unbidden-safety property"
lacksE "$SKILL" 'run unbidden|never auto-run' \
  "SKILL.md doesn't borrow second-opinion's 'never run unbidden' framing" \
  "SKILL.md claims a 'never run unbidden' property — that's second-opinion's specific safety language; remove it here to keep differentiation clean"

# --- trigger-set / description excludes colliding phrases ------------------
group "grill-me — description excludes colliding trigger phrases"
DESC=$(python3 -c "
import json
d = json.load(open('$PLUGIN_DIR/.claude-plugin/plugin.json'))
print(d.get('description', '').lower())
")
collision=0
for phrase in "second opinion" "validate" "fan out" "research and verify"; do
  if printf '%s' "$DESC" | grep -qF "$phrase"; then
    bad "plugin.json description contains colliding trigger phrase '$phrase'"
    collision=$((collision+1))
  fi
done
[ "$collision" -eq 0 ] && ok "plugin.json description excludes second-opinion's and orchestrate's trigger phrases"

# --- attribution note present ------------------------------------------------
group "grill-me — attribution to Matt Pocock's prior art"
has "$PLUGIN_DIR/README.md" "Pocock" \
  "README.md credits Matt Pocock's original grill-me/grilling skills" \
  "README.md is missing the Pocock attribution note"
has "$PLUGIN_DIR/README.md" "mattpocock/skills" \
  "README.md links to github.com/mattpocock/skills" \
  "README.md is missing the link to the source repo"

# Note: the red-by-default sentinel itself (SCAFFOLD-UNIMPLEMENTED-...) is
# already checked globally, across every shipped plugin file, by the shared
# runner's own section 8 — including the exemption for the generator that
# legitimately embeds the literal. Re-checking it here would either duplicate
# that guard or (worse) match this pack's own comments describing it, so it is
# intentionally left to the shared, single-source-of-truth check.
