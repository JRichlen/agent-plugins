# Cheap eval pack for the 'docs-hygiene' plugin — SOURCED by evals/cheap/run.sh
# with cwd = repo root; inherits ok/bad/group/has/hasE/lacksE and
# $PLUGIN_NAME / $PLUGIN_DIR.
#
# What this defends: docs-hygiene's invariant has two halves — (1) a stale
# claim is never left in place, corrected or explicitly flagged in the same
# pass, and (2) a contradiction between layered instruction files always
# resolves to ONE explicit kept version, never left standing for both to
# survive. Grepping the plugin's own prose can only prove the PROCEDURE is
# documented — it can't prove the procedure actually discriminates a stale
# claim from a current one. So this pack also runs a real, deterministic
# implementation of the path-tier of the heuristic (scripts/check-path-claim.sh)
# against fixture instruction-file snippets and asserts its actual output,
# not just that the words describing it exist somewhere.

SKILL="$PLUGIN_DIR/skills/docs-hygiene/SKILL.md"
REF="$PLUGIN_DIR/skills/docs-hygiene/references/refactoring-workflow.md"
AGENTS="$PLUGIN_DIR/AGENTS.md"
README="$PLUGIN_DIR/README.md"
COMMAND="$PLUGIN_DIR/commands/docs-hygiene.md"
CHECKER="$PLUGIN_DIR/evals/cheap/scripts/check-path-claim.sh"
FX="$PLUGIN_DIR/evals/cheap/fixtures"

# --- structure: the plugin's advertised surface actually exists ------------
group "docs-hygiene — structure"
for f in \
  "$PLUGIN_DIR/.claude-plugin/plugin.json" \
  "$SKILL" \
  "$REF" \
  "$AGENTS" \
  "$README" \
  "$COMMAND" \
  "$CHECKER" \
  "$FX/root-claim.md" \
  "$FX/nested-claim.md" \
  "$FX/stale-claim.md" \
  "$FX/current-claim.md" \
  "$FX/repo-tree/skills/plugin-foo/scripts/deploy.sh"; do
  if [ -f "$f" ]; then ok "present: ${f#$PLUGIN_DIR/}"; else bad "MISSING: ${f#$PLUGIN_DIR/}"; fi
done

# --- invariant text carried verbatim in both SKILL.md and AGENTS.md --------
group "docs-hygiene — invariant text present verbatim"
INVARIANT_MARKER='never leaves the contradiction standing for the next reader'
if grep -qF "$INVARIANT_MARKER" "$SKILL"; then
  ok "SKILL.md carries the contradiction-resolution invariant verbatim"
else
  bad "SKILL.md is missing the contradiction-resolution invariant text"
fi
if grep -qF "$INVARIANT_MARKER" "$AGENTS"; then
  ok "AGENTS.md carries the contradiction-resolution invariant verbatim"
else
  bad "AGENTS.md is missing the contradiction-resolution invariant text"
fi

# --- BEHAVIORAL: real path-tier resolution, not just documented -----------
# This is the load-bearing part of the pack. It runs the deterministic
# checker against fixtures and asserts its ACTUAL output, so a regression
# that breaks the underlying discrimination (e.g. the script always reports
# CURRENT, or always reports STALE, regardless of input) goes red even
# though every word of prose describing the procedure is still intact.
group "docs-hygiene — path-tier staleness check discriminates for real"

if [ ! -x "$CHECKER" ]; then
  bad "check-path-claim.sh is missing or not executable at $CHECKER"
else
  ok "check-path-claim.sh is present and executable"

  # Negative control first: a claim naming a path that DOES exist must be
  # reported CURRENT with exit 0. If this fails, the checker is broken in a
  # way that would make every other assertion below meaningless (a script
  # that always says STALE would still pass the stale-claim check below).
  out="$("$CHECKER" "$FX/current-claim.md" "$FX/repo-tree" 2>&1)"; rc=$?
  if [ "$rc" -eq 0 ] && printf '%s' "$out" | grep -q '^CURRENT:'; then
    ok "negative control: a claim naming an existing path is reported CURRENT (exit 0)"
  else
    bad "negative control FAILED: current-claim.md was not reported CURRENT (got rc=$rc, out='$out') — checker cannot be trusted"
  fi

  # A single stale claim (invariant half 1: never left in place / silently
  # repeated) must be reported STALE with a nonzero exit.
  out="$("$CHECKER" "$FX/stale-claim.md" "$FX/repo-tree" 2>&1)"; rc=$?
  if [ "$rc" -ne 0 ] && printf '%s' "$out" | grep -q '^STALE:'; then
    ok "a claim naming a nonexistent path is detected STALE (nonzero exit), never silently accepted"
  else
    bad "stale-claim.md was NOT detected as stale (got rc=$rc, out='$out') — a stale claim would be silently propagated"
  fi

  # The contradiction pair (invariant half 2: resolves to ONE explicit kept
  # version). root-claim.md and nested-claim.md assert the same fact
  # (where the deploy script lives) with two different paths. Exactly one
  # of the two must resolve CURRENT and the other STALE — if both were
  # CURRENT the fixture wouldn't be a real contradiction, and if both were
  # STALE there'd be nothing to keep.
  root_out="$("$CHECKER" "$FX/root-claim.md" "$FX/repo-tree" 2>&1)"; root_rc=$?
  nested_out="$("$CHECKER" "$FX/nested-claim.md" "$FX/repo-tree" 2>&1)"; nested_rc=$?
  if [ "$root_rc" -ne 0 ] && [ "$nested_rc" -eq 0 ]; then
    ok "contradiction pair resolves to exactly ONE kept version: nested-claim.md is CURRENT, root-claim.md is STALE"
  else
    bad "contradiction pair did NOT resolve to one kept version (root rc=$root_rc: '$root_out'; nested rc=$nested_rc: '$nested_out')"
  fi
fi

# --- prose: staleness heuristic's drift-risk tiers are all named -----------
group "docs-hygiene — staleness heuristic tiers named"
for tier in "**Paths**" "**Commands**" "**Behavior/architecture claims**" "**Domain-concept/vocabulary claims**"; do
  if grep -qF "$tier" "$SKILL"; then
    ok "SKILL.md names heuristic tier: $tier"
  else
    bad "SKILL.md is missing heuristic tier: $tier"
  fi
done

# --- prose: unambiguous vs ambiguous fix are both named and distinct -------
group "docs-hygiene — unambiguous vs ambiguous fix distinguished"
if grep -qF '**Unambiguous fix**' "$SKILL"; then
  ok "SKILL.md names the unambiguous-fix case"
else
  bad "SKILL.md is missing the unambiguous-fix case"
fi
if grep -qF '**Ambiguous fix**' "$SKILL"; then
  ok "SKILL.md names the ambiguous-fix case"
else
  bad "SKILL.md is missing the ambiguous-fix case"
fi
if grep -qiE 'do not guess' "$SKILL"; then
  ok "SKILL.md states that an ambiguous fix must not be guessed"
else
  bad "SKILL.md does not state that an ambiguous fix must not be guessed"
fi

# --- progressive disclosure: reference file exists AND is referenced -------
group "docs-hygiene — progressive disclosure wired"
if [ -f "$REF" ]; then
  ok "references/refactoring-workflow.md exists"
else
  bad "references/refactoring-workflow.md is missing"
fi
if grep -qF 'references/refactoring-workflow.md' "$SKILL"; then
  ok "SKILL.md references references/refactoring-workflow.md"
else
  bad "SKILL.md does not reference references/refactoring-workflow.md — progressive disclosure not wired"
fi
# The SKILL.md must also state the load-only-when-multi-file condition,
# so a reader doesn't load the heavier procedure for a single-file check.
if grep -qiE 'only when.{0,80}two or more instruction files' "$SKILL"; then
  ok "SKILL.md states the reference is loaded only for 2+ file contradictions"
else
  bad "SKILL.md does not scope reference-loading to the 2+ file contradiction case"
fi

# --- reference file: all seven refactoring steps present -------------------
group "docs-hygiene — refactoring-workflow.md carries all seven steps"
for step in \
  "Enumerate the full layered set" \
  "Find contradictions" \
  "do not silently pick one" \
  "Record one explicit kept version" \
  "Deduplicate ownership" \
  "Extract essentials" \
  "Flag-for-deletion pass"; do
  if grep -qF "$step" "$REF"; then
    ok "refactoring-workflow.md has step: $step"
  else
    bad "refactoring-workflow.md is missing step: $step"
  fi
done

# --- reference file: summary table names all four contradiction tiers ------
group "docs-hygiene — refactoring-workflow.md summary table complete"
if grep -qE '^\| Contradiction tier \| Deterministically checkable inline\? \| Resolution \|' "$REF"; then
  ok "refactoring-workflow.md summary table header is intact"
else
  bad "refactoring-workflow.md summary table header is missing or malformed"
fi
for tier_row in "Path (renamed/moved file)" "Command (script/CLI entry)" "Behavior/architecture claim" "Policy/branch-protection claim"; do
  if grep -qF "$tier_row" "$REF"; then
    ok "summary table has row: $tier_row"
  else
    bad "summary table is missing row: $tier_row"
  fi
done

# --- differentiation: boundary vs fleet-playbook-curator and plugin-factory
group "docs-hygiene — boundary vs fleet-playbook-curator and plugin-factory named"
if grep -qi 'fleet-playbook-curator' "$SKILL" && grep -qi 'source-of-truth: false' "$SKILL"; then
  ok "SKILL.md names fleet-playbook-curator and its source-of-truth: false posture"
else
  bad "SKILL.md does not clearly distinguish itself from fleet-playbook-curator"
fi
if grep -qi 'plugin-factory' "$SKILL"; then
  ok "SKILL.md names the plugin-factory boundary"
else
  bad "SKILL.md does not name the plugin-factory boundary"
fi

# --- worked, real, in-repo staleness examples are cited (not hypothetical) -
# The design brief is explicit: cite the marketplace's own stale README and
# fleet-playbook-curator's corrected "intentionally RED" claim as REAL,
# verifiable worked examples, not invented ones.
group "docs-hygiene — real in-repo worked examples cited"
if grep -qF 'graveyard' "$SKILL" && grep -qF 'tailscale-wif' "$SKILL"; then
  ok "SKILL.md cites the root README's stale 2-of-11 plugin table by name"
else
  bad "SKILL.md does not cite the root README's stale plugin table with the actual plugin names"
fi
if grep -qi 'fleet-playbook-curator' "$SKILL" && grep -qi 'intentionally RED' "$SKILL"; then
  ok "SKILL.md cites fleet-playbook-curator's corrected 'intentionally RED' claim"
else
  bad "SKILL.md does not cite fleet-playbook-curator's corrected 'intentionally RED' claim"
fi
# Cross-check these citations are actually still true of the repo right now —
# the plugin that teaches "don't cite stale claims" would be self-defeating
# if its own worked examples went stale. The root README table really does
# name only these two plugins (not all 11); assert that structurally.
ROOT_README="$REPO_ROOT/README.md"
if [ -f "$ROOT_README" ]; then
  plugin_count=$(python3 -c "import json; print(len(json.load(open('$REPO_ROOT/.claude-plugin/marketplace.json'))['plugins']))")
  install_lines=$(grep -c '/plugin install .*@jrichlen' "$ROOT_README")
  if [ "$install_lines" -lt "$plugin_count" ]; then
    ok "root README's install table ($install_lines entries) is still behind marketplace.json ($plugin_count plugins) — the worked example remains real and current"
  else
    bad "root README's install table now covers all $plugin_count plugins — the SKILL.md's worked example is STALE and must be updated or replaced (ironic, but the invariant applies to this plugin's own docs too)"
  fi
fi

# --- keywords / description byte-identical between plugin.json and --------
# marketplace.json — the exact drift class the task brief calls out as
# having happened once already (orchestrate) and gone unnoticed.
group "docs-hygiene — plugin.json and marketplace.json entry are byte-identical"
python3 - "$PLUGIN_DIR" "$REPO_ROOT" <<'PY'
import json, sys
plugin_dir, repo_root = sys.argv[1:3]
pj = json.load(open(f"{plugin_dir}/.claude-plugin/plugin.json"))
mkt = json.load(open(f"{repo_root}/.claude-plugin/marketplace.json"))
entry = next((p for p in mkt["plugins"] if p.get("name") == "docs-hygiene"), None)
if entry is None:
    print("  FAIL no marketplace.json entry named docs-hygiene")
    sys.exit(1)
fail = 0
if entry.get("description") != pj.get("description"):
    print("  FAIL description differs between plugin.json and marketplace.json"); fail = 1
else:
    print("  PASS description is byte-identical between plugin.json and marketplace.json")
if entry.get("keywords") != pj.get("keywords"):
    print("  FAIL keywords differ between plugin.json and marketplace.json"); fail = 1
else:
    print("  PASS keywords are byte-identical between plugin.json and marketplace.json")
if pj.get("version") != "0.0.1" and entry.get("version") == pj.get("version"):
    print(f"  PASS version matches and is bumped past scaffold default ({pj.get('version')})")
else:
    print(f"  FAIL version mismatch or still at scaffold default (plugin.json={pj.get('version')}, marketplace={entry.get('version')})"); fail = 1
sys.exit(fail)
PY
if [ $? -eq 0 ]; then ok "plugin.json and marketplace.json entry are fully in sync (description, keywords, version)"; else bad "plugin.json and marketplace.json entry have drifted — see FAIL lines above"; fi
