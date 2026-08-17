#!/usr/bin/env bash
#
# scaffold-plugin.sh — deterministically generate a new marketplace plugin
# skeleton and wire it into the marketplace lockfile in one command.
#
# The whole point is that the mechanical, error-prone parts of adding a plugin —
# a valid plugin.json, a SKILL.md with real frontmatter, the AGENTS.md +
# CLAUDE.md/GEMINI.md cross-harness symlinks, a command stub, and — critically —
# the marketplace.json entry — are produced identically every time, with NO
# unfilled {{placeholder}} tokens and NO timestamps or randomness. Determinism is
# what lets the plugin-factory dogfood its own output byte-for-byte in the cheap
# eval (see plugins/plugin-factory/evals/cheap/checks.sh).
#
# Two safety properties are baked in on purpose:
#   * Invariant-first (#3): SKILL.md leads with an "## Invariant" section, so the
#     author states what must ALWAYS/NEVER hold before writing any prose.
#   * Red-by-default (#13): the generated evals/cheap/checks.sh is a stub that
#     FAILS CLOSED — it carries an unguessable sentinel and calls bad(), so a
#     freshly scaffolded plugin cannot show green until a human replaces it with
#     real deterministic checks for that plugin's invariant.
#
# Usage:
#   scaffold-plugin.sh <name> [options]
#     --description TEXT   one-line plugin description (marketplace + manifest)
#     --author TEXT        author name (default: Jordan Richlen)
#     --invariant TEXT     the load-bearing "always/never" for this plugin
#     --root DIR           marketplace root (default: auto-detected repo root)
#     --force              overwrite an existing plugins/<name>/ directory
#
# Exit 0 on success; nonzero (with a message on stderr) on any refusal.
set -euo pipefail

# --- the red-by-default sentinel -------------------------------------------
# SCAFFOLD-SENTINEL-SOURCE: this generator legitimately embeds the sentinel
# literal below so it can write it into every red stub. evals/cheap/run.sh's
# sentinel scan skips any file carrying this SCAFFOLD-SENTINEL-SOURCE marker, so
# the generator itself is allowed to contain it while shipped stubs are not.
SENTINEL='SCAFFOLD-UNIMPLEMENTED-b3f1c2a4-7d6e-4f0a-9c2b-1e5d8a4f6c30'

die() { echo "scaffold-plugin: $*" >&2; exit 1; }

# --- parse args -------------------------------------------------------------
NAME=""
DESC=""
AUTHOR="Jordan Richlen"
INVARIANT=""
ROOT=""
FORCE=0
while [ $# -gt 0 ]; do
  case "$1" in
    --description) DESC="${2:?--description needs a value}"; shift 2 ;;
    --author)     AUTHOR="${2:?--author needs a value}"; shift 2 ;;
    --invariant)  INVARIANT="${2:?--invariant needs a value}"; shift 2 ;;
    --root)       ROOT="${2:?--root needs a value}"; shift 2 ;;
    --force)      FORCE=1; shift ;;
    -h|--help)    grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    --*)          die "unknown option: $1" ;;
    *)            [ -z "$NAME" ] && NAME="$1" || die "unexpected argument: $1"; shift ;;
  esac
done

[ -n "$NAME" ] || die "usage: scaffold-plugin.sh <name> [options]"

# --- validate name ----------------------------------------------------------
# kebab-case so it's a safe directory name, a valid plugin id, and a clean
# command/skill slug all at once.
case "$NAME" in
  *[!a-z0-9-]*|-*|*-|"") die "name '$NAME' must be kebab-case: ^[a-z][a-z0-9-]*\$ (lowercase, digits, hyphens; no leading/trailing hyphen)" ;;
esac
[[ "$NAME" =~ ^[a-z] ]] || die "name '$NAME' must start with a lowercase letter"

# --- locate the marketplace root -------------------------------------------
if [ -z "$ROOT" ]; then
  # walk up from this script until we find the marketplace manifest
  d="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  while [ "$d" != "/" ]; do
    [ -f "$d/.claude-plugin/marketplace.json" ] && { ROOT="$d"; break; }
    d="$(dirname "$d")"
  done
  [ -n "$ROOT" ] || die "could not auto-detect marketplace root; pass --root DIR"
fi
ROOT="$(cd "$ROOT" && pwd)"
[ -f "$ROOT/.claude-plugin/marketplace.json" ] || die "no .claude-plugin/marketplace.json under --root $ROOT"

PLUGIN_DIR="$ROOT/plugins/$NAME"
if [ -e "$PLUGIN_DIR" ] && [ "$FORCE" -ne 1 ]; then
  die "plugins/$NAME already exists; pass --force to overwrite"
fi

[ -n "$DESC" ] || DESC="TODO: one-line description of what the $NAME plugin does and when to reach for it."
[ -n "$INVARIANT" ] || INVARIANT="State the one thing that must ALWAYS hold and the one thing that must NEVER happen for this plugin. Until this is a real, testable invariant, the red-by-default eval stub keeps this plugin failing the cheap tier on purpose."

# --- create the skeleton ----------------------------------------------------
rm -rf "$PLUGIN_DIR"
mkdir -p "$PLUGIN_DIR/.claude-plugin" \
         "$PLUGIN_DIR/skills/$NAME" \
         "$PLUGIN_DIR/commands" \
         "$PLUGIN_DIR/evals/cheap"

# plugin.json (version 0.0.1 — a scaffold is pre-release until implemented)
python3 - "$PLUGIN_DIR/.claude-plugin/plugin.json" "$NAME" "$DESC" "$AUTHOR" <<'PY'
import json, sys
out, name, desc, author = sys.argv[1:5]
data = {
  "name": name,
  "version": "0.0.1",
  "description": desc,
  "author": {"name": author},
  "repository": "https://github.com/JRichlen/agent-plugins",
  "homepage": f"https://github.com/JRichlen/agent-plugins/tree/main/plugins/{name}",
  "license": "MIT",
  "keywords": [],
  "skills": "./skills/",
  "commands": "./commands/",
}
with open(out, "w") as f:
  json.dump(data, f, indent=2)
  f.write("\n")
PY

# SKILL.md — invariant-first (#3): the invariant leads, before any workflow prose.
cat > "$PLUGIN_DIR/skills/$NAME/SKILL.md" <<SKILL
---
name: $NAME
description: >-
  $DESC
  Use this skill whenever the user is working with $NAME.
---

# $NAME

## Invariant

$INVARIANT

Write this first, before any workflow prose. The invariant is what the cheap
eval defends; everything below exists to keep it true.

## When to use this

TODO: the contexts and user phrases that should trigger this skill.

## How it works

TODO: the workflow. Prefer portable prose and deterministic scripts over
harness-specific machinery so the skill works on any harness.
SKILL

# AGENTS.md — cross-harness entry point. Only references paths this scaffold
# actually creates, so the AGENTS.md real-path gate in run.sh stays green.
cat > "$PLUGIN_DIR/AGENTS.md" <<AGENTS
# AGENTS.md — $NAME

$DESC

## How to use it

Read \`skills/$NAME/SKILL.md\` and follow it — it is the authoritative
description of this plugin's workflow and the invariant it defends.

The command \`commands/$NAME.md\` is the entry point a user invokes.

## The invariant this plugin defends

$INVARIANT

The deterministic checks that defend it live in \`evals/cheap/checks.sh\` and run
as part of the marketplace cheap tier.
AGENTS

# Cross-harness symlinks so harnesses reading CLAUDE.md / GEMINI.md find AGENTS.md.
( cd "$PLUGIN_DIR" && ln -sf AGENTS.md CLAUDE.md && ln -sf AGENTS.md GEMINI.md )

# README.md
cat > "$PLUGIN_DIR/README.md" <<README
# $NAME

$DESC

## Install

\`\`\`
/plugin marketplace add JRichlen/agent-plugins
/plugin install $NAME@jrichlen
\`\`\`

## Status

Freshly scaffolded. The cheap eval is intentionally RED until you replace
\`evals/cheap/checks.sh\` with real deterministic checks for this plugin's
invariant (see \`AGENTS.md\`).

## License

MIT
README

# command stub
cat > "$PLUGIN_DIR/commands/$NAME.md" <<CMD
---
description: $DESC
---

Invoke the \`$NAME\` skill and follow \`skills/$NAME/SKILL.md\`.

TODO: describe what this command does for the user.
CMD

# evals/cheap/checks.sh — RED BY DEFAULT (#13). Sourced by run.sh; inherits
# ok/bad/group and PLUGIN_NAME/PLUGIN_DIR. It fails closed until implemented.
cat > "$PLUGIN_DIR/evals/cheap/checks.sh" <<CHECKS
# Cheap eval pack for the '$NAME' plugin — SOURCED by evals/cheap/run.sh with
# cwd = repo root; inherits ok/bad/group and \$PLUGIN_NAME / \$PLUGIN_DIR.
#
# RED BY DEFAULT: this stub fails closed so a freshly scaffolded plugin cannot
# ship green with zero safety coverage. Replace the body below with real,
# deterministic checks of THIS plugin's invariant (grep for a load-bearing
# marker, assert a generated file's shape, validate a manifest field), then
# delete the sentinel line and the bad() call.
group "plugin '\$PLUGIN_NAME' cheap eval pack (UNIMPLEMENTED)"
# $SENTINEL
bad "plugin '\$PLUGIN_NAME' still ships the scaffold's red-by-default stub — replace \$PLUGIN_DIR/evals/cheap/checks.sh with real checks for its invariant before it can go green"
CHECKS

# --- wire into the marketplace lockfile (#6) --------------------------------
# marketplace.json is the generated lockfile: adding a plugin dir without a
# matching entry is a wiring error the cheap tier rejects, so the generator
# writes the entry itself (idempotently — replacing any stale entry of the same
# name) rather than trusting a human to hand-edit JSON.
python3 - "$ROOT/.claude-plugin/marketplace.json" "$NAME" "$DESC" "$AUTHOR" <<'PY'
import json, sys
path, name, desc, author = sys.argv[1:5]
mkt = json.load(open(path))
plugins = mkt.setdefault("plugins", [])
entry = {
    "name": name,
    "description": desc,
    "version": "0.0.1",
    "source": f"./plugins/{name}",
    "author": {"name": author},
    "license": "MIT",
    "keywords": [],
}
for i, p in enumerate(plugins):
    if p.get("name") == name:
        plugins[i] = entry
        break
else:
    plugins.append(entry)
with open(path, "w") as f:
    json.dump(mkt, f, indent=2)
    f.write("\n")
PY

echo "scaffolded plugins/$NAME (red-by-default) and wired it into marketplace.json"
echo "next: fill the TODOs, state a real invariant, and replace evals/cheap/checks.sh with real checks."
