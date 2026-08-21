# Cheap eval pack for the 'fleet-playbook-curator' plugin — SOURCED by evals/cheap/run.sh
# with cwd = repo root; inherits ok/bad/group and $PLUGIN_NAME / $PLUGIN_DIR.
#
# What the cheap tier defends is this plugin's invariant: the fleet-playbook is a
# curated INDEX, never the source of truth — facts auto-commit, interpretation is
# PR-only, every claim is citable. Each check below turns a silent regression of
# that invariant (soften the banner, flip source-of-truth, let curate push to main,
# drop the sha requirement, make the diff nondeterministic) into a red build.

SK="$PLUGIN_DIR/skills/fleet-playbook-curator"
PB="$SK/templates/fleet-playbook"
SYNC="$SK/templates/fleet-sync.yml"
FX="$PLUGIN_DIR/evals/cheap/fixtures"
# has/hasE/lacksE are provided by evals/cheap/run.sh (shared, single definition).

# --- structure: the advertised surface exists ------------------------------
group "fleet-playbook-curator — structure"
for f in \
  "$PLUGIN_DIR/.claude-plugin/plugin.json" \
  "$SK/SKILL.md" "$SK/PROMPT.md" \
  "$SK/scripts/list-fleet-members.sh" "$SK/scripts/diff-fleet.sh" \
  "$SK/scripts/gather-context.sh" "$SK/scripts/scaffold-repo.sh" "$SK/scripts/validate-citations.sh" \
  "$SYNC" "$SK/templates/fleet.example.yaml" \
  "$PB/SKILL.md" "$PB/index.schema.json" "$PB/index.seed.json" "$PB/CHANGELOG.md" \
  "$PLUGIN_DIR/agents/fleet-playbook-curator.md" \
  "$PLUGIN_DIR/commands/deploy-fleet-playbook.md" \
  "$PLUGIN_DIR/commands/curate-fleet-playbook.md" \
  "$PLUGIN_DIR/docs/DESIGN.md"; do
  if [ -f "$f" ]; then ok "present: ${f#$PLUGIN_DIR/}"; else bad "MISSING: ${f#$PLUGIN_DIR/}"; fi
done

# --- invariant: the playbook template declares itself non-authoritative -----
group "fleet-playbook-curator — non-authoritative by construction"
has "$PB/SKILL.md" 'source-of-truth: false' \
  "playbook template carries source-of-truth: false frontmatter" \
  "playbook template lost the source-of-truth: false key — it can now read as authoritative"
has "$PB/SKILL.md" 'NOT the source of truth' \
  "playbook template keeps the non-authoritative banner" \
  "playbook template banner ('NOT the source of truth') was removed/softened"
lacksE "$PB/SKILL.md" 'source-of-truth:[[:space:]]*true' \
  "playbook template never sets source-of-truth: true" \
  "playbook template sets source-of-truth: true — breaks the invariant"

# --- invariant: every claim must cite a real sha ---------------------------
group "fleet-playbook-curator — citation ledger requires a real sha"
hasE "$PB/index.schema.json" '"required":[[:space:]]*\[[^]]*"repo"[^]]*"path"[^]]*"sha"[^]]*"curated_at"' \
  "index schema requires repo+path+sha+curated_at on every claim" \
  "index schema no longer requires the full repo/path/sha/curated_at citation tuple"
hasE "$PB/index.schema.json" '\[0-9a-f\]\{7,40\}' \
  "index schema pins sha to a real hex commit (no placeholders)" \
  "index schema dropped the hex-sha pattern — placeholder shas would validate"

# --- invariant: facts auto-commit, interpretation is PR-only ----------------
group "fleet-playbook-curator — detect(no-LLM) / curate(PR-only) split"
detect_block="$(awk '/^  detect:/{f=1} /^  curate:/{f=0} f' "$SYNC")"
curate_block="$(awk '/^  curate:/{f=1} f' "$SYNC")"
if printf '%s' "$detect_block" | grep -q 'ANTHROPIC_API_KEY'; then
  bad "detect job references ANTHROPIC_API_KEY — the detector must be LLM-free"
else ok "detect job is LLM-free (no LLM credential)"; fi
if printf '%s' "$detect_block" | grep -qE 'push +origin +HEAD:main'; then
  ok "detect job auto-commits facts to main"
else bad "detect job no longer pushes the facts manifest to main"; fi
if printf '%s' "$curate_block" | grep -q 'gh pr create'; then
  ok "curate job lands changes via a PR"
else bad "curate job does not open a PR (gh pr create missing) — interpretation could reach main unreviewed"; fi
if printf '%s' "$curate_block" | grep -qE 'push +origin +HEAD:main|push +[^ ]*:main\b'; then
  bad "curate job pushes to main — interpretation must be PR-only"
else ok "curate job never pushes to main (PR-only)"; fi

# --- determinism: the diff is a pure function -------------------------------
group "fleet-playbook-curator — deterministic diff"
if command -v jq >/dev/null 2>&1; then
  d1="$(bash "$SK/scripts/diff-fleet.sh" "$FX/old-manifest.json" "$FX/new-manifest.json" 2>/dev/null)"
  d2="$(bash "$SK/scripts/diff-fleet.sh" "$FX/old-manifest.json" "$FX/new-manifest.json" 2>/dev/null)"
  if [ -n "$d1" ] && [ "$d1" = "$d2" ]; then ok "diff-fleet.sh is byte-deterministic on the fixture"
  else bad "diff-fleet.sh produced differing/empty output across runs (nondeterministic)"; fi
  if printf '%s' "$d1" | jq -e '.changed==true and (.added|length)==1 and (.removed|length)==1 and (.renamed|length)==1 and (.updated|length)==1' >/dev/null 2>&1; then
    ok "diff-fleet.sh classifies add/remove/rename(by node_id)/update correctly"
  else bad "diff-fleet.sh misclassified the fixture (expected 1 each of add/remove/rename/update)"; fi
else
  ok "jq unavailable — skipping determinism exec check (structural checks still enforced)"
fi

# --- invariant: citations must be TRACEABLE, not just present --------------
# Closes the "cited-but-fabricated" hole the ansible-homelab-sim simulation found:
# a claim can carry a sha + path yet name a file never read this pass (worst case,
# a removed member). The validator + these fixtures make that a red build.
group "fleet-playbook-curator — citation traceability guard"
VC="$SK/scripts/validate-citations.sh"
if bash "$VC" "$FX/cite-index-good.json" "$FX/cite-diff.json" "$FX/cite-context.json" >/dev/null 2>&1; then
  ok "validate-citations accepts a fully-traceable ledger"
else bad "validate-citations rejected a valid ledger (false positive)"; fi
if bash "$VC" "$FX/cite-index-bad.json" "$FX/cite-diff.json" "$FX/cite-context.json" >/dev/null 2>&1; then
  bad "validate-citations ACCEPTED a fabricated removed-member file citation — the guard is broken"
else ok "validate-citations rejects a fabricated removed-member file citation (the sim's defect)"; fi
# Provenance strengthening: repo-was-read is necessary but not sufficient — the cited
# PATH must be in that repo's gathered tree (the first-curation verifier caught claims
# citing files whose contents were never in context).
if bash "$VC" "$FX/cite-index-badpath.json" "$FX/cite-diff.json" "$FX/cite-context.json" >/dev/null 2>&1; then
  bad "validate-citations ACCEPTED a citation to a path NOT in the gathered tree — provenance guard too weak"
else ok "validate-citations rejects a file citation whose path is absent from the gathered tree"; fi

# --- scripts parse + JSON is valid -----------------------------------------
group "fleet-playbook-curator — scripts parse, JSON valid"
for s in "$SK"/scripts/*.sh; do
  if bash -n "$s" 2>/dev/null; then ok "bash -n ok: ${s#$PLUGIN_DIR/}"; else bad "bash -n FAILED: ${s#$PLUGIN_DIR/}"; fi
done
for j in "$PB/index.schema.json" "$PB/index.seed.json" "$FX/old-manifest.json" "$FX/new-manifest.json"; do
  if python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$j" 2>/dev/null; then ok "valid JSON: ${j#$PLUGIN_DIR/}"; else bad "INVALID JSON: ${j#$PLUGIN_DIR/}"; fi
done

# --- portability: the agent seam is swappable ------------------------------
group "fleet-playbook-curator — cross-harness seam"
has "$SYNC" 'AGENT_CMD' \
  "curate workflow exposes a swappable AGENT_CMD (not hard-wired to one harness)" \
  "curate workflow hard-wires the agent invocation — lost the cross-harness seam"

# --- honest signals: this plugin must not lie about its own liveness -------
# Every check below defends a hole found by reading the shipped code, where the
# pipeline could report success while doing nothing observable. A tool whose
# entire premise is "never assert what you didn't verify" is the last place a
# silent-green path belongs.
group "fleet-playbook-curator — no silent-green paths"

# Asserted as a POSITIVE, deliberately. The obvious form here is a negative grep
# for the old swallow-the-no-op line — but this file's own comments quote that
# line to explain why it was removed, so the negative matched the documentation
# and went red on a correct tree. A negative grep breaks the moment you document
# what you deleted; assert the fix is present instead.
has "$SYNC" 'curation ran, no playbook delta' \
  "a zero-delta curation writes a changelog line rather than being silently swallowed" \
  "REGRESSION: a no-op curation leaves no changelog trace — an agent that did nothing is again indistinguishable from an agent that never ran"

has "$SYNC" '::notice::Curation ran and produced NO playbook change' \
  "a no-op curation emits a visible annotation naming the repos that changed" \
  "no-op curation is silent again — restore the ::notice:: attribution"

# Anchored to the actual gh query, not the step name or the comment above it:
# a first pass grepped for "Backpressure", which also appears in the explanatory
# comment, so renaming the step still passed. Mutation testing caught it. Match
# something only the executable path can contain.
has "$SYNC" 'head:curate/' \
  "detect reports unmerged curation PRs (playbook prose can rot behind a queue while facts stay current)" \
  "lost the unmerged-PR backpressure check — the playbook can go stale behind open PRs with every run green"

has "$SYNC" 'LAST_VERIFIED' \
  "last-verified is a separate clock from last-curated (freshness banner was wrong in BOTH directions when collapsed into one)" \
  "LAST_VERIFIED stamp gone — the freshness banner reverts to being wrong in both directions"

has "$SYNC" '::error::detect could not push facts to main' \
  "a failed facts push to main fails loudly (it is a load-bearing assumption, not incidental)" \
  "detect's push failure is silent again — branch protection on main would break this daily with no clear signal"

# --- portability: owner may be an org OR a user ----------------------------
group "fleet-playbook-curator — owner resolution"
has "$SK/scripts/list-fleet-members.sh" 'users/${owner}/repos' \
  "enumeration falls back to users/<owner>/repos (orgs/ alone 404s for personal accounts)" \
  "org-only enumeration is back — any user-owned fleet silently fails to enumerate"

has "$SK/scripts/list-fleet-members.sh" 'Refusing to emit an empty fleet' \
  "a glob matching zero repos fails loudly instead of emitting an empty manifest forever" \
  "an empty fleet is emitted silently again — it looks identical to a stable fleet on every later run"

# --- the README must not assert a false status ------------------------------
group "fleet-playbook-curator — status honesty"
# Positive assertion for the same reason as above: the README now openly records
# that it once carried a false status line, so a negative grep for that phrase
# would match the confession and fail a correct tree.
has "$PLUGIN_DIR/README.md" 'Implemented and green across all three eval tiers' \
  "README states the plugin's true, current eval status" \
  "README no longer states its real status — it previously claimed an 'intentionally RED' eval long after the evals passed, which is exactly the kind of uncited assertion this plugin exists to refuse"
