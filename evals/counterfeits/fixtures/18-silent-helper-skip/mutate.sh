#!/usr/bin/env bash
# Append one assertion to the baseline plugin's cheap pack that calls a helper
# no runner defines. The pack still parses and every other check still passes;
# only the fail-closed pack guard can catch it. Before #120 this was a silent
# no-op that still reported green.
set -euo pipefail
root="${1:?usage: mutate.sh <synthetic-root>}"
pack="$root/plugins/sample-guard/evals/cheap/checks.sh"

cat >> "$pack" <<'OUTER'

# A check that cannot run. `hasNot` is defined by no runner and by no pack, so
# this line is a "command not found" that execution would otherwise sail past —
# leaving the tier green over an assertion that never executed.
hasNot "$PLUGIN_DIR/scripts/emit.sh" "rm -rf" "guard present" "guard MISSING"
OUTER
