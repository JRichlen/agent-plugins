# Cheap eval pack for the 'verify-before-claim' plugin — SOURCED by
# evals/cheap/run.sh with cwd = repo root; inherits ok/bad/group and
# $PLUGIN_NAME / $PLUGIN_DIR (and the shared has/hasE/lacksE helpers defined
# once in run.sh).
#
# What this plugin's invariant actually is: no claim of fact, completion, or
# reproduction may be asserted as settled without the specific falsifying
# check having been run, its output shown next to the claim, and any residual
# uncertainty flagged inline rather than smoothed into confident prose. The
# design is progressive disclosure — a core procedure that is always active,
# plus four reference files that load only on their own trigger — so these
# checks defend BOTH the structural wiring (all four files exist and are
# actually named in the dispatcher table) and the content invariants (the
# skill practices what it preaches: it does not use, unflagged, the exact
# vague phrases it bans).

SKILL="$PLUGIN_DIR/skills/verify-before-claim/SKILL.md"
REFDIR="$PLUGIN_DIR/skills/verify-before-claim/references"
AGENTS="$PLUGIN_DIR/AGENTS.md"
README="$PLUGIN_DIR/README.md"
COMMAND="$PLUGIN_DIR/commands/verify-before-claim.md"

REF1="$REFDIR/pre-claim-reproduction.md"
REF2="$REFDIR/uncertainty-flagging.md"
REF3="$REFDIR/primary-source-research.md"
REF4="$REFDIR/skill-behavior-verification.md"

# --- structure: the plugin's advertised surface actually exists ------------
group "verify-before-claim — structure"
for f in \
  "$PLUGIN_DIR/.claude-plugin/plugin.json" \
  "$SKILL" \
  "$AGENTS" \
  "$README" \
  "$COMMAND"; do
  if [ -f "$f" ]; then ok "present: $f"; else bad "MISSING: $f"; fi
done

# --- all four reference files exist on disk ---------------------------------
# Positive, structural: the dispatcher table is worthless if the file it
# points at was never written.
group "verify-before-claim — all four reference files exist on disk"
for f in "$REF1" "$REF2" "$REF3" "$REF4"; do
  if [ -f "$f" ]; then ok "present: $f"; else bad "MISSING reference file: $f"; fi
done

# --- dispatcher table names all four reference files -----------------------
# Existing on disk isn't enough — SKILL.md's dispatcher table must actually
# cite each filename, or progressive disclosure is claimed but not wired: an
# agent reading SKILL.md would have no way to discover the file exists.
group "verify-before-claim — dispatcher table names all four reference files"
for name in \
  "pre-claim-reproduction.md" \
  "uncertainty-flagging.md" \
  "primary-source-research.md" \
  "skill-behavior-verification.md"; do
  if grep -qF "references/$name" "$SKILL"; then
    ok "SKILL.md dispatcher table names references/$name"
  else
    bad "SKILL.md dispatcher table is MISSING references/$name"
  fi
done

# --- invariant text survives verbatim in both SKILL.md and AGENTS.md -------
# The scaffold wrote this into both at generation time from --invariant; a
# later edit to one and not the other is a real drift risk this catches.
group "verify-before-claim — invariant text present verbatim"
INVARIANT_MARKER='backed by the specific check that would prove it false, performed directly'
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

# --- the second half of the invariant: residual uncertainty must be flagged,
# never smoothed --------------------------------------------------------------
group "verify-before-claim — residual-uncertainty clause present"
hasE "$SKILL" 'residual uncertainty' \
     "SKILL.md names residual uncertainty explicitly" \
     "SKILL.md is MISSING the residual-uncertainty clause of the invariant"
hasE "$SKILL" 'never (be )?smoothed' \
     "SKILL.md forbids smoothing uncertainty into confident prose" \
     "SKILL.md does not forbid smoothing residual uncertainty into confident prose"

# --- differentiation: 'Not this' section names both neighbouring plugins ---
# The design brief is explicit this is load-bearing. Require both plugin
# names to actually appear inside a '## Not this' section, not merely
# somewhere in the file (a passing mention elsewhere would not tell a reader
# WHY this plugin differs).
group "verify-before-claim — differentiation names both neighbouring plugins"
NOT_THIS_BLOCK="$(awk '/^## Not this/{flag=1; next} /^## /{flag=0} flag' "$SKILL")"
if printf '%s' "$NOT_THIS_BLOCK" | grep -q .; then
  ok "SKILL.md has a non-empty '## Not this' section"
else
  bad "SKILL.md has NO '## Not this' section (or it is empty)"
fi
if printf '%s' "$NOT_THIS_BLOCK" | grep -qF 'second-opinion'; then
  ok "'## Not this' names second-opinion"
else
  bad "'## Not this' does NOT name second-opinion"
fi
if printf '%s' "$NOT_THIS_BLOCK" | grep -qF 'orchestrate'; then
  ok "'## Not this' names orchestrate"
else
  bad "'## Not this' does NOT name orchestrate"
fi

# --- the skill practices what it preaches -----------------------------------
# The banned vague phrases are deliberately QUOTED once, by name, inside the
# clearly delimited ANTI-PATTERN-LIST block (a positive assertion — the list
# must name them). Outside that block, in the skill's own procedural prose,
# none of them may appear unflagged — that's the "no 'should work' left in
# its own procedure text" requirement from the design brief. Stripping the
# delimited block before scanning is what keeps this a real check instead of
# the exact naive-negative-grep failure mode (matching the plugin's own
# documentation of the thing it bans) that has broken past plugins' evals.
group "verify-before-claim — anti-pattern list present, and not violated outside it"

if grep -qF '<!-- ANTI-PATTERN-LIST-START -->' "$SKILL" && grep -qF '<!-- ANTI-PATTERN-LIST-END -->' "$SKILL"; then
  ok "SKILL.md has a delimited anti-pattern list block"
else
  bad "SKILL.md is MISSING the delimited anti-pattern list block (ANTI-PATTERN-LIST-START/END markers)"
fi

for phrase in "should work" "this looks correct" "presumably" "I'm confident this is right"; do
  if grep -qF "$phrase" "$SKILL"; then
    ok "anti-pattern list names '$phrase'"
  else
    bad "anti-pattern list is MISSING '$phrase'"
  fi
done

STRIPPED="$(sed '/<!-- ANTI-PATTERN-LIST-START -->/,/<!-- ANTI-PATTERN-LIST-END -->/d' "$SKILL")"
VIOLATION=0
for phrase in "should work" "this looks correct" "presumably" "I'm confident this is right"; do
  if printf '%s' "$STRIPPED" | grep -qiF "$phrase"; then
    bad "banned phrase '$phrase' appears UNFLAGGED outside the anti-pattern list — the skill violates its own rule"
    VIOLATION=1
  fi
done
if [ "$VIOLATION" -eq 0 ]; then
  ok "no banned vague phrase appears outside the anti-pattern list in SKILL.md"
fi

for f in "$REF1" "$REF2" "$REF3" "$REF4" "$AGENTS" "$README" "$COMMAND"; do
  REFVIOLATION=0
  for phrase in "should work" "this looks correct" "presumably" "I'm confident this is right"; do
    if grep -qiF "$phrase" "$f" 2>/dev/null; then
      bad "banned phrase '$phrase' appears in $f — the plugin's own prose violates the rule it defends"
      REFVIOLATION=1
    fi
  done
  if [ "$REFVIOLATION" -eq 0 ]; then
    ok "no banned vague phrase in $f"
  fi
done

# --- no leftover scaffold placeholders --------------------------------------
group "verify-before-claim — no unfilled TODOs"
if grep -rln "TODO" "$PLUGIN_DIR" 2>/dev/null | grep -v '/evals/cheap/checks\.sh$' | grep -q .; then
  bad "unfilled TODO marker(s) remain under $PLUGIN_DIR — scaffold prose was never replaced"
else
  ok "no TODO markers under $PLUGIN_DIR (outside this checks.sh)"
fi
