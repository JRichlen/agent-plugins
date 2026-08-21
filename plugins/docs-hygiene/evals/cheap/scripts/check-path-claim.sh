#!/usr/bin/env bash
#
# check-path-claim.sh — deterministic stand-in for the path-tier of
# docs-hygiene's staleness-detection heuristic ("does the named file/directory
# exist, right now, at that exact path? One ls/rg/find call.").
#
# Given a claim file containing one backticked path and a repo root to check
# it against, report whether the claimed path currently resolves. This is the
# literal mechanical check the SKILL.md's inline heuristic and
# references/refactoring-workflow.md's "path-tier — auto-resolvable" worked
# example both describe — used here so the cheap eval can assert real,
# executable behavior instead of only grepping the plugin's own prose.
#
# Usage:   check-path-claim.sh <claim-file> <repo-root>
# Prints:  "CURRENT: <path>"  and exits 0  if the claimed path exists
#          "STALE: <path>"    and exits 1  if the claimed path does not exist
#          "NO-CLAIM"         and exits 2  if the claim file has no backticked path
set -euo pipefail

claim_file="${1:?usage: check-path-claim.sh <claim-file> <repo-root>}"
repo_root="${2:?usage: check-path-claim.sh <claim-file> <repo-root>}"

# Pick the first backticked token that looks like a path (contains a "/") —
# a fixture's own prose may legitimately backtick other short tokens (a
# filename, a command name) before the actual claimed path appears.
path="$(grep -oE '`[^`]+`' "$claim_file" | tr -d '`' | grep '/' | head -1)"

if [ -z "$path" ]; then
  echo "NO-CLAIM"
  exit 2
fi

if [ -e "$repo_root/$path" ]; then
  echo "CURRENT: $path"
  exit 0
else
  echo "STALE: $path"
  exit 1
fi
