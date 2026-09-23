#!/usr/bin/env bash
# Validate a curated playbook's claim ledger against what was ACTUALLY READ this pass.
# Closes the "cited-but-fabricated" hole the simulation found: a citation can be
# syntactically valid (has a sha + a path) yet name a file that was never provided —
# most dangerously for a REMOVED member, which is never read. No LLM. Deterministic.
#
# Rule: a claim whose `path` names a FILE (anything but a manifest-level sentinel)
# is valid ONLY if its `repo` appears in context.json's read surfaces. Removed members
# are never read, so any FILE citation on a removed repo is a violation by construction.
#
# Usage: validate-citations.sh <index.json> <diff.json> <context.json>
# Exit 0 = every citation traceable; exit 1 = one or more fabricated/non-traceable.
set -euo pipefail

index="${1:?usage: validate-citations.sh <index.json> <diff.json> <context.json>}"
ctx="${3:?usage: validate-citations.sh <index.json> <diff.json> <context.json>}"
for f in "$index" "$ctx"; do [ -f "$f" ] || { echo "validate-citations: no such file: $f" >&2; exit 2; }; done

# Repos we actually read this pass (have a gathered surface).
read_repos="$(jq -r '.context[]?.full_name' "$ctx" 2>/dev/null | sort -u)"

# The gathered tree (newline-separated blob paths) for one repo, or empty.
tree_of() { jq -r --arg r "$1" '.context[]? | select(.full_name==$r) | .tree // ""' "$ctx" 2>/dev/null; }

violations=0
while IFS= read -r claim; do
  [ -n "$claim" ] || continue
  repo="$(jq -r '.repo // ""' <<<"$claim")"
  path="$(jq -r '.path // ""' <<<"$claim")"
  # Manifest-level citations (no file surface) are always allowed.
  case "$path" in ""|"(manifest)"|manifest|HEAD|head) continue ;; esac
  # (1) A FILE-path citation requires that repo to have been read this pass.
  if ! grep -qxF "$repo" <<<"$read_repos"; then
    echo "FABRICATED CITATION: claim cites ${repo}@…:${path} but ${repo} was not read this pass (absent from context.json). Removed/unread members may carry ONLY manifest-level citations." >&2
    violations=$((violations + 1))
    continue
  fi
  # (2) The cited PATH must actually be in that repo's gathered tree — closes the
  #     "cited a file that wasn't in the surface" gap: repo-was-read is necessary
  #     but not sufficient. (Semantic support of the claim by the file is the
  #     behavioral/verifier layer's job, not this deterministic gate.)
  if ! tree_of "$repo" | grep -qxF "$path"; then
    echo "UNTRACEABLE CITATION: claim cites ${repo}:${path}, but that path is not in ${repo}'s gathered tree in context.json." >&2
    violations=$((violations + 1))
  fi
done < <(jq -c '.claims[]?' "$index")

if [ "$violations" -ne 0 ]; then
  echo "validate-citations: ${violations} non-traceable citation(s) — failing." >&2
  exit 1
fi
echo "validate-citations: all $(jq '.claims | length' "$index") citations traceable to a read surface or the manifest."
