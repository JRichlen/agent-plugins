#!/usr/bin/env bash
# Remove the T31 entry from the staged adapter.json catalog fragment while
# leaving index.json's allocation (T31 -> adapter) untouched. See DEFECT.md.
set -euo pipefail
root="${1:?usage: mutate.sh <synthetic-root>}"
target="$root/evals/agentic/manifests/catalog/adapter.json"

if [ ! -f "$target" ]; then
  echo "mutate.sh: $target not found (evals/agentic/ not staged into the synthetic root)" >&2
  exit 1
fi

python3 - "$target" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, encoding="utf-8") as f:
    doc = json.load(f)

before = len(doc["entries"])
doc["entries"] = [e for e in doc["entries"] if e.get("id") != "T31"]
if len(doc["entries"]) != before - 1:
    print(f"mutate.sh: expected to remove exactly one T31 entry from {path}", file=sys.stderr)
    sys.exit(1)

with open(path, "w", encoding="utf-8") as f:
    json.dump(doc, f, indent=2, sort_keys=True)
PY

echo "mutate.sh: removed the T31 entry from $target"
