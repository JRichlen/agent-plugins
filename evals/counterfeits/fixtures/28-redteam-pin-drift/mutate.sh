#!/usr/bin/env bash
set -euo pipefail

root="$1"
target="$root/evals/redteam/pin.json"

if [[ ! -f "$target" ]]; then
  echo "28-redteam-pin-drift: $target not staged -- inert until build_root() stages evals/redteam/** (see DEFECT.md)" >&2
  exit 0
fi

python3 - "$target" <<'PY'
import json
import sys

p = sys.argv[1]
with open(p) as f:
    data = json.load(f)
data["promptfoo"]["version"] = "0.123.0"
with open(p, "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
PY
