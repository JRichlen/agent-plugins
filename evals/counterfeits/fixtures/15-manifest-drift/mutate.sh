#!/usr/bin/env bash
# Change plugin.json's description without touching the marketplace.json entry,
# so the two manifests drift apart.
set -euo pipefail
root="${1:?usage: mutate.sh <synthetic-root>}"
manifest="$root/plugins/sample-guard/.claude-plugin/plugin.json"
python3 - "$manifest" <<'PY'
import json, sys
p = sys.argv[1]
d = json.load(open(p))
d["description"] = d["description"] + " DRIFTED"
json.dump(d, open(p, "w"), indent=2)
PY
