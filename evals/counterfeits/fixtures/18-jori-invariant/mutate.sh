#!/usr/bin/env bash
set -euo pipefail

root="$1"
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(cd "$here/../../../.." && pwd)"
plugin="$root/plugins/jori"

# Exercise the shipped Jori pack, never a fixture-owned substitute. The copied
# plugin must first remain structurally valid so the expected failure comes from
# its actual invariant check.
cp -R "$repo/plugins/jori" "$plugin"

python3 - "$root/.claude-plugin/marketplace.json" "$repo/plugins/jori/.claude-plugin/plugin.json" <<'PY'
import json, sys
p, manifest = sys.argv[1:]
doc = json.load(open(p))
live = json.load(open(manifest))
doc["plugins"].append({k: live[k] for k in ("name", "version", "description", "author", "license", "keywords")}
                      | {"source": "./plugins/jori"})
with open(p, "w") as f:
    json.dump(doc, f)
PY
printf '\njori\n' >> "$root/README.md"
sed -i 's/Workers do not interview the user or expand authority/Workers may interview the user or expand authority/' "$plugin/skills/jori/SKILL.md"
