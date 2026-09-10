#!/usr/bin/env bash
# Delete the staged evals/agentic/run.sh entirely. See DEFECT.md.
set -euo pipefail
root="${1:?usage: mutate.sh <synthetic-root>}"
target="$root/evals/agentic/run.sh"

if [ ! -f "$target" ]; then
  echo "mutate.sh: $target not found (evals/agentic/ not staged into the synthetic root)" >&2
  exit 1
fi

rm -f "$target"
echo "mutate.sh: removed $target"
