#!/usr/bin/env bash
set -euo pipefail

root="$1"
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(cd "$here/../../../.." && pwd)"
plugin="$root/plugins/delegated-intelligence"

# Exercise the shipped delegation pack, never a fixture-owned substitute. The copied
# plugin must first remain structurally valid so the expected failure comes from
# its actual invariant check.
cp -R "$repo/plugins/delegated-intelligence" "$plugin"

python3 - "$root/.claude-plugin/marketplace.json" "$repo/plugins/delegated-intelligence/.claude-plugin/plugin.json" <<'PY'
import json, sys
p, manifest = sys.argv[1:]
doc = json.load(open(p))
live = json.load(open(manifest))
doc["plugins"].append({k: live[k] for k in ("name", "version", "description", "author", "license", "keywords")}
                      | {"source": "./plugins/delegated-intelligence"})
with open(p, "w") as f:
    json.dump(doc, f)
PY
printf '\ndelegated-intelligence\n' >> "$root/README.md"
sed -i 's/Workers never receive/Workers may receive/' "$plugin/skills/delegated-intelligence/SKILL.md"
