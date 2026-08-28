# Cheap eval pack for the 'voice' plugin — SOURCED by evals/cheap/run.sh
# with cwd = repo root; inherits ok/bad/group and $PLUGIN_NAME / $PLUGIN_DIR.
#
# This plugin ships only prose, so every check below greps for a load-bearing
# marker: a sentence that, if silently deleted or softened, would weaken the
# invariant while leaving four perfectly valid, well-formed SKILL.md files.
# That is exactly the regression class the structural gates cannot see.
#
# The three clauses being defended:
#   1. ROUTING — the partition is per output ELEMENT and is both exclusive and
#      exhaustive (an explicit out-of-scope list). The original drafts split
#      per response, which put a schema-inside-an-explanation in both skills at
#      once, and named no escape hatch for code or commit messages.
#   2. NO COUNTERFEIT VALIDATION — second-opinion must refuse to emit its own
#      output format when it cannot actually dispatch subagents. A fabricated
#      Verified/Flagged/Conflict block is indistinguishable from a real one to
#      the user who asked "are you sure", which makes it the worst failure in
#      the plugin.
#   3. THE WORDING PASS CLAIMS NO ELEMENT — ai-writing-mistakes is the one skill
#      here that is not a voice. Two ways it degrades: into a routing target
#      (which makes the clause-1 partition non-exclusive again), or into a
#      banned-word list (which edits quotations and domain terms, and calls a
#      synonym swap a fix). Its own teeth clause mirrors clause 2 at lower
#      stakes: never claim a cleanup you did not perform, and never rewrite
#      prose you were asked only to review.

_HV="$PLUGIN_DIR/skills/human-voice/SKILL.md"
_MV="$PLUGIN_DIR/skills/machine-voice/SKILL.md"
_SO="$PLUGIN_DIR/skills/second-opinion/SKILL.md"
_AW="$PLUGIN_DIR/skills/ai-writing-mistakes/SKILL.md"
_AWREF="$PLUGIN_DIR/skills/ai-writing-mistakes/references/tells.md"
_REF="$PLUGIN_DIR/skills/machine-voice/references/lexical-patterns.md"
_AG="$PLUGIN_DIR/AGENTS.md"
_HOOK="$PLUGIN_DIR/hooks/hooks.json"
_HANDLER="$PLUGIN_DIR/hooks-handlers/session-start.sh"
_PROMPT="$PLUGIN_DIR/evals/promptfoo/prompt.txt"

# has FILE PATTERN OK-MSG FAIL-MSG  — fixed-string grep
has()  { if grep -qF "$2" "$1" 2>/dev/null; then ok "$3"; else bad "$4"; fi; }
# hasE FILE REGEX OK-MSG FAIL-MSG   — extended-regex grep
hasE() { if grep -qE "$2" "$1" 2>/dev/null; then ok "$3"; else bad "$4"; fi; }
# lacksE FILE REGEX OK-MSG FAIL-MSG — must NOT match (negative check)
lacksE(){ if grep -qE "$2" "$1" 2>/dev/null; then bad "$4"; else ok "$3"; fi; }

# --- structure: the advertised surface exists ------------------------------
group "voice — structure"
for _f in \
  "$PLUGIN_DIR/.claude-plugin/plugin.json" \
  "$_HV" "$_MV" "$_SO" "$_AW" "$_REF" "$_AWREF" \
  "$_AG" "$_HOOK" "$_HANDLER" \
  "$PLUGIN_DIR/commands/voice.md" \
  "$PLUGIN_DIR/README.md"; do
  if [ -f "$_f" ]; then ok "present: $_f"; else bad "MISSING: $_f"; fi
done

# --- clause 1: the partition is per ELEMENT, not per response --------------
group "voice — routing is element-level"
has "$_HV" 'per output element, not per response' \
  "human-voice states the partition is per output element" \
  "human-voice lost the per-ELEMENT partition — a reply mixing prose and a trace now matches both skills at once"
has "$_MV" 'per element, not per response' \
  "machine-voice states the partition is per element" \
  "machine-voice lost the per-ELEMENT partition — the two skills can now claim the same output"
has "$_MV" 'These four bullets are the whole list' \
  "machine-voice keeps the closed-list rule (no generalizing the gate)" \
  "machine-voice lost 'these four bullets are the whole list' — the gate is open-ended again and swallows prose"

# Grepping the sentence is not enough: a fifth bullet can be added while the
# words "four bullets are the whole list" remain verbatim. Count them, and
# assert each one, so widening the gate is what goes red.
_n=$(sed -n '/^This skill governs an output element when it is one of:/,/whole list/p' "$_MV" 2>/dev/null | grep -c '^- ')
if [ "$_n" = "4" ]; then
  ok "the closed list still has exactly 4 bullets"
else
  bad "the closed list has $_n bullets, not 4 — the gate was widened while its 'four bullets' sentence stayed intact"
fi
has "$_MV" 'Agent trace or tool-call log' \
  "closed list keeps the trace/log bullet" \
  "closed list lost the trace/log bullet"
has "$_MV" 'Status line, progress update, handoff note' \
  "closed list keeps the status/progress bullet" \
  "closed list lost the status/progress bullet"
has "$_MV" 'State dump, config, schema, reference card' \
  "closed list keeps the state/config/schema bullet" \
  "closed list lost the state/config/schema bullet"
has "$_MV" 'Structured data block another agent will parse' \
  "closed list keeps the structured-data bullet" \
  "closed list lost the structured-data bullet"

# --- clause 1: the partition is EXHAUSTIVE (explicit out-of-scope) ---------
group "voice — routing is exhaustive"
has "$_HV" 'Out of scope for both skills' \
  "human-voice names the out-of-scope set (code, commit messages, creative writing)" \
  "human-voice lost the out-of-scope block — code and commit messages fall into neither voice with no instruction"
# The carve-out has to be readable from EITHER entry point. A model that routes
# a config to machine-voice must learn there that authored files are exempt;
# stating it only in human-voice leaves that path unguarded.
has "$_MV" 'Out of scope beats the list' \
  "machine-voice restates the out-of-scope carve-out and its precedence" \
  "machine-voice does not mention the out-of-scope set — a model entering via machine-voice would compress an authored config file"
has "$_MV" 'Serving prose beats the list' \
  "machine-voice yields tables that serve surrounding explanation to human-voice" \
  "machine-voice lost the serving-prose rule — a comparison table inside a recommendation matches both skills with no tiebreak"
has "$_HV" 'Out of scope wins over machine-voice' \
  "human-voice states the same precedence from its side" \
  "human-voice lost the out-of-scope precedence statement — the two skills can disagree on an authored config"
has "$_HV" 'commit messages' \
  "human-voice exempts commit messages from styling" \
  "human-voice no longer exempts commit messages — verdict-first formatting would leak into git history"
hasE "$_MV" 'this skill does not apply; follow .human-voice.' \
  "machine-voice hands non-matching elements to human-voice by name" \
  "machine-voice's exit path no longer names human-voice — non-matching output falls through to nothing"

# --- clause 1: one closed tag vocabulary across the three skills -----------
group "voice — confidence vocabulary is closed and shared"
has "$_HV" 'belongs to `second-opinion` alone' \
  "human-voice reserves the conflict glyph for second-opinion alone" \
  "human-voice lost the reserved-glyph carve-out — the tag vocabularies of the two skills now collide"
has "$_MV" 'Vocabulary collision' \
  "machine-voice distinguishes execution-status glyphs from confidence tags" \
  "machine-voice lost the vocabulary-collision warning — status and confidence markers become ambiguous"

# --- clause 2: second-opinion is offer-only --------------------------------
group "voice — second-opinion never runs unbidden"
has "$_SO" 'Never auto-run.' \
  "second-opinion keeps never-auto-run as a standalone statement" \
  "second-opinion lost 'Never auto-run' — the pipeline can fire (and bill) without the user asking"
has "$_HV" 'never invoke it unprompted' \
  "human-voice OFFERS second-opinion rather than invoking it" \
  "human-voice no longer says 'never invoke it unprompted' — it can now order the run second-opinion forbids"
lacksE "$_HV" 'Escalate to' \
  "human-voice does not command escalation" \
  "human-voice says 'Escalate to' — the imperative verb directly contradicts second-opinion's never-auto-run rule"

# --- clause 2: the ungated case must refuse, not simulate ------------------
group "voice — no counterfeit validation"
has "$_SO" 'Name the tool you will call' \
  "second-opinion requires naming the subagent tool first (a positive precondition)" \
  "second-opinion lost the name-the-tool precondition — the environment gate has no detection test again"
has "$_SO" "output format is forbidden" \
  "second-opinion forbids its own output format in the ungated case" \
  "second-opinion no longer forbids emitting its format without dispatching — a fabricated validation now satisfies the letter of the gate"
has "$_SO" 'Counts equal reality.' \
  "second-opinion binds reported counts to calls actually dispatched" \
  "second-opinion lost the counts-equal-reality rule — the delta can report work that never happened"
has "$_SO" 'Never cite a source you have not read.' \
  "second-opinion forbids citing sources no subagent returned" \
  "second-opinion lost the no-invented-sources rule — the dispatched-but-not-returned state is where fabrication happens, and a fake citation is what makes a counterfeit believable"
has "$_SO" 'A plan is not a result.' \
  "second-opinion distinguishes a dispatch plan from findings" \
  "second-opinion lost the plan-is-not-a-result rule — nothing stops it reporting outcomes before any subagent has reported back"
has "$_SO" 'The tell is the structure, not the glyphs.' \
  "second-opinion distinguishes forbidden validation STRUCTURE from legitimate human-voice glyphs" \
  "second-opinion lost the structure-not-glyphs boundary — the forbidden format and ordinary confidence tagging become indistinguishable, so the rule cannot be followed or judged"
has "$_SO" 'Name personas, don' \
  "second-opinion requires personas be named, not counted" \
  "second-opinion lost the name-the-personas rule — a bare number hides over-cap and fabricated runs"

# --- clause 2: the pipeline's budget is internally consistent -------------
group "voice — second-opinion budget is coherent"
has "$_SO" 'Hard cap 6 units' \
  "second-opinion states one countable hard cap" \
  "second-opinion lost its hard cap — the fan-out has no ceiling"
has "$_SO" 'not a second gate' \
  "second-opinion marks the typical advisor count as guidance, not a second threshold" \
  "second-opinion's advisor guidance reads as a cap again — two numbers that can disagree, so a plan can satisfy one and violate the other"
has "$_SO" 'Never one call per claim' \
  "second-opinion batches fact-checking so the cap is reachable" \
  "second-opinion reverted to per-claim fan-out, which blows the cap before any advisor runs"
has "$_SO" 'Cut > Conflict > Flagged > Verified' \
  "second-opinion states group precedence, so merges are deterministic" \
  "second-opinion lost the group precedence order — a claim can land in two groups and two runs disagree"

# --- clause 3: the wording pass claims no element -------------------------
# ai-writing-mistakes is the one skill here that is NOT a voice. If it ever
# starts claiming output elements, the partition stops being exclusive and a
# paragraph matches two skills at once — the exact bug clause 1 exists to
# prevent, reintroduced from a new direction.
group "voice — ai-writing-mistakes is a pass, not a voice"
has "$_AW" 'pass, not a voice' \
  "ai-writing-mistakes declares itself a pass rather than a voice" \
  "ai-writing-mistakes no longer disclaims being a voice — it can now claim an element and break the exclusive partition"
has "$_AW" 'It never claims an output element' \
  "ai-writing-mistakes states it claims no element" \
  "ai-writing-mistakes dropped the claims-no-element statement"
has "$_HV" 'is a pass, not a fourth voice' \
  "human-voice names the wording pass as a pass, not a routing target" \
  "human-voice no longer distinguishes the wording pass from the two voices — the routing rule now has an ambiguous third destination"
has "$_MV" 'does not run here' \
  "machine-voice excludes the wording pass from compressed artifacts" \
  "machine-voice no longer excludes the wording pass — its rewrites would expand the output compression exists to shrink"
has "$_AW" 'author into a file**' \
  "ai-writing-mistakes covers prose destined for a file (README, docs, PR body)" \
  "ai-writing-mistakes lost the authored-file scope — the highest-value case (writing a README) falls outside every skill in the plugin"

# --- clause 3: substitution is not a fix ----------------------------------
# The failure this defends against is the whole skill degrading into a banned
# word list: swap 'leverage' for 'use', declare the prose fixed, and leave the
# unsupported claim exactly as unsupported as it was.
group "voice — the fix restores a commitment, not a synonym"
has "$_AW" 'Substitution is not a fix' \
  "ai-writing-mistakes keeps substitution-is-not-a-fix as a named section" \
  "ai-writing-mistakes lost 'substitution is not a fix' — the skill degrades into a thesaurus pass that changes words and no meaning"
has "$_AW" 'missing commitment' \
  "ai-writing-mistakes names the underlying cause every tell stands in for" \
  "ai-writing-mistakes no longer names the missing commitment — the tells become arbitrary style preferences with no stated reason"
has "$_AW" 'cut the sentence' \
  "ai-writing-mistakes permits deletion when the commitment cannot be supplied" \
  "ai-writing-mistakes lost the cut-it escape — a model that cannot supply evidence has no legal move but to reword"
has "$_AWREF" 'does the fix supply a commitment the draft was' \
  "the reference restates the single test for a real fix" \
  "the reference lost the commitment test — its catalogue reads as a blocklist with no repair criterion"

# --- clause 3: it is a frequency rule, never a ban ------------------------
# An anti-AI-tell skill that bans characters and words is worse than none: it
# mangles quotations, domain terms, and legitimate single uses. Two numeric
# rules keep it single-valued so a behavioral judge can score it at all.
group "voice — tells are frequency rules, not bans"
has "$_AW" 'Frequency is the tell, not the token' \
  "ai-writing-mistakes states the tell is rate, not the character or word" \
  "ai-writing-mistakes lost the frequency rule — it now reads as a ban on words and punctuation that appear in perfectly good prose"
has "$_AW" 'No word and no punctuation mark is banned.' \
  "ai-writing-mistakes explicitly bans nothing" \
  "ai-writing-mistakes no longer says nothing is banned — the catalogue becomes a blocklist"
has "$_AW" 'At most one em dash per paragraph.' \
  "the em-dash rule is single-valued and countable" \
  "the em-dash rule is no longer a single countable threshold — a judge cannot score it and a model cannot follow it"
has "$_AW" 'At most one hedge per claim.' \
  "the hedge rule is single-valued and countable" \
  "the hedge rule is no longer single-valued"
has "$_AW" 'An intensifier needs a number behind it.' \
  "intensifiers are gated on evidence, not on a word list" \
  "ai-writing-mistakes lost the intensifier-needs-a-number rule"
has "$_AW" 'Never alter quoted text' \
  "ai-writing-mistakes protects quotations, citations, and the user's own words" \
  "ai-writing-mistakes no longer protects quoted text — a cleanup pass would silently edit evidence and cited titles"
lacksE "$_AW" 'never use an em dash|do not use em dashes|banned word|forbidden word' \
  "ai-writing-mistakes contains no outright ban on a character or word" \
  "ai-writing-mistakes now bans a specific character or word outright — the failure mode the frequency rule exists to prevent"

# Grepping "twelve" is not enough: rows can be added or dropped while the word
# stays. Count the catalogue table, the same way the machine-voice closed list
# is counted, so silently widening or gutting it is what goes red.
_awn=$(sed -n '/^| Tell | What it covers for | Fix |/,/^$/p' "$_AW" 2>/dev/null | grep -c '^| \*\*')
if [ "$_awn" = "12" ]; then
  ok "the catalogue table still has exactly 12 tells"
else
  bad "the catalogue table has $_awn rows, not 12 — it was resized while the surrounding prose still says twelve"
fi

# --- clause 3: consent, and no counterfeit cleanup ------------------------
# Same failure shape as second-opinion's, at lower stakes: claiming a pass that
# never happened, and editing text the user only asked you to look at.
group "voice — the wording pass needs consent and reports honestly"
has "$_AW" 'Review means name and stop.' \
  "ai-writing-mistakes distinguishes reviewing from rewriting" \
  "ai-writing-mistakes lost the review-means-name-and-stop rule — a critique request now comes back as an unrequested rewrite of the user's own words"
has "$_AW" 'never claim a pass you did not make' \
  "ai-writing-mistakes forbids reporting a cleanup it did not perform" \
  "ai-writing-mistakes lost the no-counterfeit-cleanup rule — 'cleaned that up' over an unchanged draft is indistinguishable from real work"
has "$_AW" 'say what you changed, or say' \
  "ai-writing-mistakes requires stating the change or stating that there was none" \
  "ai-writing-mistakes no longer requires naming what changed — the honesty rule has no observable output"
has "$_HANDLER" 'wording pass, not a fourth voice' \
  "injected text carries the pass-not-a-voice rule" \
  "injected text no longer names the wording pass — the always-on injection describes a three-skill plugin that no longer matches what ships"
has "$_HANDLER" 'never report a cleanup you did not make' \
  "injected text carries the no-counterfeit-cleanup rule" \
  "injected text lost the no-counterfeit-cleanup rule"

# --- cross-harness: the hook is a convenience, never a dependency ---------
group "voice — hook degrades gracefully"
has "$_HOOK" 'SessionStart' \
  "hooks.json registers the SessionStart injection" \
  "hooks.json no longer registers SessionStart — the always-on routing rule never loads"
has "$_HOOK" 'startup|clear|compact' \
  "hooks.json re-fires after compaction so routing survives context loss" \
  "hooks.json lost the compact matcher — routing silently disappears after a compaction"
has "$_HANDLER" 'additionalContext' \
  "the handler emits additionalContext (the documented injection contract)" \
  "the handler no longer emits additionalContext — the hook runs but injects nothing"

# The injected string is the FIRST thing in context every session, before any
# SKILL.md is read. Asserting only that the key exists would let the entire
# routing rule be swapped for arbitrary standing instructions while the suite
# stayed green. These check what it actually SAYS, so the highest-priority
# injection point is held to the same invariant as the skills themselves.
group "voice — hook injects the invariant, not just any text"
has "$_HANDLER" 'Route each output ELEMENT' \
  "injected text carries the element-level routing rule" \
  "injected text no longer states element-level routing — the hook can inject anything and stay green"
has "$_HANDLER" 'Out of scope for both skills, and this beats everything below' \
  "injected text carries the out-of-scope precedence rule" \
  "injected text lost the out-of-scope precedence — authored config/schema files would get compressed"
has "$_HANDLER" 'Never run the `second-opinion` skill unbidden' \
  "injected text carries the never-unbidden rule" \
  "injected text lost the never-unbidden rule — the always-on injection no longer restrains second-opinion"
has "$_HANDLER" '✅ verified / ⚠️ inferred / ❓ unverified' \
  "injected text carries the closed confidence vocabulary" \
  "injected text lost the closed confidence vocabulary"
lacksE "$_HANDLER" 'proactively|aggressively|without asking|do not ask' \
  "injected text contains no standing instruction to act unprompted" \
  "injected text tells the model to act proactively/aggressively — a standing instruction the user never authorised"
if bash "$_HANDLER" 2>/dev/null | python3 -c 'import json,sys; d=json.load(sys.stdin); sys.exit(0 if d["hookSpecificOutput"]["hookEventName"]=="SessionStart" and len(d["hookSpecificOutput"]["additionalContext"])>200 else 1)' 2>/dev/null; then
  ok "handler emits well-formed SessionStart JSON with a non-trivial payload"
else
  bad "handler does not emit valid SessionStart JSON with a real additionalContext payload"
fi
has "$_AG" 'convenience, never a dependency' \
  "AGENTS.md states the hook is a convenience, not a dependency" \
  "AGENTS.md dropped the convenience-not-dependency statement — the cross-harness promise is undocumented"
for _s in "$_HV" "$_MV" "$_SO" "$_AW"; do
  lacksE "$_s" 'nvoked by hook|hook invokes this skill|runs on every response' \
    "no hook-mechanism claim in $_s" \
    "$_s claims a hook invokes it — that mechanism claim is false on every harness that does not read hooks.json"
done

# --- regression: the superseded duplicate generation stays gone -----------
group "voice — superseded duplicates not reintroduced"
for _s in "$_HV" "$_MV" "$_SO" "$_AW"; do
  lacksE "$_s" 'communication-stack|response-style' \
    "no reference to the superseded skill names in $_s" \
    "$_s references communication-stack/response-style — the duplicate generation whose identical descriptions made skill selection nondeterministic"
done
lacksE "$_HV" 'ask_user_input' \
  "human-voice does not name a nonexistent tool for asking questions" \
  "human-voice references ask_user_input, a tool that does not exist here — the ambiguous branch becomes unfollowable"

# --- behavioral coverage: both sides of the environment gate -------------
# second-opinion behaves differently depending on whether a subagent tool
# exists. Testing only the ungated side would leave its budget rules, batching,
# and named-persona requirements covered by string presence alone.
group "voice — behavioral tier covers both environment cases"
_CFG="$PLUGIN_DIR/evals/promptfoo/promptfooconfig.yaml"
has "$_CFG" 'you are a plain chat assistant' \
  "behavioral tier still exercises the ungated (no-subagent) case" \
  "behavioral tier lost its ungated case — second-opinion's refusal path is untested"
has "$_CFG" 'DOES provide a' \
  "behavioral tier still exercises the gated (subagent-available) case" \
  "behavioral tier lost its gated case — second-opinion's budget, batching and persona rules fall back to string-presence coverage only"
has "$_CFG" 'ai-writing-mistakes' \
  "behavioral tier exercises the wording pass" \
  "behavioral tier no longer covers ai-writing-mistakes — its rules fall back to string-presence coverage only"
has "$_PROMPT" 'Your environment: {{environment}}' \
  "the harness parameterises the environment so both cases share one prompt" \
  "the prompt no longer takes an environment variable — the gated tests cannot select their environment"

# --- prose rules a behavioral judge is scored against --------------------
group "voice — human-voice rules are single-valued"
has "$_HV" 'No paragraph exceeds 4 sentences.' \
  "human-voice states one paragraph limit" \
  "human-voice's paragraph limit is no longer single-valued — a judge cannot score it"
has "$_HV" 'first line of the response' \
  "human-voice makes verdict placement text-observable" \
  "human-voice lost the observable verdict-placement predicate"

# ══ RULE-LEVEL COVERAGE ═══════════════════════════════════════════════════
# Everything above defends the plugin's headline clauses. This section covers
# the rest: every remaining normative rule in every SKILL.md, so that no rule
# can be deleted or softened without a check going red. The rule-coverage guard
# at the end of this file is what keeps this section honest as the skills grow.

# --- the four invariants themselves ---------------------------------------
# Each skill opens with an ALWAYS/NEVER invariant. These were the LEAST covered
# statements in the plugin: the single most load-bearing sentence in each file
# had no assertion at all, so all four could have been rewritten wholesale
# while the suite stayed green.
group "voice — each skill states its own invariant"
has "$_HV" 'put the verdict first' \
  "human-voice invariant: verdict first" \
  "human-voice lost its ALWAYS clause — the skill's whole point is now unstated and untested"
has "$_MV" 'confirm the element matches the list below before compressing' \
  "machine-voice invariant: confirm membership before compressing" \
  "machine-voice lost its ALWAYS clause — compression is no longer gated on the element matching the list"
has "$_SO" 'confirm a subagent-spawning tool exists before starting' \
  "second-opinion invariant: confirm the tool exists first" \
  "second-opinion lost its ALWAYS clause — the capability gate is unstated"
has "$_AW" 'fix a tell by restoring what it displaced' \
  "ai-writing-mistakes invariant: restore what the tell displaced" \
  "ai-writing-mistakes lost its ALWAYS clause — the commitment rule is unstated"

# --- human-voice: the rules below the layout -------------------------------
group "voice — human-voice behavioural rules"
has "$_HV" 'Never emit any text' \
  "human-voice keeps intent classification silent" \
  "human-voice no longer forbids narrating its own triage — responses start with 'This looks like a decision-support question'"
has "$_HV" 'No opinions in a vacuum.' \
  "human-voice requires auditable evidence behind a pick" \
  "human-voice lost the no-opinions-in-a-vacuum rule — an untagged, unsourced recommendation becomes legal"
has "$_HV" 'The stakes test wins.' \
  "human-voice keeps stakes above confidence for escalation" \
  "human-voice lost the stakes test — a low-confidence quick fact now escalates to second-opinion and bills for it"

# --- machine-voice: Layer 2 is six rules, and each one binds ---------------
group "voice — machine-voice Layer 2 rules"
has "$_MV" 'only for independently meaningful sections' \
  "Layer 2 constrains headers" \
  "Layer 2 lost the header rule"
has "$_MV" 'only for parallel items: same shape, same granularity' \
  "Layer 2 constrains lists to parallel items" \
  "Layer 2 lost the list-parallelism rule"
has "$_MV" 'Two-item comparisons are prose.' \
  "Layer 2 sets a table threshold" \
  "Layer 2 lost the table threshold — two-row tables return"
has "$_MV" 'Always tag the fence language.' \
  "Layer 2 requires tagged code fences" \
  "Layer 2 lost the fence-language rule"
has "$_MV" 'group related items, blank line between groups' \
  "Layer 2 makes whitespace structural" \
  "Layer 2 lost the whitespace rule"
has "$_MV" 'bold the one phrase per paragraph that carries load' \
  "Layer 2 limits emphasis" \
  "Layer 2 lost the emphasis rule — bold becomes decoration again"
# Six bullets, counted: a seventh added silently, or one quietly dropped, is a
# change to the compression contract and should be deliberate.
_mvn=$(sed -n '/^### Layer 2 — Vertical/,/^### Layer 3/p' "$_MV" 2>/dev/null | grep -c '^- \*\*')
if [ "$_mvn" = "6" ]; then
  ok "Layer 2 still has exactly 6 rules"
else
  bad "Layer 2 has $_mvn rules, not 6 — the vertical-compression contract changed size without anyone saying so"
fi

# --- second-opinion: the reporting rules ----------------------------------
group "voice — second-opinion reporting rules"
has "$_SO" 'Never state an outcome for a claim.' \
  "second-opinion forbids outcomes before results return" \
  "second-opinion lost the no-outcome-before-return rule — the dispatched-but-empty middle state is unguarded again"
has "$_SO" 'not merely counted' \
  "cut claims must be named, not just counted" \
  "second-opinion no longer requires naming cut claims — a claim can vanish from a verdict as an anonymous integer"
has "$_SO" 'The delta is mandatory.' \
  "the validation delta is required even when nothing changed" \
  "second-opinion lost the mandatory delta — a run that changed nothing can now report nothing"
has "$_SO" 'Never inflate confidence.' \
  "sourceless concurrence cannot reach verified" \
  "second-opinion lost the no-inflation rule — advisors agreeing with no source can now be reported as verified"
# Four merge groups, counted. Adding a fifth (or dropping Cut) changes the
# output contract that the precedence order Cut > Conflict > Flagged > Verified
# is defined over, and would leave that order referring to groups that moved.
_son=$(sed -n '/^## Step 5 — Merge/,/^## Output format/p' "$_SO" 2>/dev/null | grep -cE '^- (✅|⚠️|❗|\*\*Cut\*\*)')
if [ "$_son" = "4" ]; then
  ok "the merge step still has exactly 4 groups"
else
  bad "the merge step has $_son groups, not 4 — the output contract changed under the precedence rule that orders them"
fi

# --- ai-writing-mistakes: the rules the catalogue table does not carry ------
group "voice — ai-writing-mistakes non-catalogue rules"
has "$_AW" 'would use domain terms plainly' \
  "the specialist test protects domain vocabulary" \
  "ai-writing-mistakes lost the specialist test — 'leverage' in a finance doc and 'delve' in a paper title become defects"
has "$_AW" 'Uniform rhythm.' \
  "uniform sentence and paragraph length is named as a tell" \
  "ai-writing-mistakes lost the uniform-rhythm tell — the one structural tell no word list can catch"
has "$_AW" 'A list is for parallel items' \
  "bulletized prose is named as a tell" \
  "ai-writing-mistakes lost the bulletization tell"

# --- the reference files carry rules too ----------------------------------
# Both references are loaded on demand and are where the detail lives. Neither
# was covered beyond a single grep, so either could have been emptied to a stub.
group "voice — reference files still carry their content"
has "$_REF" '## Block language' \
  "lexical-patterns keeps the block-language pattern" \
  "lexical-patterns lost a named pattern that machine-voice sends the reader to find"
has "$_REF" '## Headlinese' \
  "lexical-patterns keeps headlinese" \
  "lexical-patterns lost headlinese"
has "$_REF" '## Asyndeton' \
  "lexical-patterns keeps asyndeton" \
  "lexical-patterns lost asyndeton"
has "$_REF" '## Nominal style' \
  "lexical-patterns keeps nominal style" \
  "lexical-patterns lost nominal style"
has "$_MV" 'Four named patterns' \
  "machine-voice still promises four named patterns" \
  "machine-voice no longer names the count its reference file must supply"
has "$_AWREF" 'Invented specificity' \
  "tells.md keeps the invented-specificity tell (the accuracy-costing one)" \
  "tells.md lost invented specificity — the tell that costs the reader accuracy rather than attention"
has "$_AWREF" 'The confident summary of unread material' \
  "tells.md keeps the unread-material tell" \
  "tells.md lost the confident-summary-of-unread-material tell"

# --- AGENTS.md is the cross-harness entry point, not decoration ------------
group "voice — plugin AGENTS.md carries the contract"
has "$_AG" 'per output element, not per response' \
  "AGENTS.md states the element-level routing rule" \
  "AGENTS.md lost the routing rule — the cross-harness entry point no longer describes the partition"
has "$_AG" 'sits outside that routing decision entirely' \
  "AGENTS.md states the wording pass claims no element" \
  "AGENTS.md no longer says the wording pass claims no element"
has "$_AG" 'NEVER report work you did not' \
  "AGENTS.md carries the no-counterfeit clause" \
  "AGENTS.md lost the no-counterfeit clause that binds second-opinion and ai-writing-mistakes together"


# ══ THE GUARD: every rule must have a test ════════════════════════════════
# The sections above are a snapshot. This is the ratchet.
#
# rule-coverage.py extracts every normative rule unit from every SKILL.md and
# fails if any of them has no assertion in THIS file. It reads the assertions
# out of checks.sh directly, so there is no manifest to fall out of date.
#
# Consequence, and the point: adding a rule to a skill without adding a check
# for it turns the cheap tier red. A rule nobody tests is a rule that can be
# silently deleted, which is the exact regression class this whole pack exists
# to catch.
group "voice — every rule in every skill has an assertion"
_cov="$(python3 "$PLUGIN_DIR/evals/cheap/rule-coverage.py" "$PLUGIN_DIR/evals/cheap/checks.sh" "$_HV" "$_MV" "$_SO" "$_AW" 2>&1)"
_covrc=$?
_covtot=$(printf '%s\n' "$_cov" | awk -F'\t' '/^TOTAL/{print $2}')
if [ "$_covrc" = "0" ]; then
  ok "all $_covtot normative rule units across the four skills are asserted"
else
  printf '%s\n' "$_cov" | awk -F'\t' '/^UNENFORCED/{print "      " $2 "  " $3}'
  bad "$(printf '%s\n' "$_cov" | awk -F'\t' '/^TOTAL/{print $4}') rule unit(s) have no assertion in checks.sh — add a check, or the rule can be deleted without the suite noticing"
fi

unset _HV _MV _SO _AW _AWREF _REF _AG _HOOK _HANDLER _PROMPT _CFG _n _awn _mvn _son _cov _covrc _covtot _s _f
