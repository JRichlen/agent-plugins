#!/usr/bin/env bash
set -euo pipefail

root="$1"
target="$root/evals/redteam/run.sh"

if [[ ! -f "$target" ]]; then
  echo "26-redteam-npx: $target not staged -- inert until build_root() stages evals/redteam/** (see DEFECT.md)" >&2
  exit 0
fi

# Insert a REAL invocation shape (not a comment) right after the shebang line,
# so evals/redteam/run.sh's own bin/npxcheck.py gate is exercised against
# exactly the mutation shape counterfeit fixture 26 names in the contract.
#
# It is wrapped in a shell function that is never called, so the mutated
# script can NEVER execute it. The first version of this fixture inserted a
# bare `npx promptfoo@latest --version` statement; when the staged copy ran,
# that statement executed BEFORE the gate's own grep and reached the network,
# upgrading the host's shared npx cache from 0.122.0 to 0.122.2 (2026-09-06).
# A counterfeit mutation must be detectable, never executable.
sed -i '1a _counterfeit_26_never_called() { npx promptfoo@latest --version >/dev/null 2>&1 || true; }' "$target"
