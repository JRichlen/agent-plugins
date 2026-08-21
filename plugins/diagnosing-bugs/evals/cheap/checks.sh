# Cheap eval pack for the 'diagnosing-bugs' plugin — SOURCED by evals/cheap/run.sh
# with cwd = repo root; inherits ok/bad/group and $PLUGIN_NAME / $PLUGIN_DIR
# (and the shared has/hasE/lacksE helpers defined once in run.sh).
#
# What this plugin's invariant actually is: a bug fix must NEVER begin with a
# code change — a ranked, falsifiable hypothesis list (claim / evidence /
# falsifying test) is written first; any temporary debug instrumentation
# always carries one fixed grep-able tag and is swept to zero before shipping;
# a regression test is always gated to the confirmed seam, proven red-on-
# pre-fix / green-on-post-fix. The single easiest way for this skill to
# quietly rot is for someone to trim SKILL.md down to generic "think before
# you code" advice and lose the three concrete, checkable mechanisms that make
# it enforceable: the three-part hypothesis entry, the literal `DBGRM:` tag
# plus its exact sweep command, and the red-then-green gate proof. These
# checks fail closed on exactly that kind of regression, plus the structural
# wiring every plugin needs.

SKILL="$PLUGIN_DIR/skills/diagnosing-bugs/SKILL.md"
README="$PLUGIN_DIR/README.md"
AGENTS="$PLUGIN_DIR/AGENTS.md"
COMMAND="$PLUGIN_DIR/commands/diagnosing-bugs.md"

# --- structure: the plugin's advertised surface actually exists ------------
group "diagnosing-bugs — structure"
for f in \
  "$PLUGIN_DIR/.claude-plugin/plugin.json" \
  "$SKILL" \
  "$README" \
  "$AGENTS" \
  "$COMMAND"; do
  if [ -f "$f" ]; then ok "present: $f"; else bad "MISSING: $f"; fi
done

# --- single-file skill: no references/ directory ----------------------------
# The design brief is explicit: this is five sequential steps of ONE source
# procedure, matching the tracer-bullets precedent (0 reference files) rather
# than grill-me/semver-gate. A references/ dir appearing here would mean the
# steps got conditionally split, which contradicts the brief.
group "diagnosing-bugs — single-file skill (no references/ split)"
if [ -d "$PLUGIN_DIR/skills/diagnosing-bugs/references" ]; then
  bad "$PLUGIN_DIR/skills/diagnosing-bugs/references/ exists — this skill must stay single-file (five sequential steps of one procedure), not split into conditionally-loaded reference files"
else
  ok "no references/ directory under skills/diagnosing-bugs — skill stays single-file as designed"
fi

# --- no leftover scaffold placeholders --------------------------------------
# Excludes this checks.sh itself (it legitimately names the marker while
# checking for it).
group "diagnosing-bugs — no unfilled TODOs"
if grep -rln "TODO" "$PLUGIN_DIR" 2>/dev/null | grep -v '/evals/cheap/checks\.sh$' | grep -q .; then
  bad "unfilled TODO marker(s) remain under $PLUGIN_DIR — scaffold prose was never replaced"
else
  ok "no TODO markers under $PLUGIN_DIR (outside this checks.sh)"
fi

# --- core invariant checkpoint 1: hypothesis-before-code, three-part entry -
# A hypothesis is only real if it names a falsifying test — that's the exact
# property distinguishing "hypothesis" from "vibe" per the design. Require all
# three named parts (claim, evidence, falsifying test) AND the explicit
# before-code-change ordering rule, not just the word "hypothesis" in passing.
group "diagnosing-bugs — hypothesis-before-code invariant (three-part entries)"
hasE "$SKILL" '\*\*Claim\*\*' \
     "SKILL.md names 'Claim' as a required hypothesis-entry part" \
     "SKILL.md is MISSING the 'Claim' part of a hypothesis entry"

hasE "$SKILL" '\*\*Evidence so far\*\*' \
     "SKILL.md names 'Evidence so far' as a required hypothesis-entry part" \
     "SKILL.md is MISSING the 'Evidence so far' part of a hypothesis entry"

hasE "$SKILL" '\*\*Falsifying test\*\*' \
     "SKILL.md names 'Falsifying test' as a required hypothesis-entry part" \
     "SKILL.md is MISSING the 'Falsifying test' part of a hypothesis entry — without it a hypothesis can't be distinguished from a vibe"

hasE "$SKILL" 'not a hypothesis|is not a hypothesis' \
     "SKILL.md states that an unfalsifiable claim does not count as a hypothesis" \
     "SKILL.md is MISSING the explicit rule that an entry with no falsifying test is not a hypothesis (it's a vibe)"

hasE "$SKILL" 'before any code change|before any diagnostic or fix code|BEFORE any code change' \
     "SKILL.md states the hypothesis list must exist before ANY code change" \
     "SKILL.md is MISSING the explicit before-any-code-change ordering rule"

# --- core invariant checkpoint 2: literal grep-able tag, named + sweep cmd -
# The design requires the LITERAL tag string and the LITERAL sweep command to
# appear in the doc's own text — vague prose like "tag your debug code" is not
# enough, because a future edit could quietly drop the concrete mechanism and
# leave only vague words while still passing a check that only greps for
# "tag". Anchor to the actual literal, not a paraphrase.
group "diagnosing-bugs — tag-before-ship invariant (literal tag + sweep command)"
has "$SKILL" 'DBGRM:' \
    "SKILL.md names the literal DBGRM: tag" \
    "SKILL.md is MISSING the literal DBGRM: tag string — a vague 'tag your debug code' instruction is not enforceable"

has "$SKILL" "grep -rn 'DBGRM:'" \
    "SKILL.md states the exact sweep command (grep -rn 'DBGRM:' <scope>)" \
    "SKILL.md is MISSING the exact sweep command grep -rn 'DBGRM:' <scope>"

hasE "$SKILL" 'zero lines|MUST return zero|return zero' \
     "SKILL.md states the sweep must return zero lines (zero tolerance)" \
     "SKILL.md is MISSING the zero-tolerance result requirement for the DBGRM: sweep"

hasE "$SKILL" 'never ship untagged|must never ship untagged|never leave it tagged-and-shipped|tagged-and-shipped' \
     "SKILL.md states instrumentation must never ship untagged or tagged-and-shipped" \
     "SKILL.md is MISSING the never-ship-untagged-or-unswept rule"

# --- core invariant checkpoint 3: seam-gated regression test, red-then-green
group "diagnosing-bugs — seam-gated-test invariant (red-then-green proof)"
hasE "$SKILL" '\*\*RED\*\*' \
     "SKILL.md requires the pre-fix regression test to go RED" \
     "SKILL.md is MISSING the requirement that the regression test goes RED on the pre-fix checkout"

hasE "$SKILL" '\*\*GREEN\*\*' \
     "SKILL.md requires the post-fix regression test to go GREEN" \
     "SKILL.md is MISSING the requirement that the regression test goes GREEN after the fix is reapplied"

hasE "$SKILL" 'not.{0,40}gated to the real seam|minimization wasn.t tight enough|go back to Step 4' \
     "SKILL.md states a test that passes pre-fix means minimization was insufficient (loops back to Step 4)" \
     "SKILL.md is MISSING the corrective loop: a test passing without the fix means minimization wasn't tight enough"

hasE "$SKILL" 'coincidental higher-level (test|assertion)' \
     "SKILL.md explicitly rejects a coincidental higher-level test as satisfying the gate" \
     "SKILL.md is MISSING the explicit rejection of a coincidental higher-level test/assertion as sufficient"

# Negation guard: reject phrasings that keep the vocabulary but flip the
# guarantee — e.g. "the regression test is optional" or "tagging is optional".
if grep -qiE 'regression test is optional|hypothesis list is optional|tagging is optional|DBGRM: tag is optional|may skip the hypothesis list|ok to skip the sweep' "$SKILL"; then
  bad "an invariant-softening phrasing was found in $SKILL — one of the three never-soften checkpoints looks like it has been made optional"
else
  ok "none of the three checkpoints are phrased as optional in SKILL.md"
fi

# --- the never-soften framing itself is explicit, not implied --------------
# The design's style note requires the Invariant section to explicitly say
# which parts are approximate vs. which never soften. Losing this framing
# would silently downgrade a hard invariant back into generic best-practice
# advice.
group "diagnosing-bugs — never-soften framing is explicit"
hasE "$SKILL" 'never allowed to soften' \
     "SKILL.md explicitly states which checkpoints are never allowed to soften" \
     "SKILL.md is MISSING the explicit 'never allowed to soften' framing distinguishing hard checkpoints from approximate detail"

hasE "$SKILL" 'hypothesis-before-code' \
     "SKILL.md names the hypothesis-before-code checkpoint by its short label" \
     "SKILL.md is MISSING the short-label name 'hypothesis-before-code' for the first never-soften checkpoint"

hasE "$SKILL" 'tag-before-ship' \
     "SKILL.md names the tag-before-ship checkpoint by its short label" \
     "SKILL.md is MISSING the short-label name 'tag-before-ship' for the second never-soften checkpoint"

hasE "$SKILL" 'seam-gated-test' \
     "SKILL.md names the seam-gated-test checkpoint by its short label" \
     "SKILL.md is MISSING the short-label name 'seam-gated-test' for the third never-soften checkpoint"

# --- all seven procedure steps are present ----------------------------------
# The brief specifies seven sequential steps (0-7) of one procedure. Losing
# any one silently truncates the workflow. Anchor to the ACTUAL step HEADING
# (`^### Step N`), not any mention of "Step N" in surrounding prose — a
# heading can be renamed to generic prose (e.g. "### Minimize the case") while
# cross-references elsewhere in the file ("go back to Step 4") keep the bare
# string alive, which would let a truncated procedure pass a prose-anchored
# check. Requiring the heading form catches that.
group "diagnosing-bugs — all seven procedure steps present (as real headings)"
for n in 0 1 2 3 4 5 6 7; do
  if grep -qE "^### Step $n( |—)" "$SKILL"; then
    ok "SKILL.md has a '### Step $n' heading"
  else
    bad "SKILL.md is MISSING the '### Step $n' heading of the seven-step procedure"
  fi
done

# --- minimization step (Step 4) is present as the seam-finding mechanism ---
group "diagnosing-bugs — minimization to load-bearing seam"
hasE "$SKILL" 'load-bearing' \
     "SKILL.md names the minimized repro as the 'load-bearing' case/seam" \
     "SKILL.md is MISSING the load-bearing-case framing for Step 4's minimization"

# --- auditability (Step 7): ranked list must survive in a durable artifact -
group "diagnosing-bugs — auditability of the ranked hypothesis list"
hasE "$SKILL" 'PR description|commit message|chat output' \
     "SKILL.md states the ranked hypothesis list must be visible in a durable artifact (PR/commit/chat)" \
     "SKILL.md is MISSING where the ranked hypothesis record must surface for auditability"

# --- provenance: the source material is credited, not silently reused ------
group "diagnosing-bugs — provenance credited"
if grep -qiE 'aihero\.dev' "$README" "$SKILL"; then
  ok "aihero.dev is credited as the source"
else
  bad "MISSING credit to aihero.dev as the source of this skill's procedure"
fi
