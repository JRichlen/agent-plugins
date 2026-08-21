# Cheap eval pack for the 'context-handoff' plugin — SOURCED by
# evals/cheap/run.sh with cwd = repo root; inherits ok/bad/group and
# $PLUGIN_NAME / $PLUGIN_DIR (and the shared has/hasE/lacksE helpers defined
# once in run.sh).
#
# What this plugin's invariant actually is (two clauses, both defended here):
#   1. The continue/clear/handoff/delegate/compact choice is ALWAYS reached by
#      walking the one ordered tree top-to-bottom, first match wins — never
#      guessed ad hoc, never invoked mid-phase, never jumped to out of order.
#   2. Anything crossing a handoff boundary is ALWAYS referenced by path or
#      URL, NEVER copied or quoted inline into the handoff artifact.
# These checks are deliberately paranoid about both clauses and comparatively
# loose about prose wording elsewhere — a regression that reorders the tree,
# drops a branch, or lets the pointer-only rule go unenforced is the failure
# mode that matters here.

SKILL="$PLUGIN_DIR/skills/context-handoff/SKILL.md"
REFDIR="$PLUGIN_DIR/skills/context-handoff/references"
REF1="$REFDIR/portable-extraction.md"
REF2="$REFDIR/research-documenter.md"
CHECKER="$PLUGIN_DIR/scripts/check-handoff-portability.py"
AGENTS="$PLUGIN_DIR/AGENTS.md"
README="$PLUGIN_DIR/README.md"
COMMAND="$PLUGIN_DIR/commands/context-handoff.md"
FIXTURE_GOOD="$PLUGIN_DIR/evals/cheap/fixtures/handoff-good.md"
FIXTURE_BAD="$PLUGIN_DIR/evals/cheap/fixtures/handoff-bad.md"

# --- structure: the plugin's advertised surface actually exists ------------
group "context-handoff — structure"
for f in \
  "$PLUGIN_DIR/.claude-plugin/plugin.json" \
  "$SKILL" \
  "$AGENTS" \
  "$README" \
  "$COMMAND" \
  "$CHECKER" \
  "$FIXTURE_GOOD" \
  "$FIXTURE_BAD"; do
  if [ -f "$f" ]; then ok "present: $f"; else bad "MISSING: $f"; fi
done

# --- deterministic check 1 (design brief Part 6.1): the 5 tree nodes appear
# in SKILL.md, in canonical order, never reordered or dropped -----------------
group "context-handoff — decision tree carries all 5 nodes in canonical order"
python3 - "$SKILL" <<'PY'
import re, sys
path = sys.argv[1]
text = open(path).read()
nodes = ["CONTINUE", "CLEAR", "HANDOFF", "DELEGATE", "COMPACT"]
# Each node must appear as a numbered tree heading: "### N. NODE" (DELEGATE's
# heading carries a parenthetical, COMPACT's carries "(default)").
positions = []
ok = True
for idx, node in enumerate(nodes, start=1):
    pat = re.compile(r'^###\s*' + str(idx) + r'\.\s*' + node + r'\b', re.MULTILINE)
    m = pat.search(text)
    if not m:
        print(f"  FAIL node {idx}. {node} not found as a numbered '### {idx}. {node}' heading")
        ok = False
        continue
    positions.append((node, m.start()))
    print(f"  PASS node {idx}. {node} found as a numbered heading")
if ok:
    # canonical order: positions must be strictly increasing (already implied
    # by numbering the pattern itself, but re-assert file order independently
    # so a copy-paste reorder that kept numbers but moved text also fails)
    offsets = [pos for _, pos in positions]
    if offsets == sorted(offsets):
        print("  PASS all 5 nodes appear in canonical file order: continue, clear, handoff, delegate, compact")
    else:
        print("  FAIL nodes are present but NOT in canonical file order")
        ok = False
sys.exit(0 if ok else 1)
PY
if [ $? -eq 0 ]; then pass_inc=1; else pass_inc=0; fi
# fold the python subprocess result into this shell's pass/fail counters via
# a single ok/bad call, since the group above already printed the detail lines
if [ "$pass_inc" -eq 1 ]; then
  ok "SKILL.md decision tree: all 5 nodes present, in canonical order"
else
  bad "SKILL.md decision tree is missing a node or has nodes out of canonical order"
fi

# "first match wins" ordering discipline must be stated explicitly, not just
# implied by heading order — the invariant requires it be walked, not jumped.
if grep -qiE 'first match wins' "$SKILL"; then
  ok "SKILL.md states 'first match wins'"
else
  bad "SKILL.md does not state 'first match wins'"
fi

# Computed here (before it's needed by the ordering check just below) and
# reused by the mid-phase carve-out group further down — one extraction, two
# consumers, so it can't drift out of sync with itself.
# Anchored to the '## When the tree applies' section specifically (not just
# anywhere in the file) — the invariant's compressed parenthetical up at
# SKILL.md:12 carries a similarly-worded phrase ("never jumped to out of
# order"), so an unanchored grep would still pass even if this section's own
# restatement of the ordering rule were gutted. Scoping to the section that
# actually guides runtime behavior here is what makes this a real check
# instead of one satisfied by a copy living somewhere else in the file.
BOUNDARY_BLOCK_FLAT="$(awk '/^## When the tree applies/{flag=1; next} /^## The ordered decision tree/{flag=0} flag' "$SKILL" | tr '\n' ' ')"

# Require BOTH distinctive phrases from the section's actual ordering
# sentence ("...never jump straight to a later branch because it 'feels
# right'; the earlier branches are cheaper/safer and must be ruled out
# first.") to co-occur in that section. This is deliberately NOT satisfiable
# by the invariant's compressed restatement at SKILL.md:12 ("never jumped to
# out of order"), which has neither "later branch" nor "ruled out first" —
# so deleting this section's own ordering sentence fails even though the
# invariant line is untouched.
if printf '%s' "$BOUNDARY_BLOCK_FLAT" | grep -qiE 'never jump (straight )?to a later branch' \
  && printf '%s' "$BOUNDARY_BLOCK_FLAT" | grep -qiE 'ruled out first'; then
  ok "'## When the tree applies' forbids jumping to a later branch out of order"
else
  bad "'## When the tree applies' does not forbid jumping to a later branch out of order"
fi

# --- mid-phase carve-out: the tree must not be run mid-phase ----------------
group "context-handoff — mid-phase carve-out present"
if printf '%s' "$BOUNDARY_BLOCK_FLAT" | grep -q .; then
  ok "SKILL.md has a non-empty '## When the tree applies' section"
else
  bad "SKILL.md has NO '## When the tree applies' section (or it is empty)"
fi
if printf '%s' "$BOUNDARY_BLOCK_FLAT" | grep -qiE 'mid-phase there (is|are) (nothing to decide|only two implicit moves)'; then
  ok "'## When the tree applies' states the mid-phase carve-out (nothing to decide / two implicit moves)"
else
  bad "'## When the tree applies' does not state the mid-phase carve-out"
fi
if printf '%s' "$BOUNDARY_BLOCK_FLAT" | grep -qF 'Boundary check:'; then
  ok "'## When the tree applies' has a literal 'Boundary check:' gate"
else
  bad "'## When the tree applies' is missing the literal 'Boundary check:' gate"
fi

# --- deterministic check 2 (design brief Part 6.2): both reference files
# exist AND are referenced by relative path from SKILL.md -------------------
group "context-handoff — both reference files exist and are wired from SKILL.md"
for f in "$REF1" "$REF2"; do
  if [ -f "$f" ]; then ok "present: $f"; else bad "MISSING reference file: $f"; fi
done
for name in "references/portable-extraction.md" "references/research-documenter.md"; do
  if grep -qF "$name" "$SKILL"; then
    ok "SKILL.md references $name"
  else
    bad "SKILL.md does NOT reference $name — progressive disclosure not wired"
  fi
done

# --- deterministic check 3 (design brief Part 6.3): both invariant clauses
# appear near-verbatim inside the '## Invariant' section specifically -------
group "context-handoff — invariant text present verbatim, inside ## Invariant"
INVARIANT_BLOCK="$(awk '/^## Invariant/{flag=1; next} /^## /{flag=0} flag' "$SKILL")"
if printf '%s' "$INVARIANT_BLOCK" | grep -q .; then
  ok "SKILL.md has a non-empty '## Invariant' section"
else
  bad "SKILL.md has NO '## Invariant' section (or it is empty)"
fi

CLAUSE1='ordered decision tree top-to-bottom'
CLAUSE1B='never guessed ad hoc'
CLAUSE2='referenced by path or URL'
CLAUSE2B='NEVER copied or quoted inline'
if printf '%s' "$INVARIANT_BLOCK" | grep -qF "$CLAUSE1" && printf '%s' "$INVARIANT_BLOCK" | grep -qF "$CLAUSE1B"; then
  ok "## Invariant carries clause 1 (ordered tree, never guessed ad hoc)"
else
  bad "## Invariant is MISSING or has weakened clause 1 (ordered tree / never guessed ad hoc)"
fi
if printf '%s' "$INVARIANT_BLOCK" | grep -qF "$CLAUSE2" && printf '%s' "$INVARIANT_BLOCK" | grep -qF "$CLAUSE2B"; then
  ok "## Invariant carries clause 2 (path/URL only, never copied inline)"
else
  bad "## Invariant is MISSING or has weakened clause 2 (path/URL only / never copied inline)"
fi

# Same invariant text must also survive verbatim in AGENTS.md (the scaffold
# wrote it into both at generation time from --invariant; a later edit to one
# and not the other is a real drift risk this catches, per the pattern
# semver-gate and verify-before-claim already established).
INVARIANT_MARKER='must ALWAYS be reached by walking the one ordered decision tree top-to-bottom'
if grep -qF "$INVARIANT_MARKER" "$AGENTS"; then
  ok "AGENTS.md carries the invariant text verbatim"
else
  bad "AGENTS.md is MISSING the invariant text"
fi

# --- HANDOFF branch requires naming a concrete boundary, not vibes ----------
# Prose in SKILL.md is hard-wrapped at ~80 columns, so a phrase that happens to
# straddle a line break would be invisible to a plain single-line grep even
# though it's present. Normalize whitespace (collapse newlines to spaces)
# before matching multi-word phrases so wrapping never produces a false FAIL.
group "context-handoff — HANDOFF branch requires a named concrete boundary"
SKILL_FLAT="$(tr '\n' ' ' < "$SKILL")"
if printf '%s' "$SKILL_FLAT" | grep -qiE "if you can.t name it, this branch does not match"; then
  ok "SKILL.md requires naming the concrete boundary crossed, or HANDOFF does not match"
else
  bad "SKILL.md does not require naming a concrete boundary for HANDOFF"
fi
if printf '%s' "$SKILL_FLAT" | grep -qiE "never use it just because you want to summarize progress"; then
  ok "SKILL.md warns against reaching for HANDOFF just to summarize progress"
else
  bad "SKILL.md does not warn against the most common HANDOFF misuse"
fi

# --- DELEGATE branch defers fan-out mechanics to orchestrate, doesn't inline
# them ------------------------------------------------------------------------
group "context-handoff — DELEGATE branch defers fan-out internals to orchestrate"
DELEGATE_BLOCK_FLAT="$(awk '/^### 4\. DELEGATE/{flag=1; next} /^### 5\./{flag=0} flag' "$SKILL" | tr '\n' ' ')"
if printf '%s' "$DELEGATE_BLOCK_FLAT" | grep -qi 'orchestrate'; then
  ok "DELEGATE branch names the orchestrate plugin"
else
  bad "DELEGATE branch does not name the orchestrate plugin"
fi
if printf '%s' "$DELEGATE_BLOCK_FLAT" | grep -qiE 'do not inline fan-out mechanics'; then
  ok "DELEGATE branch explicitly declines to inline fan-out mechanics"
else
  bad "DELEGATE branch does not explicitly decline to inline fan-out mechanics"
fi

# --- differentiation: 'Not this' section names both neighbouring plugins ---
group "context-handoff — differentiation names both neighbouring plugins"
NOT_THIS_BLOCK="$(awk '/^## Not this/{flag=1; next} /^## /{flag=0} flag' "$SKILL")"
if printf '%s' "$NOT_THIS_BLOCK" | grep -q .; then
  ok "SKILL.md has a non-empty '## Not this' section"
else
  bad "SKILL.md has NO '## Not this' section (or it is empty)"
fi
if printf '%s' "$NOT_THIS_BLOCK" | grep -qF 'orchestrate'; then
  ok "'## Not this' names orchestrate"
else
  bad "'## Not this' does NOT name orchestrate"
fi
if printf '%s' "$NOT_THIS_BLOCK" | grep -qF 'dev-diary'; then
  ok "'## Not this' names dev-diary"
else
  bad "'## Not this' does NOT name dev-diary"
fi

# --- frontmatter description stays out of orchestrate/dev-diary's trigger
# vocabulary (keeps skill selection unambiguous, per the differentiation plan)
group "context-handoff — frontmatter description avoids neighbours' trigger vocabulary"
FRONTMATTER="$(awk '/^---$/{n++; next} n==1' "$SKILL")"
FORBIDDEN=0
for phrase in "fan out subagents" "research and verify" "diary" "journal" "what did I do today"; do
  if printf '%s' "$FRONTMATTER" | grep -qi "$phrase"; then
    bad "SKILL.md frontmatter description uses '$phrase', which is orchestrate's/dev-diary's trigger vocabulary"
    FORBIDDEN=1
  fi
done
[ "$FORBIDDEN" -eq 0 ] && ok "SKILL.md frontmatter description avoids orchestrate's and dev-diary's trigger phrases"

# --- deterministic check 4 (design brief Part 6.4, the "stretch check" made
# real): the pointer-only size-check rule is machine-checkable, proven by
# running the shipped checker against both a compliant and a violating fixture
group "context-handoff — pointer-only size-check rule is machine-checkable"
if python3 "$CHECKER" "$FIXTURE_GOOD" >/dev/null 2>&1; then
  ok "checker exits 0 on the compliant fixture (handoff-good.md)"
else
  bad "checker FAILED on the compliant fixture (handoff-good.md) — false positive"
fi
if python3 "$CHECKER" "$FIXTURE_BAD" >/dev/null 2>&1; then
  bad "checker exited 0 on the violating fixture (handoff-bad.md) — false negative, the rule is not actually enforced"
else
  ok "checker exits nonzero on the violating fixture (handoff-bad.md), correctly flagging the long unpointed quote"
fi
# The checker must also be referenced from portable-extraction.md, or the
# rule's "usable by an eval" mechanics are undiscoverable from the skill.
if grep -qF 'check-handoff-portability.py' "$REF1"; then
  ok "portable-extraction.md references the shipped checker script"
else
  bad "portable-extraction.md does NOT reference scripts/check-handoff-portability.py"
fi

# --- research.md rule: temporary/staleness note required, and recursion to
# the pointer-only rule is stated -------------------------------------------
group "context-handoff — research.md lifecycle and recursive pointer-only rule"
if grep -qiE 'temporary' "$REF2" && grep -qiE 'safe to delete' "$REF2"; then
  ok "research-documenter.md states research.md's temporary lifecycle and a staleness note"
else
  bad "research-documenter.md is missing the temporary lifecycle / staleness note requirement"
fi
# Scoped to the BODY of the recursion section, not just its heading — a
# heading alone ("never re-embedded") can survive while the body prose under
# it is gutted or reversed, which a whole-file grep would miss entirely.
RECURSION_BODY_FLAT="$(awk '/^## Referenced by the handoff file/{flag=1; next} flag' "$REF2" | tr '\n' ' ')"
if printf '%s' "$RECURSION_BODY_FLAT" | grep -q .; then
  ok "research-documenter.md has a non-empty recursion-rule section body"
else
  bad "research-documenter.md has NO body under its recursion-rule heading"
fi
if printf '%s' "$RECURSION_BODY_FLAT" | grep -qiE 'never copy its contents in'; then
  ok "research-documenter.md's recursion-rule body forbids re-embedding research.md into a handoff file"
else
  bad "research-documenter.md's recursion-rule body does not forbid re-embedding research.md into a handoff file"
fi
# Negation guard: reject phrasing that would let the recursion rule be
# quietly reversed even if the affirmative sentence above is still present.
if printf '%s' "$RECURSION_BODY_FLAT" | grep -qiE '(feel free to (copy|paste)|may summarize its contents|okay to (copy|embed|paste))'; then
  bad "research-documenter.md's recursion-rule body contains contradicting copy/embed-permitted language"
else
  ok "no contradicting copy/embed-permitted language in research-documenter.md's recursion-rule body"
fi

# --- no leftover scaffold placeholders --------------------------------------
group "context-handoff — no unfilled TODOs"
if grep -rln "TODO" "$PLUGIN_DIR" 2>/dev/null | grep -v '/evals/cheap/checks\.sh$' | grep -q .; then
  bad "unfilled TODO marker(s) remain under $PLUGIN_DIR — scaffold prose was never replaced"
else
  ok "no TODO markers under $PLUGIN_DIR (outside this checks.sh)"
fi
