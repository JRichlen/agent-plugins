# Cheap eval pack for the 'codebase-design' plugin — SOURCED by
# evals/cheap/run.sh with cwd = repo root; inherits ok/bad/group and
# $PLUGIN_NAME / $PLUGIN_DIR.
#
# What this defends: codebase-design's whole reason to exist is that an
# interface-shaped decision gets 3+ radically different candidates, a
# depth/locality/seam-placement comparison, and a confirmed-seam check
# BEFORE any implementation — never the first workable shape shipped
# unexamined, never a test at an unconfirmed seam. These checks are
# deliberately anchored to the STRUCTURAL content of that procedure (the
# named steps, in order; the named axes; the named checks) rather than
# generic file-existence boilerplate, and to the specific language that
# keeps this plugin from being confused with orchestrate, second-opinion, or
# grill-me. Every assertion below is positive ("X is present"), never a
# negative grep for banned language, per this repo's own hard-won lesson
# that negative greps break the moment correct prose documents the thing it
# bans.

SKILL="$PLUGIN_DIR/skills/codebase-design/SKILL.md"
REF_TWICE="$PLUGIN_DIR/skills/codebase-design/references/design-it-twice.md"
REF_DEEP="$PLUGIN_DIR/skills/codebase-design/references/deep-modules.md"
AGENTS="$PLUGIN_DIR/AGENTS.md"
README="$PLUGIN_DIR/README.md"
COMMAND="$PLUGIN_DIR/commands/codebase-design.md"
PLUGIN_JSON="$PLUGIN_DIR/.claude-plugin/plugin.json"

# --- structure: the plugin's advertised surface actually exists ------------
group "codebase-design — structure"
for f in "$PLUGIN_JSON" "$SKILL" "$REF_TWICE" "$REF_DEEP" "$AGENTS" "$README" "$COMMAND"; do
  if [ -f "$f" ]; then ok "present: $f"; else bad "MISSING: $f"; fi
done

# --- plugin.json manifest carries name/description/license -----------------
# Same parser pattern plugin-factory's own dogfood check uses: load the JSON
# and assert on the parsed fields, not a text grep, so a field present only
# in a comment or unrelated string can't fake a pass.
group "codebase-design — plugin.json manifest fields"
if python3 -c "
import json, sys
d = json.load(open(sys.argv[1]))
missing = [k for k in ('name', 'description', 'license') if not d.get(k)]
sys.exit(1 if missing else 0)
" "$PLUGIN_JSON" 2>/dev/null; then
  ok "plugin.json has non-empty name, description, and license fields"
else
  bad "plugin.json is missing (or has empty) one of name/description/license"
fi
if python3 -c "
import json, sys
d = json.load(open(sys.argv[1]))
sys.exit(0 if d.get('name') == 'codebase-design' and d.get('version') == '1.0.0' else 1)
" "$PLUGIN_JSON" 2>/dev/null; then
  ok "plugin.json names 'codebase-design' at version 1.0.0"
else
  bad "plugin.json does not name codebase-design at version 1.0.0 (still 0.0.1?)"
fi

# --- SKILL.md required sections, present AND in the specified order --------
# The invariant, the differentiation section, and all five numbered steps
# must exist. Presence alone isn't enough — Step 3 loading deep-modules.md
# BEFORE Step 1 generates candidates would be a broken procedure that still
# passed a presence-only check, so this also asserts strictly increasing
# line numbers.
group "codebase-design — SKILL.md sections present and in order"
python3 - "$SKILL" <<'PY'
import re, sys
path = sys.argv[1]
lines = open(path).read().splitlines()
required = [
    "## Invariant",
    "## Not this",
    "## Step 0 — Is this interface-shaped?",
    "## Step 1 — Produce 3+ radically different designs",
    "## Step 2 — Compare on depth, locality, seam placement",
    "## Step 3 — Confirm seams before writing any implementation",
    "## Step 4 — Final depth check before handoff",
    "## Step 5 — Ship the decision, not the debate",
]
positions = []
ok_all = True
for h in required:
    found = [i for i, l in enumerate(lines) if l.strip() == h]
    if not found:
        print(f"  FAIL missing required section header: {h!r}")
        ok_all = False
    else:
        positions.append((h, found[0]))
if ok_all:
    prev_line = -1
    for h, ln in positions:
        if ln <= prev_line:
            print(f"  FAIL section out of order: {h!r} at line {ln} is not after the previous required section")
            ok_all = False
        prev_line = ln
if ok_all:
    print("  PASS all 8 required sections present, in the specified order")
sys.exit(0 if ok_all else 1)
PY
if [ $? -eq 0 ]; then pass=$((pass+1)); else fail=$((fail+1)); fi

# --- Not this: all three adjacent plugins named, with a real contrast ------
# Scoped to the '## Not this' section body itself (extracted between that
# header and the next '## ' header), not the whole file — a mention of
# "orchestrate" in Step 1's portability note must not let a check believe
# the differentiation section still names it if that section's own bullet
# was deleted.
group "codebase-design — 'Not this' names all three adjacent plugins"
NOT_THIS_BODY="$(awk '/^## Not this$/{f=1; next} /^## /{f=0} f' "$SKILL")"
for name in "orchestrate" "second-opinion" "grill-me"; do
  if printf '%s' "$NOT_THIS_BODY" | grep -qF "$name"; then
    ok "'## Not this' section names adjacent plugin: $name"
  else
    bad "'## Not this' section does not name adjacent plugin: $name"
  fi
done
# The differentiation from orchestrate specifically must be the RESEARCH vs
# DESIGN ALTERNATIVES distinction the design brief requires, not just a
# name-drop — assert both capitalized contrast terms are present (checked
# separately, not proximity-joined: grep matches per-line, and a legitimate
# prose reflow can move either term to an adjacent line, which must not flip
# a correct tree red).
if grep -qF 'RESEARCH' "$SKILL" && grep -qF 'DESIGN ALTERNATIVES' "$SKILL"; then
  ok "SKILL.md draws the RESEARCH-fan-out vs DESIGN-ALTERNATIVES-comparison distinction against orchestrate"
else
  bad "SKILL.md does not draw the RESEARCH vs DESIGN ALTERNATIVES distinction against orchestrate"
fi
# grill-me's distinction must be the CONVERSATIONAL INTERVIEW vs GENERATING
# designs contrast, not a generic "it's different" note.
if grep -qF 'CONVERSATIONAL INTERVIEW' "$SKILL" && grep -qF 'GENERATING' "$SKILL"; then
  ok "SKILL.md draws the conversational-interview-of-the-user vs agent-generates-designs distinction against grill-me"
else
  bad "SKILL.md does not draw the interview-vs-generates distinction against grill-me"
fi

# --- Step 0: the interface-shaped gate is a real, checkable heuristic ------
# Scoped to the '## Step 0' section body itself (same awk-extraction pattern
# as 'Not this' below), not the whole file — "call sites" also appears in the
# frontmatter, the invariant, and Step 2's LOCALITY prose, so a whole-file
# grep survives deleting the actual Step 0 bullet it's meant to defend.
group "codebase-design — Step 0 gate has checkable criteria"
STEP0_BODY="$(awk '/^## Step 0 —/{f=1; next} /^## /{f=0} f' "$SKILL")"
for marker in "call sites" "crosses a boundary" "expensive or breaking to change" "new abstraction"; do
  if printf '%s' "$STEP0_BODY" | grep -qiF "$marker"; then
    ok "Step 0 heuristic names: $marker"
  else
    bad "Step 0 heuristic is missing: $marker"
  fi
done
if grep -qF 'skipping design-it-twice' "$SKILL"; then
  ok "SKILL.md gives the exact skip phrasing for non-interface-shaped code"
else
  bad "SKILL.md is missing the exact skip phrasing for non-interface-shaped code"
fi

# --- Step 1: forced-divergence generator prompts are all present -----------
group "codebase-design — Step 1 generator prompts force real divergence"
for marker in "where state lives" "call shape" "surface size" "owns error"; do
  if grep -qiF "$marker" "$SKILL"; then
    ok "Step 1 names generator prompt: $marker"
  else
    bad "Step 1 is missing generator prompt: $marker"
  fi
done

# --- Step 2: the three named axes and the tie-break rule --------------------
group "codebase-design — Step 2 axes and tie-break"
for axis in "DEPTH" "LOCALITY" "SEAM PLACEMENT"; do
  if grep -qF "$axis" "$SKILL"; then
    ok "Step 2 names axis: $axis"
  else
    bad "Step 2 is missing axis: $axis"
  fi
done
if grep -qiF 'locality wins the tiebreak' "$SKILL"; then
  ok "SKILL.md states the locality-wins tiebreak rule"
else
  bad "SKILL.md is missing the locality-wins tiebreak rule"
fi

# --- Step 3: two-adapter check and the unconfirmed-seam rule ---------------
# Scoped to the '## Step 3' section body — "two-adapter check" also appears
# in Step 4's cross-reference (:202), so a whole-file grep survives Step 3
# itself no longer naming the check it's supposed to apply.
group "codebase-design — Step 3 seam confirmation"
STEP3_BODY="$(awk '/^## Step 3 —/{f=1; next} /^## /{f=0} f' "$SKILL")"
if printf '%s' "$STEP3_BODY" | grep -qiF 'two-adapter check'; then
  ok "SKILL.md names the two-adapter check"
else
  bad "SKILL.md does not name the two-adapter check"
fi
if printf '%s' "$STEP3_BODY" | grep -qiF 'no test at an unconfirmed seam'; then
  ok "SKILL.md states the 'no test at an unconfirmed seam' rule"
else
  bad "SKILL.md does not state the 'no test at an unconfirmed seam' rule"
fi

# --- Step 4: four dependency categories and the over-fragmentation check ---
group "codebase-design — Step 4 dependency categories"
for cat in "Pure/internal logic" "Owned deep dependency" "Unowned external boundary" "Config/environment surface"; do
  if grep -qF "$cat" "$SKILL"; then
    ok "Step 4 names category: $cat"
  else
    bad "Step 4 is missing category: $cat"
  fi
done
if grep -qiF 'testability-only interface' "$SKILL" || grep -qiF 'thin, testability-only interface' "$SKILL"; then
  ok "SKILL.md names the testability-only-interface failure mode"
else
  bad "SKILL.md is missing the testability-only-interface failure mode"
fi

# --- Step 5: the handoff output shape, including the rejection-summary form
group "codebase-design — Step 5 output shape"
if grep -qiF 'considered and rejected' "$SKILL"; then
  ok "SKILL.md gives the 'considered and rejected: X (...), Z (...)' handoff form"
else
  bad "SKILL.md is missing the 'considered and rejected' handoff form"
fi

# --- Portability: default is subagent-free, escalation is named optional ---
group "codebase-design — portability is real, not just claimed"
if grep -qiF 'needs no subagent-spawning tool' "$SKILL"; then
  ok "SKILL.md states the default path needs no subagent-spawning tool"
else
  bad "SKILL.md does not clearly state the default path needs no subagent-spawning tool"
fi
if grep -qiF 'MAY optionally dispatch' "$SKILL"; then
  ok "SKILL.md states the parallel-subagent escalation is optional (MAY, not MUST)"
else
  bad "SKILL.md does not clearly mark the subagent escalation as optional"
fi

# --- references/design-it-twice.md: definitions, template, worked examples -
group "codebase-design — design-it-twice.md content"
for axis in "DEPTH" "LOCALITY" "SEAM PLACEMENT"; do
  if grep -qF "$axis" "$REF_TWICE"; then
    ok "design-it-twice.md defines axis: $axis"
  else
    bad "design-it-twice.md is missing axis definition: $axis"
  fi
done
if grep -qiF 'Comparison-table template' "$REF_TWICE"; then
  ok "design-it-twice.md carries the comparison-table template"
else
  bad "design-it-twice.md is missing the comparison-table template"
fi
if grep -qiF 'Worked example 1' "$REF_TWICE" && grep -qiF 'Worked example 2' "$REF_TWICE"; then
  ok "design-it-twice.md carries 2+ worked examples"
else
  bad "design-it-twice.md is missing 2+ worked examples"
fi

# --- references/deep-modules.md: four categories in order + all four subsections
group "codebase-design — deep-modules.md folds in all four MEDIUM companions"
for heading in \
  "## Module Depth Analysis" \
  "## The deletion test" \
  "## Seam validation: one adapter vs two" \
  "## Seam-Based Design & Test Agreement"; do
  if grep -qF "$heading" "$REF_DEEP"; then
    ok "deep-modules.md has subsection: $heading"
  else
    bad "deep-modules.md is missing subsection: $heading"
  fi
done
# The four numbered categories must be the SAME four named in SKILL.md Step 4
# — check each survives here too, so an edit can't drop one silently from the
# reference while leaving SKILL.md's summary untouched (or vice versa).
for cat in "Pure/internal logic" "Owned deep dependency" "Unowned external boundary" "Config/environment surface"; do
  if grep -qF "$cat" "$REF_DEEP"; then
    ok "deep-modules.md names category: $cat"
  else
    bad "deep-modules.md is missing category: $cat"
  fi
done
if grep -qiF 'two-adapter check' "$REF_DEEP"; then
  ok "deep-modules.md names the two-adapter check"
else
  bad "deep-modules.md does not name the two-adapter check"
fi
# Section order: Module Depth Analysis, then the deletion test, then seam
# validation, then Seam-Based Design & Test Agreement — matches the design
# brief's explicit (a)(b)(c)(d) ordering.
python3 - "$REF_DEEP" <<'PY'
import sys
lines = open(sys.argv[1]).read().splitlines()
required = [
    "## Module Depth Analysis",
    "## The deletion test",
    "## Seam validation: one adapter vs two",
    "## Seam-Based Design & Test Agreement",
]
positions = []
ok_all = True
for h in required:
    found = [i for i, l in enumerate(lines) if l.strip() == h]
    if not found:
        ok_all = False
    else:
        positions.append(found[0])
if ok_all:
    prev = -1
    for ln in positions:
        if ln <= prev:
            ok_all = False
        prev = ln
sys.exit(0 if ok_all else 1)
PY
if [ $? -eq 0 ]; then
  ok "deep-modules.md's four subsections are in the specified (a)(b)(c)(d) order"
else
  fail_msg="deep-modules.md subsections are missing or out of order"
  bad "$fail_msg"
fi

# --- progressive disclosure: both references exist AND are actually loaded -
# Not enough for the files to exist — SKILL.md must reference each by its
# relative path, or progressive disclosure is claimed but not wired (this is
# the exact "rename/typo silently breaks the on-demand load" gap the design
# brief calls out).
group "codebase-design — progressive disclosure wired by relative path"
if grep -qF 'references/design-it-twice.md' "$SKILL"; then
  ok "SKILL.md references references/design-it-twice.md by relative path"
else
  bad "SKILL.md does not reference references/design-it-twice.md by relative path"
fi
if grep -qF 'references/deep-modules.md' "$SKILL"; then
  ok "SKILL.md references references/deep-modules.md by relative path"
else
  bad "SKILL.md does not reference references/deep-modules.md by relative path"
fi

# --- invariant text survives verbatim in SKILL.md and AGENTS.md ------------
# Two markers, not one: the closing sentence (test/seam discipline) AND the
# HEADLINE ALWAYS/NEVER clause (3+ candidates compared before picking one).
# Pinning only the closing sentence lets the headline clause — the actual
# "produce 3+ radically different designs" mandate the whole plugin exists to
# enforce — be gutted to something toothless ("sanity-check it before picking
# one") while the suite stays green. Both markers must hold in both files.
group "codebase-design — invariant text is verbatim in SKILL.md and AGENTS.md"
INVARIANT_MARKER_HEAD='ALWAYS produce 3+ radically different candidate designs and compare them on depth, locality, and seam placement before picking one — NEVER let the first workable interface ship unexamined'
INVARIANT_MARKER='NEVER a shallow pass-through whose interface exists only to make internals swappable, and NEVER a test written against an unconfirmed seam'
if grep -qF "$INVARIANT_MARKER_HEAD" "$SKILL"; then
  ok "SKILL.md carries the invariant's headline ALWAYS/NEVER clause verbatim"
else
  bad "SKILL.md is missing the invariant's headline ALWAYS/NEVER clause verbatim"
fi
if grep -qF "$INVARIANT_MARKER_HEAD" "$AGENTS"; then
  ok "AGENTS.md carries the invariant's headline ALWAYS/NEVER clause verbatim"
else
  bad "AGENTS.md is missing the invariant's headline ALWAYS/NEVER clause verbatim"
fi
if grep -qF "$INVARIANT_MARKER" "$SKILL"; then
  ok "SKILL.md carries the invariant's closing sentence verbatim"
else
  bad "SKILL.md is missing the invariant's closing sentence verbatim"
fi
if grep -qF "$INVARIANT_MARKER" "$AGENTS"; then
  ok "AGENTS.md carries the invariant's closing sentence verbatim"
else
  bad "AGENTS.md is missing the invariant's closing sentence verbatim"
fi
