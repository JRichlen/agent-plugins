#!/usr/bin/env bash
#
# Cheap evals — deterministic, offline, no API cost. Runs in well under a second.
#
# This is the tier that must pass on EVERY change before commit (see AGENTS.md).
# It proves the structural + safety invariants that don't need an LLM to check:
# a bad edit to a delete-script generator that dropped a bundle guard, a
# malformed manifest, an unparseable script, or a marketplace source pointing at
# a plugin that isn't there would all be caught here for free.
#
# STRUCTURE: sections 1-9 are GENERIC — they auto-discover every plugin's files
# and hold for any plugin added to this marketplace (syntax, JSON, marketplace
# wiring both directions, frontmatter, no unfilled placeholders, real AGENTS.md
# paths, no red-by-default sentinel shipped, and portability). The plugin-SPECIFIC
# safety checks live with each plugin, in plugins/<name>/evals/cheap/checks.sh,
# and are sourced here per plugin enumerated from marketplace.json (section 10).
# Discovery FAILS CLOSED: a plugin registered in the marketplace with no cheap
# eval pack is a failure, not a silent skip — otherwise a new plugin could ship
# with zero safety coverage and still show green.
#
# Exit 0 = all checks pass. Exit 1 = at least one failed.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

pass=0; fail=0
ok()   { printf '  \033[32mPASS\033[0m %s\n' "$1"; pass=$((pass+1)); }
bad()  { printf '  \033[31mFAIL\033[0m %s\n' "$1"; fail=$((fail+1)); }
group(){ printf '\n\033[1m%s\033[0m\n' "$1"; }
# Shared marker helpers for per-plugin packs — a SINGLE definition here, inherited
# by every sourced checks.sh, so the byte-identical per-plugin copies can't drift
# apart. has FILE FIXED OK FAIL | hasE FILE REGEX OK FAIL | lacksE FILE REGEX OK FAIL.
has()   { if grep -qF "$2" "$1" 2>/dev/null; then ok "$3"; else bad "$4"; fi; }
hasE()  { if grep -qE "$2" "$1" 2>/dev/null; then ok "$3"; else bad "$4"; fi; }
lacksE(){ if grep -qE "$2" "$1" 2>/dev/null; then bad "$4"; else ok "$3"; fi; }

# --- 1. Shell scripts parse -------------------------------------------------
group "shell syntax (bash -n)"
while IFS= read -r s; do
  if bash -n "$s" 2>/dev/null; then ok "$s"; else bad "$s (syntax error)"; fi
done < <(find plugins evals -name '*.sh' -type f | sort)

# --- 2. JSON manifests are valid -------------------------------------------
group "json validity"
while IFS= read -r j; do
  if python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$j" 2>/dev/null; then
    ok "$j"; else bad "$j (invalid JSON)"; fi
done < <(find . -name '*.json' -not -path './node_modules/*' -type f | sort)

# --- 3. Marketplace <-> plugin wiring --------------------------------------
group "marketplace wiring"
python3 - "$REPO_ROOT" <<'PY'
import json, os, sys
root = sys.argv[1]
mkt = json.load(open(os.path.join(root, ".claude-plugin", "marketplace.json")))
fail = 0
for p in mkt.get("plugins", []):
    src = p.get("source", "")
    manifest = os.path.join(root, src, ".claude-plugin", "plugin.json")
    if os.path.isfile(manifest):
        pj = json.load(open(manifest))
        if pj.get("name") == p.get("name"):
            print(f"  PASS source {src} -> plugin.json name matches ('{p['name']}')")
        else:
            print(f"  FAIL source {src} plugin.json name '{pj.get('name')}' != marketplace '{p.get('name')}'"); fail += 1
    else:
        print(f"  FAIL source {src} has no .claude-plugin/plugin.json"); fail += 1
sys.exit(1 if fail else 0)
PY
if [ $? -eq 0 ]; then pass=$((pass+1)); else fail=$((fail+1)); fi

# --- 3a. description/keywords stay byte-identical between plugin.json and ---
# the marketplace.json entry. Anthropic's own official marketplace proves
# marketplace.json's `description` is what the marketplace browser actually
# shows (every entry there carries one, sometimes deliberately DIFFERENT from
# the plugin's own plugin.json description as separate marketing copy) — so
# dropping the field here would degrade discoverability. This repo instead
# keeps a single voice: the two must read exactly the same, checked here so
# they can never quietly drift apart again (as 'orchestrate' and 'graveyard'
# both already had, unnoticed, before this check existed).
group "plugin.json <-> marketplace.json description/keywords parity"
python3 - "$REPO_ROOT" <<'PY'
import json, os, sys
root = sys.argv[1]
mkt = json.load(open(os.path.join(root, ".claude-plugin", "marketplace.json")))
fail = 0
for p in mkt.get("plugins", []):
    name = p.get("name", "")
    src = (p.get("source", "") or "").lstrip("./")
    manifest = os.path.join(root, src, ".claude-plugin", "plugin.json")
    if not os.path.isfile(manifest):
        continue  # already reported as a failure by section 3
    pj = json.load(open(manifest))
    ok = True
    if pj.get("description") != p.get("description"):
        print(f"  FAIL {name}: description differs between plugin.json and marketplace.json entry")
        ok = False
    if pj.get("keywords") != p.get("keywords"):
        print(f"  FAIL {name}: keywords differ between plugin.json and marketplace.json entry")
        print(f"    plugin.json:      {pj.get('keywords')}")
        print(f"    marketplace.json: {p.get('keywords')}")
        ok = False
    if ok:
        print(f"  PASS {name}: description and keywords identical in both manifests")
    else:
        fail += 1
sys.exit(1 if fail else 0)
PY
if [ $? -eq 0 ]; then pass=$((pass+1)); else fail=$((fail+1)); fi

# --- 4. SKILL.md frontmatter -----------------------------------------------
group "skill frontmatter"
while IFS= read -r skill; do
  python3 - "$skill" <<'PY'
import sys
p = sys.argv[1]
txt = open(p).read()
if not txt.startswith("---"):
    print(f"  FAIL {p} (no frontmatter)"); sys.exit(1)
fm = txt.split("---", 2)[1]
missing = [k for k in ("name:", "description:") if k not in fm]
if missing:
    print(f"  FAIL {p} (missing {', '.join(missing)})"); sys.exit(1)
print(f"  PASS {p}")
PY
  if [ $? -eq 0 ]; then pass=$((pass+1)); else fail=$((fail+1)); fi
done < <(find plugins -name 'SKILL.md' -type f | sort)

# --- 4b. commands/*.md frontmatter must be PARSEABLE YAML -------------------
# Section 4 above checks SKILL.md frontmatter for required KEYS, but nothing
# checked that any frontmatter actually parses. That gap shipped two real bugs
# to main: semver-gate's command carried an unquoted colon inside its
# description, and fleet-playbook-curator's argument-hint began with '[', which
# YAML reads as a flow sequence and then chokes on the trailing prose. Both
# passed every tier of this suite and were only caught when `apm install`
# refused to deploy the command files ("malformed or over-budget YAML
# frontmatter") — i.e. the break surfaced in a downstream consumer, not here,
# which is the exact shape of failure this suite exists to prevent.
#
# Key-presence is not parseability. Assert the parse itself.
group "command frontmatter parses as YAML"
while IFS= read -r cmd; do
  python3 - "$cmd" <<'PY'
import sys
try:
    import yaml
except ImportError:
    print(f"  SKIP {sys.argv[1]} (PyYAML unavailable)"); sys.exit(0)
p = sys.argv[1]
txt = open(p).read()
# Frontmatter on a command file is OPTIONAL — a command that is pure prose is
# valid, and the counterfeit corpus's known-good baseline is exactly that. This
# gate is about MALFORMED frontmatter, not absent frontmatter; failing the
# latter over-rejects valid plugins. (Caught by the counterfeit tier when this
# check was first written too strictly — the corpus turning red on its own
# calibration baseline is the tier working as designed.)
if not txt.startswith("---"):
    print(f"  PASS {p} (no frontmatter — nothing to parse)"); sys.exit(0)
parts = txt.split("---", 2)
if len(parts) < 3:
    print(f"  FAIL {p} (unterminated frontmatter)"); sys.exit(1)
try:
    yaml.safe_load(parts[1])
except Exception as e:
    first = str(e).splitlines()[0]
    print(f"  FAIL {p} (unparseable YAML: {first})"); sys.exit(1)
print(f"  PASS {p}")
PY
  if [ $? -eq 0 ]; then pass=$((pass+1)); else fail=$((fail+1)); fi
done < <(find plugins -path '*/commands/*.md' -type f | sort)

# --- 5. Reverse lockfile: every plugin dir is registered --------------------
# Section 3 checks marketplace -> dir (forward). This is the reverse: any
# plugins/<name>/ that ships a plugin.json MUST have a matching marketplace
# entry. Without this, a plugin could exist on disk yet be unregistered — and an
# unregistered plugin is never enumerated in section 10, so its per-plugin safety
# pack would silently never run. Fail closed on the gap.
group "reverse lockfile (every plugin dir registered)"
python3 - "$REPO_ROOT" <<'PY'
import json, os, sys, glob
root = sys.argv[1]
mkt = json.load(open(os.path.join(root, ".claude-plugin", "marketplace.json")))
registered = { (p.get("source","") or "").lstrip("./").rstrip("/") for p in mkt.get("plugins", []) }
fail = 0
for manifest in sorted(glob.glob(os.path.join(root, "plugins", "*", ".claude-plugin", "plugin.json"))):
    d = os.path.relpath(os.path.dirname(os.path.dirname(manifest)), root)
    if d in registered:
        print(f"  PASS {d} registered in marketplace")
    else:
        print(f"  FAIL {d} has a plugin.json but no marketplace entry"); fail += 1
sys.exit(1 if fail else 0)
PY
if [ $? -eq 0 ]; then pass=$((pass+1)); else fail=$((fail+1)); fi

# --- 5b. README documents every registered plugin ---------------------------
# README.md carries a hand-maintained plugin table. It has gone stale before —
# it once named only 2 of 11 registered plugins with no warning from any check.
# Fail closed: every plugin name in marketplace.json must appear as its own
# token somewhere in README.md (a Markdown link target `plugins/<name>/` or a
# bare `<name>` mention both count), or the build goes red instead of the docs
# quietly aging out of sync with what's actually installable. This check reads
# the repo's own README.md, not the synthetic counterfeit root's, so it is a
# REPO-level gate like sections 11/11b/12 below.
if [ -f "README.md" ]; then
  group "README documents every registered plugin"
  python3 - "$REPO_ROOT" <<'PY'
import json, os, re, sys
root = sys.argv[1]
mkt = json.load(open(os.path.join(root, ".claude-plugin", "marketplace.json")))
readme = open(os.path.join(root, "README.md")).read()
fail = 0
for p in mkt.get("plugins", []):
    name = p.get("name", "")
    # word-boundary match so e.g. "voice" doesn't false-positive on "invoice"
    if re.search(r'(?<![\w-])' + re.escape(name) + r'(?![\w-])', readme):
        print(f"  PASS {name} is named in README.md")
    else:
        print(f"  FAIL {name} is registered in marketplace.json but not named in README.md"); fail += 1
sys.exit(1 if fail else 0)
PY
  if [ $? -eq 0 ]; then pass=$((pass+1)); else fail=$((fail+1)); fi
fi

# --- 6. No unfilled placeholder tokens in shipped prose/manifests -----------
# The scaffolder fills every {{token}} at generation time. A surviving {{...}} in
# a shipped *.md or *.json means a plugin went out with an unfilled template — a
# broken manifest or a hole in the prose. Scripts are intentionally excluded: the
# generator and its dogfood legitimately mention "{{placeholder}}" as machinery;
# they describe the token, they don't ship it.
group "no unfilled {{placeholder}} tokens (prose/manifests)"
ph=0
while IFS= read -r f; do
  if grep -qF '{{' "$f"; then bad "$f still contains an unfilled {{...}} token"; ph=$((ph+1)); fi
done < <(find plugins \( -name '*.md' -o -name '*.json' \) -type f | sort)
[ "$ph" -eq 0 ] && ok "no unfilled placeholder tokens in any plugin prose or manifest"

# --- 7. AGENTS.md references only real paths --------------------------------
# A plugin's AGENTS.md is the map another harness follows into the plugin. A
# backticked path token that doesn't resolve is a broken map. Only tokens that
# contain a "/" are treated as paths (a bare `SKILL.md` is a generic reference,
# and templates like `skills/<name>/...` carry a "<" and are skipped); each real
# path is resolved plugin-dir-first, then repo-root.
group "AGENTS.md references resolve to real files"
python3 - "$REPO_ROOT" <<'PY'
import os, re, sys
root = sys.argv[1]
tok = re.compile(r'`([^`]+)`')
pathish = re.compile(r'^[A-Za-z0-9._-]+(/[A-Za-z0-9._-]+)+$')
fail = 0
for base, _, files in os.walk(os.path.join(root, "plugins")):
    if "AGENTS.md" not in files: continue
    agents = os.path.join(base, "AGENTS.md")
    if os.path.islink(agents): continue
    for t in (m.strip() for m in tok.findall(open(agents).read())):
        if not pathish.match(t): continue
        if os.path.exists(os.path.join(base, t)) or os.path.exists(os.path.join(root, t)):
            continue
        print(f"  FAIL {os.path.relpath(agents, root)} references `{t}` which does not exist"); fail += 1
if fail == 0:
    print("  PASS every backticked path in every plugin AGENTS.md resolves")
sys.exit(1 if fail else 0)
PY
if [ $? -eq 0 ]; then pass=$((pass+1)); else fail=$((fail+1)); fi

# --- 8. Red-by-default sentinel never ships ---------------------------------
# The scaffolder writes a UUID-shaped sentinel into each new plugin's checks.sh
# so a freshly scaffolded (unimplemented) plugin is RED until a human writes real
# checks. If that sentinel survives into a committed plugin, the plugin shipped
# with a placeholder eval — fail closed. The generator itself legitimately embeds
# the literal, so any file marked SCAFFOLD-SENTINEL-SOURCE is exempt.
group "no red-by-default sentinel in shipped plugins"
SENTINEL='SCAFFOLD-UNIMPLEMENTED-b3f1c2a4-7d6e-4f0a-9c2b-1e5d8a4f6c30'
st=0
while IFS= read -r f; do
  grep -q 'SCAFFOLD-SENTINEL-SOURCE' "$f" && continue
  bad "$f still carries the red-by-default sentinel (unimplemented eval shipped)"; st=$((st+1))
done < <(grep -rlF "$SENTINEL" plugins 2>/dev/null)
[ "$st" -eq 0 ] && ok "no shipped plugin carries the unimplemented sentinel"

# --- 9. Portability lint (per plugin) ---------------------------------------
# Prose that leans on Claude-Code-only machinery (hooks, subagents, the Workflow
# tool's parallel()/pipeline()) is allowed only with a portability caveat. The
# shared linter enforces that per plugin dir.
group "portability lint (per plugin)"
while IFS= read -r d; do
  if out="$(evals/cheap/portability-lint.sh "$d" 2>&1)"; then
    ok "portability: $d"
  else
    bad "portability: $d"
    printf '%s\n' "$out" | sed 's/^/    /'
  fi
done < <(find plugins -mindepth 1 -maxdepth 1 -type d | sort)

# --- 10. Per-plugin safety checks (fail-closed discovery) ------------------
# Enumerate every plugin registered in the marketplace and source its cheap eval
# pack. A registered plugin MUST ship plugins/<source>/evals/cheap/checks.sh —
# a missing pack is a FAILURE, never a skip, so no plugin can ship without the
# deterministic safety checks the cheap tier exists to enforce. Each pack runs
# with cwd = repo root and inherits ok/bad/group above; PLUGIN_NAME / PLUGIN_DIR
# are exported for packs that prefer plugin-relative paths.
while IFS= read -r entry; do
  PLUGIN_NAME="${entry%%$'\t'*}"
  PLUGIN_SRC="${entry#*$'\t'}"
  PLUGIN_DIR="$PLUGIN_SRC"
  pack="$PLUGIN_SRC/evals/cheap/checks.sh"
  if [ -f "$pack" ]; then
    export PLUGIN_NAME PLUGIN_DIR
    # shellcheck source=/dev/null
    . "$pack"
  else
    group "plugin '$PLUGIN_NAME' cheap eval pack"
    bad "plugin '$PLUGIN_NAME' ($PLUGIN_SRC) has no cheap eval pack at $pack"
  fi
done < <(python3 - "$REPO_ROOT" <<'PY'
import json, os, sys
root = sys.argv[1]
mkt = json.load(open(os.path.join(root, ".claude-plugin", "marketplace.json")))
for p in mkt.get("plugins", []):
    src = (p.get("source", "") or "").lstrip("./")
    print(f"{p.get('name','')}\t{src}")
PY
)

# --- 11. Branch-protection lock (winner #15) --------------------------------
# The four required status checks and the two deep-tier safety paths are frozen
# in ci/required-checks.json; ci/check_branch_protection.py asserts each still
# appears verbatim in .github/workflows/evals.yml, so branch protection can't
# drift away from what CI emits. This is a REPO-level gate, not a per-plugin one,
# and it fires only when the workflow exists at the repo root — so it's active in
# the real repo (fail-closed on drift) yet inert in the synthetic counterfeit
# root, which carries neither .github/ nor ci/. FAIL substring: "branch-protection drift".
if [ -f ".github/workflows/evals.yml" ]; then
  group "branch-protection lock (required checks in sync with workflow)"
  if python3 ci/check_branch_protection.py --self-test >/dev/null 2>&1; then
    ok "check_branch_protection.py self-test"
  else
    bad "check_branch_protection.py self-test failed"
  fi
  if out="$(python3 ci/check_branch_protection.py --repo . 2>&1)"; then
    ok "branch protection in sync with .github/workflows/evals.yml"
  else
    bad "branch-protection drift between ci/required-checks.json and the workflow"
    printf '%s\n' "$out" | sed 's/^/    /'
  fi
fi

# --- 11b. Paid-pack discovery self-test -------------------------------------
# evals/paid/discover-paid-packs.sh is the single source of truth the workflow's
# paid (behavioral/deep) matrices are built from via fromJSON. Its --self-test
# proves the fail-closed contract (declared-but-broken => fail; absent => skip)
# and that real-repo discovery stays self-consistent. It previously drifted false
# (stale hardcoded expectations) UNNOTICED because nothing invoked it — wire it
# here so a broken discovery script is a red cheap tier. REPO-level gate (needs
# evals/paid/), inert in the synthetic counterfeit root that carries no evals/paid/.
if [ -f "evals/paid/discover-paid-packs.sh" ]; then
  group "paid-pack discovery self-test"
  if bash evals/paid/discover-paid-packs.sh --self-test >/dev/null 2>&1; then
    ok "discover-paid-packs.sh self-test"
  else
    bad "discover-paid-packs.sh self-test failed — the paid-pack discovery contract drifted"
  fi
fi

# --- 12. Install-smoke coverage (every registered plugin) -------------------
# The install smoke test (ci/install-smoke.sh) proves ONE plugin installs
# structurally. In CI it is fanned out over a matrix enumerated from
# marketplace.json, so new plugins are auto-covered there — but that coverage
# lives only in the workflow. Nothing in this always-on deterministic gate
# asserts that every registered plugin is actually smoke-tested, so if a plugin
# were ever dropped from the matrix (or the CI wiring drifted) its coverage could
# silently dip with the required cheap tier still green. Close that gap here: run
# the smoke test for EVERY plugin enumerated from the lockfile — the same source
# of truth section 10 uses — and fail closed if any plugin is missing or does not
# install. This is a REPO-level gate (it needs ci/install-smoke.sh) so, like the
# branch-protection lock, it is active in the real repo yet inert in the synthetic
# counterfeit root, which carries no ci/ directory.
if [ -f "ci/install-smoke.sh" ]; then
  group "install-smoke coverage (every registered plugin)"
  while IFS= read -r sm_plugin; do
    [ -z "$sm_plugin" ] && continue
    if out="$(ci/install-smoke.sh "$sm_plugin" 2>&1)"; then
      ok "install smoke: '$sm_plugin' installs structurally"
    else
      bad "install smoke: '$sm_plugin' is not covered by a passing smoke test"
      printf '%s\n' "$out" | sed 's/^/    /'
    fi
  done < <(python3 - "$REPO_ROOT" <<'PY'
import json, os, sys
root = sys.argv[1]
mkt = json.load(open(os.path.join(root, ".claude-plugin", "marketplace.json")))
for p in mkt.get("plugins", []):
    print(p.get("name", ""))
PY
)
fi

# --- summary ----------------------------------------------------------------
printf '\n\033[1msummary:\033[0m %d passed, %d failed\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
