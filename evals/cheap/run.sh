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

# --- 7b. Relative markdown links resolve to real files ----------------------
# Same failure shape as §7 (AGENTS.md path check) but for markdown-syntax
# links `[text](target)` in EVERY .md file under plugins/, not just AGENTS.md.
# context-handoff shipped exactly this defect: a reference doc linked its
# sibling checker script with the wrong `../../` depth, and nothing caught it
# because the only check that touched that line grepped for the script's
# BASENAME rather than resolving the path. Only local, non-anchor-only
# targets are checked — `http(s)://`, `mailto:`, and other URL schemes are
# skipped (they can't be resolved offline), as are bare `#fragment` links.
# A target's own `#fragment`/`?query` suffix is stripped before resolving,
# and `/`-rooted targets resolve from the repo root (GitHub renders those as
# repo-root-relative). Each target is resolved relative to the directory of
# the .md file that links it, per plain relative-link semantics.
group "relative markdown links resolve to real files"
python3 - "$REPO_ROOT" <<'PY'
import os, re, sys
root = sys.argv[1]
link = re.compile(r'!?\[[^\]]*\]\((<[^>]*>|[^)\s]+)(?:\s+"[^"]*")?\)')
scheme = re.compile(r'^[A-Za-z][A-Za-z0-9+.-]*:')
fail = 0
checked = 0
for base, _, files in os.walk(os.path.join(root, "plugins")):
    for fn in files:
        if not fn.endswith(".md"): continue
        src = os.path.join(base, fn)
        if os.path.islink(src): continue
        for m in link.finditer(open(src, encoding="utf-8").read()):
            raw = m.group(1).strip()
            if not raw or raw.startswith("#"): continue
            # CommonMark angle-bracket destination: <path/to/file>
            if raw.startswith("<") and raw.endswith(">"):
                inner = raw[1:-1]
                # template placeholder (e.g. <plugin-name>) — not a real path
                if re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*', inner):
                    continue
                target = inner
            else:
                # skip if it still contains < or > (template placeholder outside angle form)
                if "<" in raw or ">" in raw:
                    continue
                target = raw
            if not target or target.startswith("#"): continue
            if target.startswith("//") or scheme.match(target): continue  # http(s)://, //host, mailto:, etc.
            target = target.split("#", 1)[0].split("?", 1)[0]
            if not target: continue
            checked += 1
            resolve_from = root if target.startswith("/") else base
            candidate = os.path.realpath(os.path.join(resolve_from, target.lstrip("/")))
            root_real = os.path.realpath(root)
            if os.path.commonpath((root_real, candidate)) != root_real:
                print(f"  FAIL {os.path.relpath(src, root)} links `{target}` which escapes the repository"); fail += 1; continue
            if os.path.exists(candidate): continue
            print(f"  FAIL {os.path.relpath(src, root)} links `{target}` which does not resolve to a real file"); fail += 1
if fail == 0:
    print(f"  PASS all {checked} local relative markdown links resolve")
sys.exit(1 if fail else 0)
PY
if [ $? -eq 0 ]; then pass=$((pass+1)); else fail=$((fail+1)); fi

# --- 7c. Every references/ doc is linked from its own SKILL.md ---------------
# A reference file nothing links is shipped but INERT: progressive disclosure is
# the only way a skill loads it, so an unlinked reference never takes effect.
# Found by independent verification of the redgate slices: three growth-loop
# amendment files existed on disk while zero host skills referenced them.
group "references are reachable from their own SKILL.md"
python3 - "$REPO_ROOT" <<'PY_ORPHAN'
import os, sys
root = sys.argv[1]
fail = 0
checked = 0
for base, dirs, files in os.walk(os.path.join(root, "plugins")):
    if os.path.basename(base) != "references":
        continue
    skill = os.path.join(os.path.dirname(base), "SKILL.md")
    if not os.path.isfile(skill):
        continue
    text = open(skill, encoding="utf-8").read()
    for fn in sorted(files):
        if not fn.endswith(".md"):
            continue
        checked += 1
        if f"references/{fn}" in text:
            continue
        rel = os.path.relpath(os.path.join(base, fn), root)
        print(f"  FAIL {rel} is never linked from {os.path.relpath(skill, root)} — shipped but inert")
        fail += 1
if fail == 0:
    print(f"  PASS all {checked} reference docs are linked from their own SKILL.md")
sys.exit(1 if fail else 0)
PY_ORPHAN
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

# --- 13. Cross-plugin reference resolution -----------------------------------
# Plugins name each other in prose: wayfinder points at `grill-me` and
# `orchestrate`, context-handoff at `dev-diary`, docs-hygiene at `graveyard`,
# the voice skills at each other. A rename or removal of the referenced plugin
# leaves the referrer steering the model toward a skill that no longer exists —
# a broken map, same failure shape as §7 but across plugin boundaries. Roster =
# every plugin name in marketplace.json + every plugins/*/skills/<name>/ dir.
# Two COUPLED probes, both asserted by the script's exit code:
#   (1) DYNAMIC: every backticked hyphenated token (`foo-bar` shape — the
#       marketplace's skill-name convention) in any SKILL.md or AGENTS.md must
#       resolve in the roster or appear in the curated NONSKILL ignore set
#       (ordinary hyphenated prose terms like `api-key`, discovered by actually
#       grepping the repo). An unknown hyphenated token fails closed: either
#       the reference is broken, or the ignore set needs a reviewed addition.
#   (2) CURATED PAIRS: non-hyphenated plugin names (`graveyard`, `orchestrate`)
#       are indistinguishable from prose, so those live in an explicit
#       (file, referenced-name) allowlist grepped from the repo. Each pair's
#       file must still carry the backtick reference (a vanished reference =
#       stale allowlist = FAIL, keeping the list maintained) and the name must
#       resolve in the roster.
group "cross-plugin reference resolution"
python3 - "$REPO_ROOT" <<'PY'
import glob, json, os, re, sys
root = sys.argv[1]
# Roster: marketplace plugin names + every skill directory name.
mkt = json.load(open(os.path.join(root, ".claude-plugin", "marketplace.json")))
roster = {p.get("name", "") for p in mkt.get("plugins", [])}
roster |= {os.path.basename(d.rstrip("/"))
           for d in glob.glob(os.path.join(root, "plugins", "*", "skills", "*", ""))}
# Hyphenated backtick tokens that are NOT skill references (grepped from the
# repo; extend only after eyeballing the new token in context).
NONSKILL = {
    "oauth-client-id", "oauth-secret", "api-key", "client-id",   # credential nouns
    "as-of", "general-purpose",                                   # plain prose
    "derived-verify", "pipelined-verdict-wins",                   # orchestrate workflow templates
    "homelab-board", "ansible-homelab-sim",                       # worked-example artifacts
    "consolidate-delta", "judge-calibration", "path-consent",     # reference docs, not skills
    "engineering-default",                                        # agent-compiler golden example/registry view
}
tok = re.compile(r'`([a-z][a-z0-9]*(?:-[a-z0-9]+)+)`')
fail = 0
scanned = 0
files = sorted(glob.glob(os.path.join(root, "plugins", "*", "skills", "*", "SKILL.md")) +
               glob.glob(os.path.join(root, "plugins", "*", "AGENTS.md")))
for f in files:
    if os.path.islink(f):
        continue
    scanned += 1
    for name in sorted(set(tok.findall(open(f, encoding="utf-8").read()))):
        if name in roster or name in NONSKILL:
            continue
        print(f"  FAIL {os.path.relpath(f, root)} references `{name}` — not an installed plugin/skill "
              f"and not in the curated non-skill set"); fail += 1
if fail == 0:
    print(f"  PASS every hyphenated backtick reference in {scanned} SKILL.md/AGENTS.md files resolves")
# Curated pairs for non-hyphenated plugin names the dynamic probe can't see.
PAIRS = [
    ("plugins/docs-hygiene/skills/docs-hygiene/SKILL.md",       "graveyard"),
    ("plugins/context-handoff/skills/context-handoff/SKILL.md", "orchestrate"),
    ("plugins/wayfinder/AGENTS.md",                             "orchestrate"),
    ("plugins/wayfinder/skills/wayfinder/SKILL.md",             "orchestrate"),
]
pfail = 0
for rel, name in PAIRS:
    path = os.path.join(root, rel)
    if not os.path.isfile(path):
        # Missing file is STALENESS only when the plugin is installed here.
        # A minimal/synthetic marketplace (counterfeit tier) has neither the
        # plugin nor the file, which is not a defect — skip it.
        _plug = rel.split("/")[1] if rel.startswith("plugins/") else ""
        if _plug and os.path.isdir(os.path.join(root, "plugins", _plug)):
            print(f"  FAIL curated pair: {rel} does not exist (stale allowlist)"); pfail += 1
        continue
    if f"`{name}`" not in open(path, encoding="utf-8").read():
        print(f"  FAIL curated pair: {rel} no longer references `{name}` (stale allowlist)"); pfail += 1; continue
    if name not in roster:
        print(f"  FAIL {rel} references `{name}` which is not an installed plugin/skill"); pfail += 1; continue
print(f"  PASS all {len(PAIRS)} curated non-hyphenated references still present and resolving"
      if pfail == 0 else f"  ({pfail} curated pair(s) failed)")
sys.exit(1 if (fail or pfail) else 0)
PY
if [ $? -eq 0 ]; then pass=$((pass+1)); else fail=$((fail+1)); fi

# --- 14. Context-tax budget --------------------------------------------------
# Every installed plugin pays rent in the model's context window before it does
# any work: the root CLAUDE.md, each SKILL.md frontmatter description, and each
# plugin.json description are always-resident surfaces. Nothing bounded that
# spend, so twenty small additions could quietly crowd out the window this
# marketplace's skills need to actually run in. This check is the mandate:
# report the per-plugin bill and fail when (a) any single description exceeds
# 1024 chars (largest today: tailscale-wif SKILL.md at 995) or (b) the
# estimated total (chars/4) exceeds 9000 tokens. Measured at authoring time:
# 28933 chars ≈ 7233 tokens, so 9000 leaves ~20% headroom — enough for a couple
# of new plugins, tight enough that unbounded description growth goes red here
# instead of silently taxing every session.
group "context-tax budget (always-resident surfaces)"
python3 - "$REPO_ROOT" <<'PY'
import glob, json, os, sys
try:
    import yaml
except ImportError:
    print("  SKIP context-tax budget (PyYAML unavailable)"); sys.exit(0)
root = sys.argv[1]
MAX_DESC_CHARS = 1024
BUDGET_TOKENS  = 9000   # measured 2026-08: 7233 est tokens -> ~20% headroom
fail = 0
rows = []   # (label, chars)
claude_md = os.path.join(root, "CLAUDE.md")
rows.append(("CLAUDE.md (root)", os.path.getsize(claude_md) if os.path.isfile(claude_md) else 0))
per_plugin = {}
def take(label, plugin, text):
    global fail
    n = len(text)
    per_plugin[plugin] = per_plugin.get(plugin, 0) + n
    if n > MAX_DESC_CHARS:
        print(f"  FAIL {label} description is {n} chars (> {MAX_DESC_CHARS})"); fail += 1
for m in sorted(glob.glob(os.path.join(root, "plugins", "*", ".claude-plugin", "plugin.json"))):
    plugin = m.split(os.sep)[-3]
    take(f"{plugin}/plugin.json", plugin, json.load(open(m)).get("description", "") or "")
for s in sorted(glob.glob(os.path.join(root, "plugins", "*", "skills", "*", "SKILL.md"))):
    plugin = s.split(os.sep)[-4]
    txt = open(s, encoding="utf-8").read()
    parts = txt.split("---", 2)
    if not txt.startswith("---") or len(parts) < 3:
        print(f"  FAIL {os.path.relpath(s, root)} has no parseable frontmatter"); fail += 1; continue
    try:
        fm = yaml.safe_load(parts[1]) or {}
    except Exception:
        continue  # §4b already reports unparseable frontmatter
    take(os.path.relpath(s, root), plugin, fm.get("description", "") or "")
rows += sorted(per_plugin.items())
total = sum(n for _, n in rows)
for label, n in rows:
    print(f"  {label:<28} {n:>6} chars  ~{n // 4:>5} tokens")
print(f"  {'TOTAL':<28} {total:>6} chars  ~{total // 4:>5} tokens  (budget {BUDGET_TOKENS} tokens)")
if total // 4 > BUDGET_TOKENS:
    print(f"  FAIL estimated context tax {total // 4} tokens exceeds the {BUDGET_TOKENS}-token budget"); fail += 1
if fail == 0:
    print(f"  PASS all descriptions <= {MAX_DESC_CHARS} chars and total within budget")
sys.exit(1 if fail else 0)
PY
if [ $? -eq 0 ]; then pass=$((pass+1)); else fail=$((fail+1)); fi

# --- 15. Version drift (marketplace <-> plugin.json) -------------------------
# marketplace.json entries carry a version and so does each plugin.json; nothing
# tied them together, so a bumped plugin.json with a stale marketplace entry (or
# vice versa) would advertise one version and install another. Fail closed: a
# plugin.json with a missing or empty version field is a FAIL outright, and when
# the marketplace entry also carries a version the two must be byte-identical.
group "version drift (marketplace <-> plugin.json)"
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
        continue  # §3 already reports the missing manifest
    pv = json.load(open(manifest)).get("version")
    if not pv:
        print(f"  FAIL {name}: plugin.json has no version field (fail-closed)"); fail += 1; continue
    mv = p.get("version")
    if mv is not None and mv != pv:
        print(f"  FAIL {name}: marketplace.json version '{mv}' != plugin.json version '{pv}'"); fail += 1; continue
    print(f"  PASS {name}: version {pv}" + ("" if mv is None else " (matches marketplace entry)"))
sys.exit(1 if fail else 0)
PY
if [ $? -eq 0 ]; then pass=$((pass+1)); else fail=$((fail+1)); fi

# --- 16. Secret-scan gate on agent-written exhaust --------------------------
# Agent-written exhaust — redgate gates.log files, dev-diary drafts under docs/
# — is the surface where a pasted credential ships without any human WITNESS
# reading it closely. evals/cheap/secret-gate.sh is the mechanical WITNESS
# (dependency-free grep -E; see its header for the gitleaks/trufflehog upgrade
# path). Two halves here, both COUPLED to exit codes, never a message grep:
#   (i)  DISCOVER the exhaust surfaces that actually exist in-repo and scan
#        each — discovery, not a fixed list, so new .redgate dirs or diary
#        drafts are covered the day they appear (and absence is a no-op, not
#        a failure: no exhaust means nothing can have leaked).
#   (ii) NEGATIVE CONTROL: stage COPIES of the leaky/clean fixtures OUTSIDE
#        /fixtures/ (the scanner allowlists that segment by design) and assert
#        exit 1 on the planted fake AWS key and exit 0 on the clean control.
#        This is what makes the gate falsifiable — gut the scanner's pattern
#        table and this section, not silence, goes red. The tier stays green
#        in the synthetic counterfeit root too: the fixtures travel inside the
#        copied evals/cheap/. FAIL substring: "secret gate".
group "secret gate (agent-written exhaust)"
SG="evals/cheap/secret-gate.sh"
SG_FIXDIR="evals/cheap/fixtures/secret-gate"
if [ ! -x "$SG" ] || [ ! -f "$SG_FIXDIR/leaky.txt" ] || [ ! -f "$SG_FIXDIR/clean.txt" ]; then
  bad "secret gate machinery missing (scanner or fixtures) — the exhaust surface is unguarded"
else
  # (i) scan every agent-exhaust surface present in-repo
  sg_found=0
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    sg_found=$((sg_found+1))
    if out="$("$SG" "$f" 2>&1)"; then
      ok "secret gate: exhaust clean: $f"
    else
      bad "secret gate: secret-shaped string in $f"
      printf '%s\n' "$out" | sed 's/^/    /'
    fi
  done < <({ find .redgate -type f -name 'gates.log' 2>/dev/null; \
             find docs -maxdepth 1 -type f -name 'dev-diary*' 2>/dev/null; } | sort)
  [ "$sg_found" -eq 0 ] && ok "secret gate: no agent-exhaust surfaces in-repo (nothing to scan)"

  # (ii) negative control — assert the scanner's teeth on both fixtures
  sg_tmp="$(mktemp -d)"
  cp "$SG_FIXDIR/leaky.txt" "$sg_tmp/leaky.txt"
  cp "$SG_FIXDIR/clean.txt" "$sg_tmp/clean.txt"
  "$SG" "$sg_tmp/leaky.txt" >/dev/null 2>&1; sg_rc=$?
  if [ "$sg_rc" -eq 1 ]; then
    ok "secret gate: negative control — scanner exits 1 on the planted fake AWS key"
  else
    bad "secret gate: negative control FAILED — scanner exited $sg_rc (not 1) on the leaky fixture; the gate is blind"
  fi
  "$SG" "$sg_tmp/clean.txt" >/dev/null 2>&1; sg_rc=$?
  if [ "$sg_rc" -eq 0 ]; then
    ok "secret gate: clean control — scanner exits 0 on secret-free prose"
  else
    bad "secret gate: clean control FAILED — scanner exited $sg_rc (not 0) on clean prose; the gate over-flags"
  fi
  # allowlist contract: at its in-repo /fixtures/ path the leaky file is exempt,
  # or the always-on tier could never keep its own negative-control bait.
  if "$SG" "$SG_FIXDIR/leaky.txt" >/dev/null 2>&1; then
    ok "secret gate: /fixtures/ allowlist honored (in-repo fixture exempt)"
  else
    bad "secret gate: /fixtures/ allowlist broken — the gate flags its own eval fixtures"
  fi
  rm -rf "$sg_tmp"
fi

# --- 17. Routing eval structure (roster-level trigger routing) --------------
# The behavioral routing pack (evals/routing/) actually runs in CI with a live
# model; the cheap tier guards its STRUCTURE so a broken pack can't ship green:
# roster.txt is in sync with the marketplace, the config parses, it carries
# enough positive scenarios AND the calibration negatives, and every positive
# routes to a real installed plugin. Coupled to real state — add a plugin
# without regenerating the roster, or point a scenario at a nonexistent skill,
# and this goes red.
group "routing eval — structure"
# Repo-level pack: a marketplace root without evals/routing/ (the counterfeit
# tier's synthetic root, or a fork that hasn't adopted it) has nothing to check.
# Absent => skip; present-but-broken => fail.
if [ ! -f evals/routing/promptfooconfig.yaml ]; then
  ok "routing: no routing pack in this root — nothing to check"
elif evals/routing/gen-roster.sh --check >/dev/null 2>&1; then
  ok "routing: roster.txt is in sync with the marketplace"
else
  bad "routing: roster.txt is STALE — run evals/routing/gen-roster.sh > evals/routing/roster.txt"
fi
if [ -f evals/routing/promptfooconfig.yaml ]; then
python3 - "$REPO_ROOT" <<'PYR'
import json, os, re, sys
root = sys.argv[1]
cfgp = os.path.join(root, "evals", "routing", "promptfooconfig.yaml")
rosp = os.path.join(root, "evals", "routing", "roster.txt")
fail = 0
try:
    import yaml
    cfg = yaml.safe_load(open(cfgp)); tests = cfg.get("tests", [])
    parsed = "yaml"
except Exception:
    # PyYAML may be absent in some CI images; fall back to counting test blocks.
    cfg = None
    tests = re.findall(r'^\s*- description:', open(cfgp).read(), re.M)
    parsed = "regex-fallback"
raw = open(cfgp).read()
# The typed composition line (RQ-002): each scenario's expected answer pins a
# `specialist=` slot — a named skill is a must-fire, `none` is a calibration
# negative. Envelope/guard/interaction names are covered by the closed-vocabulary
# check below (and, fully, by route-contract.test.js in the RQ-002 section).
routes = re.findall(r'specialist=([a-z0-9-]+)', raw)
positives = [r for r in routes if r != "none"]
negatives = [r for r in routes if r == "none"]
roster = {l.split(":", 1)[0].strip() for l in open(rosp) if l.strip()}
if len(positives) >= 6:
    print(f"  PASS routing: {len(positives)} must-fire scenarios (>=6) [{parsed}]")
else:
    print(f"  FAIL routing: only {len(positives)} must-fire scenarios (<6)"); fail += 1
if len(negatives) >= 2:
    print(f"  PASS routing: {len(negatives)} must-not-fire calibration negatives (>=2)")
else:
    print(f"  FAIL routing: {len(negatives)} calibration negatives (<2) — a fire-on-everything router would pass"); fail += 1
# Every name in ANY slot of an expected line must be an installed skill.
slot_names = set()
for grp in re.findall(r'(?:specialist|envelope|guards|interaction_owner)=([a-z0-9,-]+)', raw):
    slot_names.update(n for n in grp.split(",") if n and n != "none")
missing = sorted(n for n in slot_names if n not in roster)
if missing:
    print(f"  FAIL routing: scenarios route to non-installed skills: {missing}"); fail += 1
else:
    print(f"  PASS routing: every skill named in an expected route targets an installed plugin")
sys.exit(1 if fail else 0)
PYR
if [ $? -eq 0 ]; then pass=$((pass+1)); else fail=$((fail+1)); fi
fi

# --- 18. Statistical gate (pass-rate.sh) is wired and actually bites ---------
# Gap #4: the routing pack runs each scenario repeat:5 times and pass-rate.sh
# enforces a per-scenario floor so a lucky single pass can't read green. Guard
# offline that (a) the pack still declares repeat, (b) CI still invokes the gate,
# and (c) pass-rate.sh genuinely fails a below-floor run and passes an at-floor
# one — run against synthetic fixtures so the gate is mutation-proven without a
# model call. Coupled: drop repeat, unwire the gate, or invert its verdict and
# this goes red.
group "statistical gate — pass-rate floor bites"
# The repeat:/CI-wiring halves only apply where a routing pack exists; the
# pass-rate.sh fixture halves are repo-independent and always run.
if [ ! -f evals/routing/promptfooconfig.yaml ]; then
  ok "statistical gate: no routing pack in this root — repeat/CI wiring not applicable"
elif grep -qE '^\s*repeat:\s*[0-9]+' evals/routing/promptfooconfig.yaml; then
  ok "routing pack declares repeat: (scenarios run more than once)"
else
  bad "routing pack lost its repeat: — n=1 greens are uninterpretable again"
fi
if [ ! -f .github/workflows/evals.yml ]; then
  ok "statistical gate: no workflow file in this root — CI wiring not applicable"
elif grep -q 'pass-rate.sh' .github/workflows/evals.yml; then
  ok "CI wires pass-rate.sh into the routing job"
else
  bad "CI no longer invokes pass-rate.sh — the statistical floor is not enforced"
fi
# Every behavioral (rubric) pack must ALSO declare repeat: — a single-shot rubric
# leg is the same uninterpretable n=1 green the routing pack fixed, and one 504
# would sink it. Skip-when-absent so the counterfeit synthetic root (no plugins/)
# stays green; bite only where a real pack is PRESENT but lost its repeat.
_pf_packs="$(ls -d plugins/*/evals/promptfoo 2>/dev/null || true)"
if [ -z "$_pf_packs" ]; then
  ok "statistical gate: no behavioral packs in this root — repeat check not applicable"
else
  _missing_repeat=""
  for _d in $_pf_packs; do
    _cfg="$_d/promptfooconfig.yaml"
    [ -f "$_cfg" ] || continue
    grep -qE '^\s*repeat:\s*[0-9]+' "$_cfg" || _missing_repeat="$_missing_repeat $(basename "$(dirname "$(dirname "$_d")")")"
  done
  if [ -n "$_missing_repeat" ]; then
    bad "behavioral pack(s) lost repeat: —$_missing_repeat — n=1 rubric greens are uninterpretable and a 504 sinks the leg"
  else
    ok "every behavioral pack declares repeat: (rubric legs run more than once)"
  fi
fi
_pr="evals/paid/pass-rate.sh"
_tmp="$(mktemp -d)"
python3 - "$_tmp" <<'PYF'
import json, sys
d = sys.argv[1]
# Fixtures use the REAL promptfoo >= 0.122 row shape: a passing row carries
# failureReason 0 and error null; an ASSERTION-failed row carries failureReason 1
# AND an .error string (the assertion message); a transport-error row carries
# failureReason 2 and the provider error. .error alone no longer discriminates.
def prow(desc): return {"testCase":{"description":desc},"success":True,"failureReason":0,"error":None,"response":{"output":"hello"}}
def frow(desc): return {"testCase":{"description":desc},"success":False,"failureReason":1,"error":"Expected output to match regex \"X\"","response":{"output":"wrong answer"}}
def rows(desc, n, passes): return [prow(desc) if i < passes else frow(desc) for i in range(n)]
def erow(desc): return {"testCase":{"description":desc},"success":False,"failureReason":2,"error":"API error: The operation was aborted, Code: 504","response":{"output":""}}
json.dump({"results":{"results": rows("A",5,5)+rows("B",5,4)}}, open(d+"/good.json","w"))   # 1.0, 0.8
json.dump({"results":{"results": rows("A",5,5)+rows("C",5,2)}}, open(d+"/bad.json","w"))    # 0.4 -> below 0.8
json.dump({"results":{"results": rows("A",1,1)}}, open(d+"/under.json","w"))                # n=1 -> fail-closed
# FAULT semantics (gap #4, the observed 504): a transport error is an INVALID
# sample, excluded from the floor — a scenario that really passed its 2 valid
# attempts must not go red because a 3rd attempt 504'd.
json.dump({"results":{"results": rows("A",3,3)+[prow("B"),prow("B"),erow("B")]}}, open(d+"/fault-ok.json","w"))
# ...but an all-FAULT scenario is "never tested", not "green": fail closed.
json.dump({"results":{"results": rows("A",3,3)+[erow("C"),erow("C"),erow("C")]}}, open(d+"/fault-starved.json","w"))
# ...and a real assertion failure (failureReason 1) carrying .error — which under
# promptfoo >= 0.122 is EVERY assertion failure — must be scored as a FAIL
# against the floor, never excluded as a FAULT: 4 pass + 1 real fail = 0.80,
# below a 0.9 floor. Excluding it would read 4/4 = 1.00 and pass (the PR #93
# counterfeit-green).
json.dump({"results":{"results": rows("D",5,4)}}, open(d+"/real-fail.json","w"))
# ...and .error ALONE may only mean FAULT when failureReason is ABSENT (the
# legacy-shape fallback). A row that carries failureReason 0 (present, not an
# error, not an assertion) + a non-empty .error + success false is an
# unexplained non-pass: it must be SCORED as a FAIL, never excluded. Before the
# fix the code applied the .error fallback to every non-assertion row, so this
# read 4/4 = 1.00 (1 FAULT excluded) and passed a 0.9 floor (fail-open).
def zrow(desc): return {"testCase":{"description":desc},"success":False,"failureReason":0,"error":"Expected output to match regex \"X\"","response":{"output":"wrong answer"}}
json.dump({"results":{"results": rows("E",4,4)+[zrow("E")]}}, open(d+"/fr0-error.json","w"))
PYF
if bash "$_pr" "$_tmp/good.json" --floor 0.8 --min-runs 2 >/dev/null 2>&1; then
  ok "pass-rate: an at-floor run passes (0.8 >= 0.8)"
else
  bad "pass-rate: at-floor run wrongly failed — floor logic broken"
fi
if bash "$_pr" "$_tmp/bad.json" --floor 0.8 --min-runs 2 >/dev/null 2>&1; then
  bad "pass-rate: a below-floor scenario (0.4) passed — the gate does not bite"
else
  ok "pass-rate: a below-floor scenario (0.4) fails the run"
fi
if bash "$_pr" "$_tmp/under.json" --floor 0.8 --min-runs 2 >/dev/null 2>&1; then
  bad "pass-rate: an n=1 run passed — fail-closed repeat guard broken"
else
  ok "pass-rate: an n=1 (un-repeated) run fails closed"
fi
# A single transport FAULT must be EXCLUDED, not counted as a rubric failure:
# scenario B is 2/2 on its valid samples with one 504 dropped -> the run passes.
if bash "$_pr" "$_tmp/fault-ok.json" --floor 0.8 --min-runs 2 --min-valid 2 >/dev/null 2>&1; then
  ok "pass-rate: a transport FAULT (504) is excluded, not scored as a failure"
else
  bad "pass-rate: a 504 was counted as a rubric failure — the n=1 fragility is back"
fi
# An all-FAULT scenario has zero valid samples -> the model was never actually
# tested -> must fail CLOSED (a 504 storm is not a green).
if bash "$_pr" "$_tmp/fault-starved.json" --floor 0.8 --min-runs 2 --min-valid 2 >/dev/null 2>&1; then
  bad "pass-rate: an all-504 scenario passed — a FAULT storm read as green (fail-open)"
else
  ok "pass-rate: an all-FAULT scenario fails closed (never tested != green)"
fi
# A real assertion failure (failureReason 1) carries .error under promptfoo
# >= 0.122; it must be scored as a FAIL against the floor, never excluded as a
# FAULT. 4/5 = 0.80 < 0.9 must fail — if the fail is laundered as a FAULT the
# run reads 4/4 = 1.00 and passes (the exact counterfeit green from PR #93).
if bash "$_pr" "$_tmp/real-fail.json" --floor 0.9 --min-runs 2 --min-valid 2 >/dev/null 2>&1; then
  bad "pass-rate: a real assertion failure carrying .error was excluded as a FAULT — failures launder as weather (fail-open)"
else
  ok "pass-rate: a real assertion failure carrying .error is scored as FAIL, not excluded as FAULT"
fi
# failureReason PRESENT (0) + .error + not passed: the .error fallback must NOT
# fire — only a row with NO failureReason may be FAULTed on .error alone. 4/5 =
# 0.80 < 0.9 must fail; laundering the row reads 4/4 = 1.00 and passes.
if bash "$_pr" "$_tmp/fr0-error.json" --floor 0.9 --min-runs 2 --min-valid 2 >/dev/null 2>&1; then
  bad "pass-rate: a failureReason=0 non-pass carrying .error was excluded as a FAULT — .error overrides a present failureReason (fail-open)"
else
  ok "pass-rate: .error alone FAULTs only when failureReason is absent; a present failureReason=0 non-pass is scored FAIL"
fi
rm -rf "$_tmp"

# --- 19. Example gallery (docs/examples) is in sync and non-fabricated -------
# The published before/after gallery is a VERIFICATION surface: every card is a
# real, provenanced with-skill/without-skill model run captured from the eval
# tier (docs/examples/data/*.json), rendered to docs/examples/index.html by
# docs/build-examples.sh. Guard offline that the committed HTML is in sync with
# the data (so a stale page can't ship), and that no snapshot ships without the
# two outputs and provenance that make it verifiable rather than marketing.
# Coupled: edit a snapshot without regenerating, or drop a snapshot's provenance,
# and this goes red.
group "example gallery — sync and provenance"
# Repo-level surface: absent => skip (a minimal marketplace has no gallery);
# present-but-stale or present-but-unprovenanced => fail. Presence is -e, not
# -x, so a dropped exec bit cannot silently skip the whole check.
if [ ! -e docs/build-examples.sh ]; then
  ok "example gallery: not present in this root — nothing to check"
elif [ ! -x docs/build-examples.sh ]; then
  bad "examples: build-examples.sh exists but is not executable — chmod +x it"
elif docs/build-examples.sh --check >/dev/null 2>&1; then
  ok "examples: index.html is in sync with docs/examples/data/"
else
  bad "examples: index.html is STALE — run docs/build-examples.sh"
fi
if [ -e docs/build-examples.sh ]; then
python3 - "$REPO_ROOT" <<'PYE'
import glob, json, os, sys
root = sys.argv[1]
fail = 0
found = 0
for f in sorted(glob.glob(os.path.join(root, "docs", "examples", "data", "*.json"))):
    found += 1
    name = os.path.basename(f)
    try:
        s = json.load(open(f))
    except Exception as e:
        print(f"  FAIL examples/{name}: invalid JSON ({e})"); fail += 1; continue
    prob = []
    for k in ("plugin", "prompt", "with_skill", "without_skill", "provenance"):
        if not s.get(k): prob.append(f"missing {k}")
    for side in ("with_skill", "without_skill"):
        if isinstance(s.get(side), dict) and not (s[side].get("output") or "").strip():
            prob.append(f"{side} has no output")
    prov = s.get("provenance") or {}
    for k in ("source", "model"):
        if not prov.get(k): prob.append(f"provenance missing {k}")
    # a plugin snapshot must name a real installed plugin
    if s.get("plugin") and not os.path.isdir(os.path.join(root, "plugins", s["plugin"])):
        prob.append(f"plugin '{s['plugin']}' is not installed")
    if prob:
        print(f"  FAIL examples/{name}: " + "; ".join(prob)); fail += 1
    else:
        print(f"  PASS examples/{name}: real pair with provenance ({s['plugin']})")
if found == 0:
    print("  FAIL example gallery declared but docs/examples/data/ is empty"); fail += 1
# PLAN.md's "committed snapshots | **N of M**" row is a hand-written count that
# drifted twice (14 of 23 over a 15-file directory and a 24-plugin marketplace).
# Pin it to the data: N is the snapshot count, M the marketplace plugin count.
import re
plan = os.path.join(root, "docs", "examples", "PLAN.md")
mp = os.path.join(root, ".claude-plugin", "marketplace.json")
if os.path.exists(plan) and os.path.exists(mp):
    m = re.search(r"\| committed snapshots \| \*\*(\d+) of (\d+)\*\*", open(plan).read())
    plugins = len((json.load(open(mp)).get("plugins") or []))
    if not m:
        print("  FAIL examples: PLAN.md has no 'committed snapshots | **N of M**' row"); fail += 1
    elif (int(m.group(1)), int(m.group(2))) != (found, plugins):
        print(f"  FAIL examples: PLAN.md says {m.group(1)} of {m.group(2)} snapshots, but docs/examples/data/ holds {found} and the marketplace lists {plugins} plugins"); fail += 1
    else:
        print(f"  PASS examples: PLAN.md snapshot count ({found} of {plugins}) matches the data directory and the marketplace")
sys.exit(1 if fail else 0)
PYE
if [ $? -eq 0 ]; then pass=$((pass+1)); else fail=$((fail+1)); fi
fi

# ═══ BEGIN testing-doc drift guard (issue #89) ═══════════════════════════════
# --- 20. Testing-doc drift (docs/testing.md <-> live tier inventory) ---------
# docs/testing.md is the authoritative tier inventory, and the standing order
# (root AGENTS.md) says any PR that adds/removes/renames/re-scopes an eval
# tier, workflow job, or per-plugin pack must update it in the same PR. This
# gate makes that order bite: evals/cheap/check-testing-doc.sh derives the
# live inventory DYNAMICALLY (job names from .github/workflows/*.yml|*.yaml,
# eval dirs from evals/*/, plugin-qualified packs from plugins/*/evals/*/)
# and compares it — both directions — against the doc's machine-readable
# LIVE-INVENTORY block.
# REPO-level gate: active in the real repo (where a MISSING docs/testing.md is
# itself drift and fails closed), inert in the counterfeit tier's synthetic
# root. The inertness marker is `.git` — present at the real repo root (a dir,
# or a file in a git worktree), never created in the counterfeit runner's
# synthetic temp root, and deliberately NOT part of the tracked inventory: an
# earlier marker (evals/counterfeits/) was itself a tracked eval-dir, so a PR
# removing that tier would have made this guard silently skip the very drift
# it exists to catch. The marker must never be something the inventory tracks.
# FAIL substring: "testing-doc drift".
if [ -d ".github/workflows" ] && [ -e ".git" ] \
   && [ -f "evals/cheap/check-testing-doc.sh" ]; then
  group "testing-doc drift (docs/testing.md <-> live tier inventory)"
  if out="$(bash evals/cheap/check-testing-doc.sh 2>&1)"; then
    ok "docs/testing.md inventory matches the live workflows, eval dirs, and per-plugin packs"
  else
    bad "testing-doc drift — docs/testing.md and the live tier inventory disagree"
    printf '%s\n' "$out" | sed 's/^/    /'
  fi
fi
# ═══ END testing-doc drift guard ═════════════════════════════════════════════

# --- 21. Design-trajectory timeline (docs/timeline) is in sync and receipted --
# The decision timeline is generated from a hand-curated inventory
# (docs/timeline/data/decisions.json) by docs/timeline/build-timeline.sh. Guard
# offline that the committed HTML is in sync with the data, and that no entry
# ships without the schema that makes it checkable: a forcing problem, a
# decision, and at least one receipt that resolves (a repo path that exists, or
# a link into this repository). Cut entries must record why they were cut.
# Coupled: edit the data without regenerating, break a receipt path, or drop a
# cut entry's reason, and this goes red.
group "design-trajectory timeline — sync and receipts"
# Repo-level surface: absent => skip; present-but-stale, present-but-broken,
# or unreceipted => fail. Presence is -e, not -x, so a dropped exec bit cannot
# silently skip the whole check.
if [ ! -e docs/timeline/build-timeline.sh ]; then
  ok "timeline: not present in this root — nothing to check"
elif [ ! -x docs/timeline/build-timeline.sh ]; then
  bad "timeline: build-timeline.sh exists but is not executable — chmod +x it"
elif docs/timeline/build-timeline.sh --check >/dev/null 2>&1; then
  ok "timeline: index.html is in sync with docs/timeline/data/decisions.json"
else
  bad "timeline: index.html is STALE — run docs/timeline/build-timeline.sh"
fi
if [ -e docs/timeline/build-timeline.sh ]; then
python3 - "$REPO_ROOT" <<'PYT'
import json, os, re, subprocess, sys
root = sys.argv[1]
fail = 0
has_git = os.path.isdir(os.path.join(root, ".git"))
# Per receipt: a sha that resolves is verified in any clone. A sha that does
# not resolve is a FAIL in a full clone, but only "unverifiable" in a shallow
# one (CI's default fetch-depth: 1 cannot see history) — reported out loud,
# never silently green.
shallow = has_git and subprocess.run(["git", "-C", root, "rev-parse", "--is-shallow-repository"],
                                     capture_output=True, text=True).stdout.strip() == "true"
verified_shas = 0
unverified_shas = 0
def flunk(msg):
    global fail
    print(f"  FAIL timeline: {msg}"); fail += 1
try:
    data = json.load(open(os.path.join(root, "docs", "timeline", "data", "decisions.json")))
except Exception as e:
    flunk(f"invalid JSON ({e})"); sys.exit(1)
if not (data.get("thesis") or "").strip():
    flunk("missing thesis")

repo = "https://github.com/JRichlen/agent-plugins"
root_real = os.path.realpath(root)
def check_receipts(owner, receipts):
    """Every published claim — a decision, a methodology rung, a horizon item —
    carries at least one receipt that resolves: a repo path that exists (confined
    to the repo root), or a URL into this repository (commit shas verified)."""
    global verified_shas, unverified_shas
    if not receipts:
        flunk(f"{owner}: no receipts — every claim must be checkable"); return
    for r in receipts:
        if not (r.get("label") or "").strip():
            flunk(f"{owner}: receipt missing label")
        url = r.get("url") if isinstance(r.get("url"), str) else ""
        rpath = r.get("path") if isinstance(r.get("path"), str) else ""
        url, rpath = url.strip(), rpath.strip()
        if bool(url) == bool(rpath):
            flunk(f"{owner}: receipt '{r.get('label','?')}' needs exactly one non-empty url/path")
        elif rpath:
            full = os.path.realpath(os.path.join(root, rpath))
            if full != root_real and not full.startswith(root_real + os.sep):
                flunk(f"{owner}: receipt path escapes the repository: {rpath}")
            elif not os.path.exists(full):
                flunk(f"{owner}: receipt path does not exist: {rpath}")
        else:
            if url != repo and not url.startswith(repo + "/"):
                flunk(f"{owner}: receipt url points outside this repository: {url}")
            else:
                m = re.search(r"/commit/([0-9a-f]{7,40})$", url)
                if m:
                    if has_git:
                        ok_sha = subprocess.run(["git", "-C", root, "cat-file", "-e", m.group(1) + "^{commit}"],
                                                capture_output=True).returncode == 0
                        if ok_sha: verified_shas += 1
                        elif shallow: unverified_shas += 1
                        else: flunk(f"{owner}: commit receipt does not resolve in this clone: {m.group(1)}")
                    else:
                        unverified_shas += 1

era_ids = []
for e in data.get("eras", []):
    for k in ("id", "title", "window", "lesson"):
        if not (e.get(k) or "").strip(): flunk(f"era {e.get('id','?')}: missing {k}")
    era_ids.append(e.get("id"))
if len(era_ids) != len(set(era_ids)):
    flunk("duplicate era ids")
# acts partition the eras: every era in exactly one act, every act non-empty
acts = data.get("acts") or []
if acts:
    seen_eras = []
    for a in acts:
        for k in ("id", "title", "summary"):
            if not (a.get(k) or "").strip(): flunk(f"act {a.get('id','?')}: missing {k}")
        if not a.get("eras"): flunk(f"act {a.get('id','?')}: names no eras")
        for eid in a.get("eras", []):
            if eid not in era_ids: flunk(f"act {a.get('id','?')}: unknown era '{eid}'")
            seen_eras.append(eid)
    for eid in era_ids:
        n = seen_eras.count(eid)
        if n != 1: flunk(f"era {eid} appears in {n} acts (must be exactly one)")
seen = set()
shown = 0
for d in data.get("decisions", []):
    did = d.get("id", "?")
    if did in seen: flunk(f"{did}: duplicate decision id")
    seen.add(did)
    for k in ("id", "era", "date", "title", "forced_by", "decided"):
        if not (d.get(k) or "").strip(): flunk(f"{did}: missing {k}")
    if d.get("era") not in era_ids:
        flunk(f"{did}: unknown era '{d.get('era')}'")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d.get("date") or ""):
        flunk(f"{did}: date not ISO (YYYY-MM-DD)")
    if not isinstance(d.get("curated"), bool):
        flunk(f"{did}: curated must be true or false")
    elif d["curated"]:
        shown += 1
    elif not (d.get("cut_reason") or "").strip():
        flunk(f"{did}: cut from the page without a recorded cut_reason")
    check_receipts(did, d.get("receipts") or [])
if shown == 0:
    flunk("no curated decisions — the page would be empty")
# the methodology ladder and the horizon are published claims too
# the page must say, in its own data, that it is a learning journey in progress
if len((data.get("disclosure") or "").strip()) < 80:
    flunk("disclosure: the page must carry an in-progress disclosure (data.disclosure, at least 80 chars)")
tiers = (data.get("methodology") or {}).get("tiers") or []
for t in tiers:
    tid = f"tier:{t.get('id','?')}"
    for k in ("id", "title", "proves", "cannot", "born_in"):
        if not (t.get(k) or "").strip(): flunk(f"{tid}: missing {k}")
    if t.get("born_in") and t["born_in"] not in seen:
        flunk(f"{tid}: born_in '{t['born_in']}' is not a recorded decision — a rung must name the decision that created it")
    check_receipts(tid, t.get("receipts") or [])
items = (data.get("horizon") or {}).get("items") or []
for h in items:
    hid = f"horizon:{h.get('id','?')}"
    for k in ("id", "title", "status", "question"):
        if not (h.get(k) or "").strip(): flunk(f"{hid}: missing {k}")
    check_receipts(hid, h.get("receipts") or [])
if fail == 0:
    sha_note = f"{verified_shas} commit receipts verified in the object store"
    if unverified_shas:
        sha_note += f", {unverified_shas} NOT verified ({'shallow clone' if shallow else 'no .git in this root'})"
    print(f"  PASS timeline: {shown} curated of {len(seen)} recorded decisions, {len(tiers)} methodology rungs, {len(items)} horizon items — every path receipt exists, every URL points into this repo, {sha_note}")
sys.exit(1 if fail else 0)
PYT
if [ $? -eq 0 ]; then pass=$((pass+1)); else fail=$((fail+1)); fi
fi

# ─── BEGIN RQ-001 behavior-surface trigger map ───────────────────────────────
# The behavior-bearing path definition is frozen in ci/behavior-surfaces.json;
# ci/check_behavior_surfaces.py asserts (offline, no model call) that the
# workflow's behavioral/routing filters stay in verbatim lockstep with it, that
# a counterfeit table of changed-file cases — including behavior edits OUTSIDE
# SKILL.md — selects exactly the packs it should, and that both legs announce
# EVALUATED vs SKIPPED. REPO-level gate: inert where the workflow or spec is
# absent. FAIL substring: "behavior-surface drift".
if [ -f "ci/check_behavior_surfaces.py" ] && [ -f ".github/workflows/evals.yml" ]; then
  group "behavior-surface trigger map (behavioral/routing selection)"
  if python3 ci/check_behavior_surfaces.py --self-test >/dev/null 2>&1; then
    ok "check_behavior_surfaces.py self-test"
  else
    bad "check_behavior_surfaces.py self-test failed"
  fi
  if out="$(python3 ci/check_behavior_surfaces.py --repo . 2>&1)"; then
    ok "behavior-bearing edits (incl. outside SKILL.md) select their behavioral/routing packs"
  else
    bad "behavior-surface drift: a behavior-bearing edit would not select its eval pack"
    printf '%s\n' "$out" | sed 's/^/    /'
  fi
fi
# ─── END RQ-001 behavior-surface trigger map ─────────────────────────────────

# ─── BEGIN RQ-002 typed route/step contracts (offline) ───────────────────────
# The composition routing pack (evals/routing/) and its redgate trajectory pack
# (evals/routing/trajectory/) grade a typed ROUTE:/STEP: line through fail-closed
# javascript contracts. These node tests prove, offline and with no model call:
# every scenario's expected line validates, a malformed/ambiguous fixture set
# rejects (each fail-closed rule exercised individually), the trajectory
# cross-field invariants bite (MAJOR ⇒ no proceed unless approved; auto ⇒ patch),
# and the S1 legacy single-skill strings (`ROUTE: diagnosing-bugs`,
# `ROUTE: redgate`) cannot satisfy the composition contract — the deterministic
# half of issue #88's acceptance criteria, before any key is spent. REPO-level
# gate: inert where the routing pack is absent (the counterfeit synthetic root);
# present-but-broken => fail. FAIL substring: "route/step contract".
if [ -f evals/routing/route-contract.test.js ]; then
  group "typed route/step contracts (offline, deterministic)"
  if ! command -v node >/dev/null 2>&1; then
    ok "route/step contracts: node unavailable locally — SKIPPED here; CI's ubuntu runner executes them"
  else
    if out="$(node evals/routing/route-contract.test.js 2>&1)"; then
      ok "route contract: expected lines validate; malformed + S1 legacy fixtures reject"
    else
      bad "route/step contract: route-contract.test.js failed"
      printf '%s\n' "$out" | sed 's/^/    /'
    fi
    if [ -f evals/routing/trajectory/step-contract.test.js ]; then
      if out="$(node evals/routing/trajectory/step-contract.test.js 2>&1)"; then
        ok "step contract: trajectory gate invariants hold; malformed fixtures reject"
      else
        bad "route/step contract: step-contract.test.js failed"
        printf '%s\n' "$out" | sed 's/^/    /'
      fi
    else
      bad "route/step contract: routing pack present without trajectory/step-contract.test.js (fail-closed)"
    fi
  fi
fi
# ─── END RQ-002 typed route/step contracts ───────────────────────────────────

# ─── BEGIN behavioral-pack no-tools clause ───────────────────────────────────
# --- 21. Every behavioral pack's subject prompt forbids tool-call syntax -------
# The behavioral tier is a SINGLE-reply harness: the subject model never gets a
# tool result back. A cheap subject model can still stochastically emit fake
# tool-call syntax (e.g. `<tool name="read" args={"path": "src/list.js"} />`)
# and stop, with no final answer for the grader to judge — PR #95 run
# 33592173756 lost two of three scope-fence rows exactly that way, and the same
# pack was green minutes later on PR #96. Under the honest statistical gate
# (pass-rate.sh scores real assertion failures against the floor) such rows are
# real FAILs, so any pack could flip red on any run. Each pack's subject prompt
# therefore carries an explicit no-tools clause; this gate asserts the
# load-bearing phrase is still present in EVERY pack so it cannot drift out of
# one prompt silently. The prompt surface is DISCOVERED from each pack's
# promptfooconfig.yaml (`- file://<prompt>` under `prompts:`), never assumed to
# be prompt.txt: tailscale-wif renders its subject prompt from prompt.js, and a
# gate that only scanned prompt.txt reported green while that pack was still
# exposed (Codex review, PR #97). A pack whose config names a prompt file that
# does not exist, or names none, fails too. REPO-level gate, same inertness
# marker as §20 (`.git`): the counterfeit tier's synthetic root ships no
# promptfoo packs. Fail-closed: zero packs found in the real repo is itself a
# failure. FAIL substring: "no-tools clause".
if [ -e ".git" ]; then
  group "behavioral packs: subject prompt forbids tool-call syntax"
  NO_TOOLS_PHRASE='never emit tool-call'
  pack_prompts=0
  for cfg in plugins/*/evals/promptfoo/promptfooconfig.yaml; do
    [ -f "$cfg" ] || continue
    cfg_dir=$(dirname "$cfg")
    # every `file://…` under the prompts: block (comments stripped); the block
    # ends at the next top-level key.
    prompt_refs=$(awk '/^prompts:/{p=1;next} p&&/^[^ #-]/{p=0} p' "$cfg" \
      | sed 's/#.*$//' | grep -o 'file://[^[:space:]"'"'"']*' | sed 's#^file://##' || true)
    if [ -z "$prompt_refs" ]; then
      bad "no-tools clause: $cfg names no file:// prompt under prompts: — the gate cannot see this pack's subject prompt"
      continue
    fi
    for ref in $prompt_refs; do
      pp="$cfg_dir/$ref"
      if [ ! -f "$pp" ]; then
        bad "no-tools clause: $cfg names $ref but $pp does not exist"
        continue
      fi
      pack_prompts=$((pack_prompts+1))
      has "$pp" "$NO_TOOLS_PHRASE" \
        "$pp carries the no-tools clause" \
        "$pp is missing the no-tools clause ('$NO_TOOLS_PHRASE') — a subject that emits fake tool-call syntax and stops scores as a real FAIL"
    done
  done
  if [ "$pack_prompts" -eq 0 ]; then
    bad "no-tools clause: no behavioral pack prompt found via plugins/*/evals/promptfoo/promptfooconfig.yaml — the gate has nothing to protect"
  fi
fi
# ─── END behavioral-pack no-tools clause ─────────────────────────────────────

# --- summary ----------------------------------------------------------------
printf '\n\033[1msummary:\033[0m %d passed, %d failed\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
