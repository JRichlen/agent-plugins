# Cheap eval pack for the 'wayfinder' plugin — SOURCED by evals/cheap/run.sh
# with cwd = repo root; inherits ok/bad/group and $PLUGIN_NAME / $PLUGIN_DIR
# (and the shared has/hasE/lacksE helpers defined once in run.sh).
#
# What this plugin's invariant actually is: a multi-session effort must
# ALWAYS be represented as a labeled map of typed decision tickets
# (grilling/prototype/research/task) with dependencies made explicit before
# any ticket is dispatched; planning tickets must NEVER be silently converted
# into execution tickets (a scope surprise closes the ticket and spawns a new
# LINKED task ticket instead); and only the non-blocking frontier — every
# open ticket whose dependencies are all CLOSED, computed fresh each time,
# never cached — may ever be dispatched in parallel. These checks defend
# BOTH the structural wiring (three reference files exist and are actually
# named in SKILL.md's procedure) and the content invariants (the type-lock
# rule, the frontier definition, the cycle check, the fog-of-war test, and
# the differentiation from orchestrate/grill-me are all present as real,
# specific prose — not generic file-existence boilerplate).

SKILL="$PLUGIN_DIR/skills/wayfinder/SKILL.md"
REFDIR="$PLUGIN_DIR/skills/wayfinder/references"
AGENTS="$PLUGIN_DIR/AGENTS.md"
README="$PLUGIN_DIR/README.md"
COMMAND="$PLUGIN_DIR/commands/wayfinder.md"

REF_TAXONOMY="$REFDIR/ticket-taxonomy.md"
REF_BREAKDOWN="$REFDIR/task-breakdown.md"
REF_FOGOFWAR="$REFDIR/fog-of-war.md"

# --- structure: the plugin's advertised surface actually exists ------------
group "wayfinder — structure"
for f in \
  "$PLUGIN_DIR/.claude-plugin/plugin.json" \
  "$SKILL" \
  "$AGENTS" \
  "$README" \
  "$COMMAND"; do
  if [ -f "$f" ]; then ok "present: $f"; else bad "MISSING: $f"; fi
done

# --- all three reference files exist on disk --------------------------------
# Positive, structural: SKILL.md's pointers into references/ are worthless if
# the files they point at were never written.
group "wayfinder — all three reference files exist on disk"
for f in "$REF_TAXONOMY" "$REF_BREAKDOWN" "$REF_FOGOFWAR"; do
  if [ -f "$f" ]; then ok "present: $f"; else bad "MISSING reference file: $f"; fi
done

# --- SKILL.md's procedure actually cites all three reference files ---------
# Existing on disk isn't enough — the procedure steps must actually point a
# reader at each file, or the references/ split is unwired documentation.
group "wayfinder — SKILL.md procedure cites all three reference files"
for name in "ticket-taxonomy.md" "task-breakdown.md" "fog-of-war.md"; do
  if grep -qF "references/$name" "$SKILL"; then
    ok "SKILL.md procedure cites references/$name"
  else
    bad "SKILL.md procedure is MISSING a citation of references/$name"
  fi
done

# --- plugin.json shipped past the scaffold's pre-release version -----------
group "wayfinder — plugin.json is past scaffold version 0.0.1"
PJ_VERSION="$(python3 -c "import json; print(json.load(open('$PLUGIN_DIR/.claude-plugin/plugin.json'))['version'])" 2>/dev/null)"
if [ "$PJ_VERSION" = "0.0.1" ] || [ -z "$PJ_VERSION" ]; then
  bad "plugin.json version is still the scaffold default ('$PJ_VERSION') — bump it for a real release"
else
  ok "plugin.json version is '$PJ_VERSION' (past scaffold default)"
fi

# --- invariant text present verbatim in both SKILL.md and AGENTS.md --------
# The scaffold wrote this into both at generation time from --invariant; a
# later edit to one and not the other is a real drift risk this catches.
group "wayfinder — invariant text present verbatim"
INVARIANT_MARKER='the non-blocking frontier (every open ticket whose listed dependencies are all CLOSED, computed fresh each time, never cached) may be dispatched in parallel'
if grep -qF "$INVARIANT_MARKER" "$SKILL"; then
  ok "SKILL.md carries the invariant text verbatim"
else
  bad "SKILL.md is MISSING the invariant text"
fi
if grep -qF "$INVARIANT_MARKER" "$AGENTS"; then
  ok "AGENTS.md carries the invariant text verbatim"
else
  bad "AGENTS.md is MISSING the invariant text"
fi

# --- the four ticket types are each defined, by name, in the taxonomy ------
group "wayfinder — all four ticket types are defined in ticket-taxonomy.md"
for t in grilling prototype research task; do
  if grep -qE "^### \`$t\`" "$REF_TAXONOMY"; then
    ok "ticket-taxonomy.md defines the '$t' type as its own heading"
  else
    bad "ticket-taxonomy.md is MISSING a '### \`$t\`' heading"
  fi
done

# --- type-lock rule: a scope surprise closes-and-links, never relabels -----
# This is the concrete mechanism behind "planning tickets must NEVER be
# conflated with or silently converted into execution tickets."
group "wayfinder — type-lock rule (close-and-link, never relabel in place)"
hasE "$REF_TAXONOMY" 'type never changes in place' \
     "ticket-taxonomy.md states the type-lock rule" \
     "ticket-taxonomy.md is MISSING the type-lock rule statement"
hasE "$REF_TAXONOMY" 'resolved-into-a-new-linked-task-ticket' \
     "ticket-taxonomy.md names the close-and-link resolution by its exact term" \
     "ticket-taxonomy.md is MISSING the resolved-into-a-new-linked-task-ticket term"
hasE "$SKILL" 'never (be )?relabeled in place' \
     "SKILL.md states tickets are never relabeled in place" \
     "SKILL.md is MISSING the never-relabeled-in-place clause"

# --- frontier definition: computed, not cached ------------------------------
group "wayfinder — frontier definition is the computed-not-cached heuristic"
hasE "$REF_BREAKDOWN" 'frontier is the set of open tickets whose every listed dependency is CLOSED' \
     "task-breakdown.md states the exact frontier definition" \
     "task-breakdown.md is MISSING the exact frontier definition"
hasE "$REF_BREAKDOWN" 'never cached' \
     "task-breakdown.md forbids caching frontier membership" \
     "task-breakdown.md does NOT forbid caching frontier membership"

# --- cycle check: mechanical DAG-traversal revisit check --------------------
group "wayfinder — cycle check is a mechanical revisit-on-current-path test"
hasE "$REF_BREAKDOWN" 'revisits a ticket already on the current (resolution )?path' \
     "task-breakdown.md states the cycle check as a path-revisit test" \
     "task-breakdown.md is MISSING the path-revisit cycle-check definition"
hasE "$REF_BREAKDOWN" '[Ss]plit a ticket' \
     "task-breakdown.md names 'split a ticket' as a cycle-break move" \
     "task-breakdown.md is MISSING 'split a ticket' as a cycle-break move"
hasE "$REF_BREAKDOWN" '[Dd]emote (one edge|it) (from|to) .{0,20}informs' \
     "task-breakdown.md names demoting an edge to 'informs' as a cycle-break move" \
     "task-breakdown.md is MISSING the demote-to-informs cycle-break move"

# --- fog-of-war: the one-sentence-with-a-question-mark test ----------------
group "wayfinder — fog-of-war one-sentence-question test"
hasE "$REF_FOGOFWAR" 'one sentence with a question mark' \
     "fog-of-war.md states the one-sentence-question test" \
     "fog-of-war.md is MISSING the one-sentence-question test"
hasE "$SKILL" 'one sentence with a question mark' \
     "SKILL.md restates the one-sentence-question test in the procedure" \
     "SKILL.md is MISSING the one-sentence-question test in the procedure"
hasE "$REF_FOGOFWAR" 'explicitly out of scope' \
     "fog-of-war.md names the explicitly-out-of-scope bucket" \
     "fog-of-war.md is MISSING the explicitly-out-of-scope bucket"

# --- homelab-board discipline: rendered views are throwaway, never state ---
group "wayfinder — board-vs-reality drift rule (homelab-board discipline)"
hasE "$SKILL" 'must write to the ticket store' \
     "SKILL.md states the control-must-write-or-not-exist rule" \
     "SKILL.md is MISSING the control-must-write-or-not-exist rule"
hasE "$SKILL" 'exactly one (status label|column label)? ?per (ticket|issue)' \
     "SKILL.md states the exactly-one-status-label-per-ticket rule" \
     "SKILL.md is MISSING the exactly-one-status-label-per-ticket rule"

# --- differentiation: 'Not this' section names both orchestrate and grill-me
# The design brief is explicit this is load-bearing, and its precedent
# (verify-before-claim) requires both names to actually appear inside a
# '## Not this' section, not merely somewhere in the file.
group "wayfinder — differentiation names both orchestrate and grill-me"
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
if printf '%s' "$NOT_THIS_BLOCK" | grep -qF 'grill-me'; then
  ok "'## Not this' names grill-me"
else
  bad "'## Not this' does NOT name grill-me"
fi
# '## Not this' must be the section immediately after '## Invariant', per the
# verify-before-claim placement precedent named in the design brief.
HEADINGS_ORDER="$(grep -E '^## ' "$SKILL" | sed -n '1,2p')"
if printf '%s\n' "$HEADINGS_ORDER" | sed -n '1p' | grep -qF '## Invariant' \
   && printf '%s\n' "$HEADINGS_ORDER" | sed -n '2p' | grep -qF '## Not this'; then
  ok "'## Not this' immediately follows '## Invariant' (verify-before-claim precedent)"
else
  bad "'## Not this' does NOT immediately follow '## Invariant' — got order: $(printf '%s' "$HEADINGS_ORDER" | tr '\n' ' | ')"
fi

# --- 'Not this' claims about orchestrate/grill-me are accurate, not just present
# A confident-but-wrong differentiation is a documented failure mode for this
# build. Anchor to a real, structural fact about each neighbouring plugin
# rather than trusting SKILL.md's prose alone: orchestrate's own SKILL.md
# must actually be single-session/no-persistent-ticket-state (it names the
# Workflow tool and returns from one run), and grill-me's own SKILL.md must
# actually be a live, single-session interrogation (it has its own Invariant
# naming "single-session").
group "wayfinder — 'Not this' claims check out against the real neighbouring plugins"
ORCHESTRATE_SKILL="orchestrate/skills/orchestrate/SKILL.md"
ORCHESTRATE_PATH=""
for cand in "$PLUGIN_DIR/../orchestrate/skills/orchestrate/SKILL.md" "plugins/orchestrate/skills/orchestrate/SKILL.md"; do
  [ -f "$cand" ] && ORCHESTRATE_PATH="$cand" && break
done
if [ -n "$ORCHESTRATE_PATH" ]; then
  hasE "$ORCHESTRATE_PATH" 'Workflow tool' \
       "orchestrate's real SKILL.md does name the Workflow tool, matching wayfinder's claim" \
       "orchestrate's real SKILL.md does NOT name the Workflow tool — wayfinder's claim is stale"
else
  bad "could not locate orchestrate's real SKILL.md to check wayfinder's claim against"
fi
GRILLME_PATH=""
for cand in "$PLUGIN_DIR/../grill-me/skills/grill-me/SKILL.md" "plugins/grill-me/skills/grill-me/SKILL.md"; do
  [ -f "$cand" ] && GRILLME_PATH="$cand" && break
done
if [ -n "$GRILLME_PATH" ]; then
  hasE "$GRILLME_PATH" 'single-session' \
       "grill-me's real SKILL.md does describe itself as single-session, matching wayfinder's claim" \
       "grill-me's real SKILL.md does NOT describe itself as single-session — wayfinder's claim is stale"
else
  bad "could not locate grill-me's real SKILL.md to check wayfinder's claim against"
fi

# --- no leftover scaffold placeholders --------------------------------------
group "wayfinder — no unfilled TODOs"
if grep -rln "TODO" "$PLUGIN_DIR" 2>/dev/null | grep -v '/evals/cheap/checks\.sh$' | grep -q .; then
  bad "unfilled TODO marker(s) remain under $PLUGIN_DIR — scaffold prose was never replaced"
else
  ok "no TODO markers under $PLUGIN_DIR (outside this checks.sh)"
fi
