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

# Repos we actually read this pass (have a gathered surface), by both identities.
# node_id is the identity the manifest and diff are joined on and is the one that
# survives a rename and refuses a REUSED name; full_name is mutable and is the
# legacy key, kept only so ledgers written before node_id existed still validate.
read_repos="$(jq -r '.context[]?.full_name' "$ctx" 2>/dev/null | sort -u)"
read_node_ids="$(jq -r '.context[]?.node_id // empty' "$ctx" 2>/dev/null | sort -u)"

# The gathered tree (newline-separated blob paths) for one repo, or empty.
tree_of() { jq -r --arg r "$1" '.context[]? | select(.full_name==$r) | .tree // ""' "$ctx" 2>/dev/null; }
tree_of_node() { jq -r --arg n "$1" '.context[]? | select(.node_id==$n) | .tree // ""' "$ctx" 2>/dev/null; }
name_of_node() { jq -r --arg n "$1" '.context[]? | select(.node_id==$n) | .full_name // ""' "$ctx" 2>/dev/null; }

violations=0
legacy_claims=0
while IFS= read -r claim; do
  [ -n "$claim" ] || continue
  repo="$(jq -r '.repo // ""' <<<"$claim")"
  path="$(jq -r '.path // ""' <<<"$claim")"
  node_id="$(jq -r '.node_id // ""' <<<"$claim")"
  # Manifest-level citations (no file surface) are always allowed.
  case "$path" in ""|"(manifest)"|manifest|HEAD|head) continue ;; esac
  # (1) A FILE-path citation requires that repo to have been read this pass.
  #     A claim that carries node_id is matched on node_id ONLY: it survives a
  #     rename, and a REUSED repo name carries a different node_id, so a stale
  #     citation cannot resolve to the wrong repository. That holds even when
  #     context.json has no node_ids at all — falling back to full_name there
  #     would let the reused name through, so the lookup simply fails closed.
  #     Only a claim that omits node_id (a legacy ledger) is matched on
  #     full_name, and the summary says so.
  if [ -n "$node_id" ]; then
    if [ -z "$read_node_ids" ] || ! grep -qxF "$node_id" <<<"$read_node_ids"; then
      echo "FABRICATED CITATION: claim cites ${repo}@…:${path} (node_id ${node_id}) but that repository was not read this pass (no such node_id in context.json). A renamed member keeps its node_id; a REUSED name does not." >&2
      violations=$((violations + 1))
      continue
    fi
    current_name="$(name_of_node "$node_id")"
    if [ -n "$current_name" ] && [ "$current_name" != "$repo" ]; then
      echo "note: ${repo} was renamed to ${current_name} since this claim was curated; the citation still resolves because it is keyed on node_id." >&2
    fi
    claim_tree="$(tree_of_node "$node_id")"
  else
    legacy_claims=$((legacy_claims + 1))
    if ! grep -qxF "$repo" <<<"$read_repos"; then
      echo "FABRICATED CITATION: claim cites ${repo}@…:${path} but ${repo} was not read this pass (absent from context.json). Removed/unread members may carry ONLY manifest-level citations." >&2
      violations=$((violations + 1))
      continue
    fi
    claim_tree="$(tree_of "$repo")"
  fi
  # (2) The cited PATH must actually be in that repo's gathered tree — closes the
  #     "cited a file that wasn't in the surface" gap: repo-was-read is necessary
  #     but not sufficient. (Semantic support of the claim by the file is the
  #     behavioral/verifier layer's job, not this deterministic gate.)
  if ! grep -qxF "$path" <<<"$claim_tree"; then
    echo "UNTRACEABLE CITATION: claim cites ${repo}:${path}, but that path is not in ${repo}'s gathered tree in context.json." >&2
    violations=$((violations + 1))
  fi
done < <(jq -c '.claims[]?' "$index")

if [ "$violations" -ne 0 ]; then
  echo "validate-citations: ${violations} non-traceable citation(s) — failing." >&2
  exit 1
fi
echo "validate-citations: all $(jq '.claims | length' "$index") citations traceable to a read surface or the manifest."
if [ "$legacy_claims" -ne 0 ]; then
  echo "validate-citations: ${legacy_claims} claim(s) carried no node_id and were matched on the MUTABLE full_name. Those citations survive neither a rename nor a name reuse; re-curate them to pick up node_id." >&2
fi
