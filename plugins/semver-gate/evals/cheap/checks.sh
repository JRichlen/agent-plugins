# Cheap eval pack for the 'semver-gate' plugin — SOURCED by evals/cheap/run.sh with
# cwd = repo root; inherits ok/bad/group and $PLUGIN_NAME / $PLUGIN_DIR.
#
# This plugin ships only prose (a judgment lens, no scripts), so every check
# below greps for a load-bearing marker: a sentence that, if silently deleted
# or softened, would weaken the invariant while leaving a well-formed SKILL.md.
# That's exactly the regression class structural gates (frontmatter, JSON
# validity) cannot see. The three things being defended:
#   1. THE QUOTES ARE REAL — the MAJOR/MINOR/PATCH mapping is anchored to
#      verbatim semver.org and Conventional Commits language, not a loose
#      paraphrase. Losing an exact quote is losing the honesty of the mapping.
#   2. MAJOR ALWAYS DOMINATES — the tie-break rule that makes a simultaneously
#      additive-and-destructive action MAJOR, not MINOR.
#   3. LAYERING — this skill sits on top of the system-prompt reversibility
#      instruction and an autoMode classifier, and a hardcoded rule in either
#      always wins. Losing that framing turns this into a green-field policy
#      that could contradict pre-existing judgment infrastructure instead of
#      composing with it.

_SKILL="$PLUGIN_DIR/skills/semver-gate/SKILL.md"
_AG="$PLUGIN_DIR/AGENTS.md"
_CMD="$PLUGIN_DIR/commands/semver-gate.md"
_README="$PLUGIN_DIR/README.md"

# Every anchor below is a full sentence or clause quoted out of prose that gets
# hand-wrapped at ~80 columns, so a literal single-line grep is the wrong tool
# — it would go red on a harmless rewrap that changed nothing semantic. norm()
# collapses newlines/runs of whitespace to single spaces first, so a check
# only fails when the WORDS actually changed, not when a line broke differently.
# Matching is case-insensitive for the same reason: "NEVER" vs "never" is a
# copyediting choice, not the thing being defended.
norm() { tr '\n' ' ' < "$1" 2>/dev/null | tr -s ' '; }
# has FILE FIXED OK-MSG FAIL-MSG   — fixed-string grep, whitespace-normalized
has()  { if norm "$1" | grep -qiF "$2"; then ok "$3"; else bad "$4"; fi; }
# hasE FILE REGEX OK-MSG FAIL-MSG  — extended-regex grep, whitespace-normalized
hasE() { if norm "$1" | grep -qiE "$2"; then ok "$3"; else bad "$4"; fi; }
# lacksE FILE REGEX OK-MSG FAIL-MSG — must NOT match (negative check)
lacksE(){ if norm "$1" | grep -qiE "$2"; then bad "$4"; else ok "$3"; fi; }

# --- structure: the advertised surface exists -------------------------------
group "semver-gate — structure"
for _f in \
  "$PLUGIN_DIR/.claude-plugin/plugin.json" \
  "$_SKILL" "$_AG" "$_CMD" "$_README"; do
  if [ -f "$_f" ]; then ok "present: $_f"; else bad "MISSING: $_f"; fi
done

# --- clause 1: the semver.org quotes are verbatim, not paraphrased ---------
group "semver-gate — semver.org quotes are exact"
has "$_SKILL" 'MAJOR version when you make incompatible API changes' \
  "SKILL.md keeps semver.org's exact MAJOR summary wording" \
  "SKILL.md lost semver.org's exact MAJOR wording — the mapping is no longer anchored to the real spec"
has "$_SKILL" 'MINOR version when you add functionality in a backward compatible manner' \
  "SKILL.md keeps semver.org's exact MINOR summary wording" \
  "SKILL.md lost semver.org's exact MINOR wording"
has "$_SKILL" 'PATCH version when you make backward compatible bug fixes' \
  "SKILL.md keeps semver.org's exact PATCH summary wording" \
  "SKILL.md lost semver.org's exact PATCH wording"
has "$_SKILL" 'MUST be incremented if any backward incompatible changes are introduced to the public API' \
  "SKILL.md keeps semver.org's normative MAJOR rule verbatim" \
  "SKILL.md lost the normative MAJOR rule — the MAJOR bar is no longer traceable to the real spec"
has "$_SKILL" 'A bug fix is defined as an internal change that fixes incorrect behavior' \
  "SKILL.md keeps semver.org's bug-fix definition verbatim" \
  "SKILL.md lost the bug-fix definition — the PATCH bar is no longer traceable to the real spec"

# --- clause 1: the Conventional Commits quotes are verbatim -----------------
group "semver-gate — Conventional Commits quotes are exact"
has "$_SKILL" 'this correlates with `PATCH` in Semantic Versioning' \
  "SKILL.md keeps the exact fix->PATCH correlation" \
  "SKILL.md lost the exact fix->PATCH correlation from the Conventional Commits spec"
has "$_SKILL" 'this correlates with `MINOR` in Semantic Versioning' \
  "SKILL.md keeps the exact feat->MINOR correlation" \
  "SKILL.md lost the exact feat->MINOR correlation from the Conventional Commits spec"
has "$_SKILL" 'correlating with `MAJOR` in Semantic Versioning' \
  "SKILL.md keeps the exact BREAKING CHANGE->MAJOR correlation" \
  "SKILL.md lost the exact BREAKING CHANGE->MAJOR correlation from the Conventional Commits spec"
has "$_SKILL" 'A BREAKING CHANGE can be part of commits of any type' \
  "SKILL.md keeps the exact clause that breaking changes override the type" \
  "SKILL.md lost the clause that a BREAKING CHANGE overrides its carrying type — the source of the MAJOR-dominates rule"

# --- clause 2: MAJOR always dominates (the tie-break) -----------------------
group "semver-gate — MAJOR always dominates"
hasE "$_SKILL" 'MAJOR always dominates|MAJOR overrides' \
  "SKILL.md states the MAJOR-dominates tie-break rule" \
  "SKILL.md lost the MAJOR-dominates tie-break rule — a simultaneously additive-and-destructive action would no longer default to the safer classification"
has "$_SKILL" 'never taken on an assumption' \
  "SKILL.md states a MAJOR action is never taken on an assumption" \
  "SKILL.md lost 'never taken on an assumption' — the core invariant statement"
hasE "$_SKILL" 'even under time pressure' \
  "SKILL.md states the MAJOR stop survives time pressure" \
  "SKILL.md lost the time-pressure clause — the exact failure mode the enforce_admins worked example defends against"
hasE "$_AG" 'never taken on an assumption' \
  "AGENTS.md restates the invariant" \
  "AGENTS.md no longer restates the core invariant"

# --- clause 3: layering — hardcoded rules and the system-prompt section win -
group "semver-gate — composes with, never overrides, existing judgment infra"
has "$_SKILL" '# Executing actions with care' \
  "SKILL.md quotes the real system-prompt section heading verbatim" \
  "SKILL.md lost the verbatim system-prompt heading — the grounding to real infrastructure is gone"
has "$_SKILL" 'Carefully consider the reversibility and blast radius of actions' \
  "SKILL.md quotes the system-prompt's reversibility/blast-radius sentence verbatim" \
  "SKILL.md lost the verbatim reversibility/blast-radius sentence"
hasE "$_SKILL" 'a hardcoded rule always wins|hardcoded rule.*wins' \
  "SKILL.md states a hardcoded rule always wins over this skill's reasoning" \
  "SKILL.md lost the rule that a hardcoded soft_deny/protected-branch/routine-allowlist verdict always wins — this skill could now contradict pre-existing policy instead of composing with it"
has "$_SKILL" 'db:push' \
  "SKILL.md grounds the mapping in the real dnd-campaign-companion soft_deny example" \
  "SKILL.md lost the real soft_deny worked example (pnpm db:push) — the mapping is no longer tied to a concrete, verifiable precedent"
has "$_SKILL" 'db:migrate:deploy' \
  "SKILL.md keeps the second real soft_deny example (db:migrate:deploy)" \
  "SKILL.md lost the db:migrate:deploy soft_deny example"

# --- clause 4: the enforce_admins calibration example survives intact ------
group "semver-gate — the enforce_admins worked example is intact"
has "$_SKILL" 'enforce_admins' \
  "SKILL.md keeps the enforce_admins worked example" \
  "SKILL.md lost the enforce_admins worked calibration example"
has "$_SKILL" 'least-destructive alternative' \
  "SKILL.md states a MAJOR stop must name the least-destructive alternative" \
  "SKILL.md lost the least-destructive-alternative requirement — a MAJOR stop could become a bare yes/no ask again"
hasE "$_SKILL" "doesn't auto-authorize the mechanism|imperative doesn't auto-authorize" \
  "SKILL.md states a user's imperative doesn't auto-authorize the underlying mechanism" \
  "SKILL.md lost the rule that a direct request ('merge it') doesn't auto-authorize a MAJOR-class mechanism to reach it"

# --- clause 5: the mapping table has all three tiers with real behavior ----
group "semver-gate — the three-tier mapping is complete"
hasE "$_SKILL" '\*\*PATCH\*\*.*Act\.' \
  "mapping table's PATCH row says Act (silent)" \
  "mapping table's PATCH row is missing or no longer says Act"
hasE "$_SKILL" '\*\*MINOR\*\*.*Act\*\*, but flag' \
  "mapping table's MINOR row says Act, but flag prominently" \
  "mapping table's MINOR row no longer says act-but-flag — MINOR could collapse into PATCH (silent) or MAJOR (blocking)"
hasE "$_SKILL" '\*\*MAJOR\*\*.*Stop\.' \
  "mapping table's MAJOR row says Stop" \
  "mapping table's MAJOR row is missing or no longer says Stop"

# --- no dangling references to files this plugin doesn't ship --------------
# A skill that name-drops a references/ file it never wrote would break the
# repo-wide AGENTS.md path-resolution gate (root cheap tier, section 7) and
# leave a reader chasing a file that doesn't exist. Assert the negative
# directly here too, so this pack fails loudly and specifically instead of
# only failing far away in the generic root gate.
group "semver-gate — no dangling references/ path"
for _f in "$_SKILL" "$_AG" "$_CMD" "$_README"; do
  lacksE "$_f" 'references/' \
    "$_f names no references/ file (this plugin ships none)" \
    "$_f references a references/ path, but plugins/semver-gate/skills/semver-gate/references/ does not exist — dangling link"
done

unset _SKILL _AG _CMD _README _f
