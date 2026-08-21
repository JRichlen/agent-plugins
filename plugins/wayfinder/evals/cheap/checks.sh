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
# Existing on disk isn't enough — the procedure STEPS must actually point a
# reader at each file, or the references/ split is unwired documentation.
# Scoped to '## The procedure' section only: the later '## Every judgment
# call...' summary also cites all three files, and a naive whole-file grep
# would stay green even if every in-procedure pointer were deleted (the
# progressive-disclosure wiring the citations exist to prove would then be
# gone while this check kept passing on the summary's restatement alone).
group "wayfinder — SKILL.md procedure cites all three reference files"
# Collapsed to a single line before matching: markdown line-wrapping can put
# whitespace inside a phrase we need to match as one run of text, and a
# collapsed grep is immune to a rewrap moving that whitespace around.
PROCEDURE_BLOCK="$(awk '/^## The procedure/{flag=1; next} /^## /{flag=0} flag' "$SKILL" | tr -s '[:space:]' ' ')"
for name in "ticket-taxonomy.md" "task-breakdown.md" "fog-of-war.md"; do
  if printf '%s' "$PROCEDURE_BLOCK" | grep -qF "references/$name"; then
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
# The heading and the marker sentence above can both survive while the
# close-and-link PROCEDURE BODY underneath is gutted (e.g. replaced with the
# exact in-place relabel the invariant forbids) — a marker-phrase test alone
# can't tell. Scope to the type-lock section and require its real numbered
# steps, anchored to structure (start-of-line "N. ...") so restating them in
# prose elsewhere can't satisfy this either.
TYPE_LOCK_BLOCK="$(awk '/^## The type-lock rule/{flag=1; next} /^## /{flag=0} flag' "$REF_TAXONOMY")"
if printf '%s' "$TYPE_LOCK_BLOCK" | grep -qE '^1\. Close the original ticket'; then
  ok "ticket-taxonomy.md's close-and-link procedure has a real step 1 (close the original ticket)"
else
  bad "ticket-taxonomy.md's close-and-link procedure is MISSING step 1 (close the original ticket) — marker phrase alone is not the real procedure"
fi
if printf '%s' "$TYPE_LOCK_BLOCK" | grep -qE '^2\. Open a new ticket, typed `task`'; then
  ok "ticket-taxonomy.md's close-and-link procedure has a real step 2 (open a new linked task ticket)"
else
  bad "ticket-taxonomy.md's close-and-link procedure is MISSING step 2 (open a new linked task ticket)"
fi
if printf '%s' "$TYPE_LOCK_BLOCK" | grep -qE '^3\. The new `task` ticket goes through fog-of-war charting'; then
  ok "ticket-taxonomy.md's close-and-link procedure has a real step 3 (new ticket re-enters fog-of-war charting)"
else
  bad "ticket-taxonomy.md's close-and-link procedure is MISSING step 3 (new ticket re-enters fog-of-war charting)"
fi

# --- frontier definition: computed, not cached ------------------------------
group "wayfinder — frontier definition is the computed-not-cached heuristic"
hasE "$REF_BREAKDOWN" 'frontier is the set of open tickets whose every listed dependency is CLOSED' \
     "task-breakdown.md states the exact frontier definition" \
     "task-breakdown.md is MISSING the exact frontier definition"
hasE "$REF_BREAKDOWN" 'never cached' \
     "task-breakdown.md forbids caching frontier membership" \
     "task-breakdown.md does NOT forbid caching frontier membership"
# The always-loaded SKILL.md restates this same definition in step 2 of its
# own procedure — and nothing above checks THAT copy. SKILL.md could be
# rewritten to directly contradict its own Invariant (a cached "on frontier"
# flag is exactly the drift the invariant forbids) with no check firing.
# Scoped to step 2 only, so a correct restatement elsewhere in the file can't
# stand in for step 2's own text.
STEP2_BLOCK="$(awk '/^### 2\. Build the dependency graph/{flag=1; next} /^### /{flag=0} flag' "$SKILL" | tr -s '[:space:]' ' ')"
if printf '%s' "$STEP2_BLOCK" | grep -qF 'every listed dependency is CLOSED'; then
  ok "SKILL.md's own procedure (step 2) states the frontier = every listed dependency is CLOSED"
else
  bad "SKILL.md's procedure (step 2) is MISSING or contradicts the frontier definition"
fi
if printf '%s' "$STEP2_BLOCK" | grep -qF 'never a cached'; then
  ok "SKILL.md's own procedure (step 2) forbids caching frontier membership"
else
  bad "SKILL.md's procedure (step 2) does NOT forbid caching frontier membership — cached-flag drift risk"
fi

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
# Scoped to step 3 itself, not the whole file — the '## Every judgment call'
# summary near the end also restates this phrase, so a whole-file grep stays
# green even if the procedure's own test (SKILL.md's step 3) is replaced with
# vague guidance ("use your judgment..."). The summary can't stand in for the
# step that actually owns the rule.
STEP3_BLOCK="$(awk '/^### 3\. Mark unknowns explicitly/{flag=1; next} /^### /{flag=0} flag' "$SKILL" | tr -s '[:space:]' ' ')"
if printf '%s' "$STEP3_BLOCK" | grep -qE 'one sentence with a question mark'; then
  ok "SKILL.md's own procedure (step 3) states the one-sentence-question test"
else
  bad "SKILL.md's procedure (step 3) is MISSING the one-sentence-question test"
fi
hasE "$REF_FOGOFWAR" 'explicitly out of scope' \
     "fog-of-war.md names the explicitly-out-of-scope bucket" \
     "fog-of-war.md is MISSING the explicitly-out-of-scope bucket"

# --- homelab-board discipline: rendered views are throwaway, never state ---
group "wayfinder — board-vs-reality drift rule (homelab-board discipline)"
hasE "$SKILL" 'must write to the ticket store' \
     "SKILL.md states the control-must-write-or-not-exist rule" \
     "SKILL.md is MISSING the control-must-write-or-not-exist rule"
# Scoped to step 0 (where wayfinder states this as ITS OWN operative rule),
# not the whole file — the '## Modeled on homelab-board' narrative section
# also matches this phrase while only describing homelab-board itself, so a
# whole-file grep stays green even if wayfinder's own rule at step 0 is
# inverted ("as many [labels] as you want, blockers optional").
STEP0_BLOCK="$(awk '/^### 0\. Detect the ticket store/{flag=1; next} /^### /{flag=0} flag' "$SKILL" | tr -s '[:space:]' ' ')"
if printf '%s' "$STEP0_BLOCK" | grep -qE 'exactly one (status label|column label)? ?per (ticket|issue)'; then
  ok "SKILL.md's own procedure (step 0) states the exactly-one-status-label-per-ticket rule"
else
  bad "SKILL.md's procedure (step 0) is MISSING the exactly-one-status-label-per-ticket rule"
fi

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
# build. The PRIOR version of this group never opened wayfinder's own
# SKILL.md at all — it only grepped the neighbours' files for strings
# wayfinder cannot influence, so no edit to wayfinder's "Not this" section
# could ever turn it red. Fixed here to do both halves: (1) read wayfinder's
# OWN claim text (scoped to its "Not this" section, reusing the same
# structural scoping as the section-presence group above) and require the
# SPECIFIC property it attributes to each neighbour, so a false claim written
# INTO wayfinder's file is caught directly; (2) cross-check that same
# property string genuinely appears in the neighbour's real SKILL.md, so a
# claim that happens to be internally consistent but factually wrong about
# the neighbour is also caught.
group "wayfinder — 'Not this' claims check out against the real neighbouring plugins"
# Scoped to each neighbour's OWN bullet paragraph, not the whole "Not this"
# section: the section also carries a closing "load-bearing distinction"
# paragraph that summarizes BOTH neighbours together (it says "single-session"
# too), which could otherwise let a gutted per-neighbour claim hide behind
# the summary sentence — the same substrate-restatement trap this whole pass
# is fixing, just one section down. Anchoring stop-markers to the next
# bullet/paragraph keeps each check honest about which text it's reading.
ORCH_CLAIM_BLOCK="$(awk '/^- \*\*orchestrate\*\*/{flag=1} /^- \*\*grill-me\*\*/{flag=0} flag' "$SKILL" | tr -s '[:space:]' ' ')"
GRILLME_CLAIM_BLOCK="$(awk '/^- \*\*grill-me\*\*/{flag=1} /^The load-bearing distinction/{flag=0} flag' "$SKILL" | tr -s '[:space:]' ' ')"

ORCHESTRATE_PATH=""
for cand in "$PLUGIN_DIR/../orchestrate/skills/orchestrate/SKILL.md" "plugins/orchestrate/skills/orchestrate/SKILL.md"; do
  [ -f "$cand" ] && ORCHESTRATE_PATH="$cand" && break
done
if [ -n "$ORCHESTRATE_PATH" ]; then
  if printf '%s' "$ORCH_CLAIM_BLOCK" | grep -qF 'no persistent state across sessions'; then
    ok "wayfinder's OWN orchestrate paragraph claims it has no persistent state across sessions"
  else
    bad "wayfinder's orchestrate paragraph no longer claims no persistent state across sessions — differentiation may now be false or gutted"
  fi
  if printf '%s' "$ORCH_CLAIM_BLOCK" | grep -qE 'caller-supplied .dimensions. list'; then
    ok "wayfinder's OWN orchestrate paragraph attributes the 'dimensions' input to orchestrate"
    if grep -qF 'dimensions' "$ORCHESTRATE_PATH"; then
      ok "orchestrate's real SKILL.md corroborates: it genuinely takes a 'dimensions' input"
    else
      bad "orchestrate's real SKILL.md does NOT mention 'dimensions' — wayfinder's claim is stale"
    fi
  else
    bad "wayfinder's orchestrate paragraph no longer attributes the 'dimensions' input to orchestrate"
  fi
else
  bad "could not locate orchestrate's real SKILL.md to check wayfinder's claim against"
fi

GRILLME_PATH=""
for cand in "$PLUGIN_DIR/../grill-me/skills/grill-me/SKILL.md" "plugins/grill-me/skills/grill-me/SKILL.md"; do
  [ -f "$cand" ] && GRILLME_PATH="$cand" && break
done
if [ -n "$GRILLME_PATH" ]; then
  if printf '%s' "$GRILLME_CLAIM_BLOCK" | grep -qE 'single-session'; then
    ok "wayfinder's OWN grill-me paragraph claims grill-me is single-session"
    if grep -qE 'single-session' "$GRILLME_PATH"; then
      ok "grill-me's real SKILL.md corroborates: it genuinely describes itself as single-session"
    else
      bad "grill-me's real SKILL.md does NOT describe itself as single-session — wayfinder's claim is stale"
    fi
  else
    bad "wayfinder's grill-me paragraph no longer claims grill-me is single-session"
  fi
  if printf '%s' "$GRILLME_CLAIM_BLOCK" | grep -qF 'no ticket store, no persistence across sessions'; then
    ok "wayfinder's OWN grill-me paragraph claims grill-me has no ticket store or cross-session persistence"
  else
    bad "wayfinder's grill-me paragraph no longer claims grill-me has no ticket store or cross-session persistence — differentiation may now be false or gutted"
  fi
else
  bad "could not locate grill-me's real SKILL.md to check wayfinder's claim against"
fi

# --- no leftover scaffold placeholders --------------------------------------
# Scans checks.sh itself too, unlike the prior bare-word version this
# replaces (which excluded checks.sh entirely, so an unfilled scaffold
# placeholder left in the eval pack itself could never fire). Matched on the
# actual scaffold marker shape (the bare word immediately followed by a
# colon, per scaffold-plugin.sh) rather than the bare word alone, so this
# file's own prose describing the check ("no unfilled placeholders", the
# messages below) — which never uses that colon shape — can't self-trigger a
# false positive.
TODO_MARKER="TOD""O:"
group "wayfinder — no unfilled TODOs"
if grep -rlF "$TODO_MARKER" "$PLUGIN_DIR" 2>/dev/null | grep -q .; then
  bad "unfilled scaffold placeholder marker(s) remain under $PLUGIN_DIR — scaffold prose was never replaced"
else
  ok "no unfilled scaffold placeholder markers under $PLUGIN_DIR"
fi
