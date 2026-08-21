# Cheap eval pack for the 'tracer-bullets' plugin — SOURCED by evals/cheap/run.sh
# with cwd = repo root; inherits ok/bad/group and $PLUGIN_NAME / $PLUGIN_DIR
# (and the shared has/hasE/lacksE helpers defined once in run.sh).
#
# What this plugin's invariant actually is: a tracer bullet is a REAL,
# end-to-end, KEPT-and-built-upon slice — never a disposable prototype/spike.
# The single easiest way for this skill to quietly rot is for someone to trim
# the SKILL.md down to "build something small first" and lose the one clause
# that makes it a tracer bullet rather than a prototype: that the slice is
# real and gets KEPT, not thrown away. These checks fail closed on exactly
# that kind of regression, plus the structural wiring every plugin needs.

SKILL="$PLUGIN_DIR/skills/tracer-bullets/SKILL.md"
README="$PLUGIN_DIR/README.md"
AGENTS="$PLUGIN_DIR/AGENTS.md"
COMMAND="$PLUGIN_DIR/commands/tracer-bullets.md"

# --- structure: the plugin's advertised surface actually exists ------------
group "tracer-bullets — structure"
for f in \
  "$PLUGIN_DIR/.claude-plugin/plugin.json" \
  "$SKILL" \
  "$README" \
  "$AGENTS" \
  "$COMMAND"; do
  if [ -f "$f" ]; then ok "present: $f"; else bad "MISSING: $f"; fi
done

# --- no leftover scaffold placeholders --------------------------------------
# Excludes this checks.sh itself (it legitimately names the marker while
# checking for it) and the reference docs, which are prose ABOUT the plugin.
group "tracer-bullets — no unfilled TODOs"
if grep -rln "TODO" "$PLUGIN_DIR" 2>/dev/null | grep -v '/evals/cheap/checks\.sh$' | grep -q .; then
  bad "unfilled TODO marker(s) remain under $PLUGIN_DIR — scaffold prose was never replaced"
else
  ok "no TODO markers under $PLUGIN_DIR (outside this checks.sh)"
fi

# --- core invariant: kept-and-built-upon, never a disposable prototype -----
# This is the whole point of the plugin. A tracer bullet that isn't clearly
# distinguished from a prototype/spike is just "build something small first,"
# which is not a load-bearing invariant — anyone would already do that.
group "tracer-bullets — kept-vs-thrown-away invariant"
hasE "$SKILL" 'kept|widen(s|ed|ing)? it in place|becomes the skeleton' \
     "SKILL.md states the slice is kept / widened in place" \
     "SKILL.md is MISSING language that the tracer-bullet slice is KEPT and widened, not discarded"

hasE "$SKILL" 'thrown away|discard(ed)?|disposable' \
     "SKILL.md names the discard fate that belongs to prototypes/spikes, not tracer bullets" \
     "SKILL.md is MISSING the contrasting 'thrown away / discarded' language for prototypes — without it there is nothing to distinguish a tracer bullet FROM"

hasE "$SKILL" '[Pp]rototype' \
     "SKILL.md explicitly names 'prototype' as the contrasting concept" \
     "SKILL.md never says the word 'prototype' — the invariant this plugin exists to defend (tracer bullet != prototype) is unstated"

hasE "$SKILL" '[Ss]pike' \
     "SKILL.md explicitly names 'spike' as the contrasting concept" \
     "SKILL.md never says the word 'spike' — the invariant this plugin exists to defend (tracer bullet != spike) is unstated"

# Negation guard: the keyword greps above pass on an INVERTED rule (e.g. "a
# tracer bullet is now disposable, like a prototype"). Reject phrasings that
# keep the vocabulary but flip the guarantee.
if grep -qiE 'tracer bullets? (are|is) (disposable|thrown away|meant to be discarded)|no (longer|need to) keep the (slice|tracer bullet)|tracer bullets? (and|are the same as|are basically) prototypes' "$SKILL"; then
  bad "kept-vs-thrown-away invariant looks INVERTED in $SKILL — a phrasing keeps the vocabulary but flips tracer bullets into something disposable"
else
  ok "kept-vs-thrown-away invariant not inverted in SKILL.md"
fi

# --- both use-case domains are covered --------------------------------------
# The design explicitly requires both: software delivery AND open-ended
# investigation/research (with a worked example). Losing either half silently
# narrows the skill back to "just a coding technique," which is a real
# regression given this plugin was built specifically to cover both.
group "tracer-bullets — both use-case domains covered"
if grep -qiE 'software delivery' "$SKILL"; then
  ok "SKILL.md covers the software-delivery use case"
else
  bad "SKILL.md is MISSING a software-delivery use case section"
fi
if grep -qiE 'investigation|research' "$SKILL"; then
  ok "SKILL.md covers the investigation/research use case"
else
  bad "SKILL.md is MISSING an investigation/research use case section"
fi

# --- prototyping_contrast is explicit, not implied --------------------------
# The design calls this out by name as the property most likely to be gotten
# wrong. Require a dedicated section (not just passing words) that states the
# contrast directly, e.g. as a heading or comparison table.
group "tracer-bullets — prototyping contrast is an explicit section"
if grep -qiE '^#+.*(prototype|spike)' "$SKILL"; then
  ok "SKILL.md has a dedicated heading contrasting tracer bullets with prototypes/spikes"
else
  bad "SKILL.md has NO dedicated heading contrasting tracer bullets with prototypes/spikes — the contrast is the property most likely to erode silently if it's only implied in body prose"
fi

# --- provenance: the source material is credited, not silently reused ------
group "tracer-bullets — provenance credited"
if grep -qiE 'Pragmatic Programmer' "$README" "$SKILL"; then
  ok "The Pragmatic Programmer is credited as the origin"
else
  bad "MISSING credit to The Pragmatic Programmer (Hunt & Thomas) as the origin of the term"
fi
if grep -qiE 'aihero\.dev' "$README" "$SKILL"; then
  ok "aihero.dev is credited as the applied-writeup source"
else
  bad "MISSING credit to aihero.dev (Matt Pocock's tracer-bullets post) as a source"
fi
