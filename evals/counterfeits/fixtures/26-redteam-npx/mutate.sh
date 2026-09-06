#!/usr/bin/env bash
set -euo pipefail

root="$1"
target="$root/evals/redteam/run.sh"

if [[ ! -f "$target" ]]; then
  echo "26-redteam-npx: $target not staged -- inert until build_root() stages evals/redteam/** (see DEFECT.md)" >&2
  exit 0
fi

# Insert a REAL invocation (not a comment) right after the shebang line, so
# evals/redteam/run.sh's own bin/npxcheck.py gate is exercised against
# exactly the mutation shape counterfeit fixture 26 names in the contract.
sed -i '1a npx promptfoo@latest --version >/dev/null 2>&1 || true' "$target"
