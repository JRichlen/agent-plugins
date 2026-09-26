#!/usr/bin/env bash
# Append an unmatched tool ("AdminOverride") to the baseline arm's
# allowed_tools in the staged evals/agentic/manifests/arms/graveyard.json.
# It is neither a shared generic tool nor the declared generic_equivalent of
# any full_package_arm capability in the same file -- the "unmatched
# widening" defect pairing.assert_exposure_parity must reject. See
# DEFECT.md for the current (wired and firing) status.
set -euo pipefail
root="${1:?usage: mutate.sh <synthetic-root>}"
target="$root/evals/agentic/manifests/arms/graveyard.json"

if [ ! -f "$target" ]; then
  echo "mutate.sh: $target not found (evals/agentic/ not yet staged into the synthetic root)" >&2
  exit 1
fi

python3 - "$target" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, encoding="utf-8") as f:
    doc = json.load(f)

baseline = doc["baseline_arm"]
if "AdminOverride" in baseline["allowed_tools"]:
    print("mutate.sh: AdminOverride already present -- nothing to do", file=sys.stderr)
    sys.exit(1)
baseline["allowed_tools"] = baseline["allowed_tools"] + ["AdminOverride"]

with open(path, "w", encoding="utf-8") as f:
    json.dump(doc, f, indent=2, sort_keys=True)
PY

echo "mutate.sh: baseline_arm.allowed_tools in $target now carries an unmatched 'AdminOverride' entry"
