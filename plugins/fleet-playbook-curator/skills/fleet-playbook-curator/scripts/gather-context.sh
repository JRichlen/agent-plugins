#!/usr/bin/env bash
# Bundle curation context for ONLY the changed members. No LLM. Portable bash/gh/jq.
#
# Usage: gather-context.sh <diff.json> [prev_manifest.json]
# For each added/renamed/updated member in the diff, collects the cheap, high-signal
# surface a curator needs to route: README (head), the top-level tree, workflow
# trigger lines, and the commit log since the last curated sha. Emits a JSON bundle
# to stdout. Intentionally skips 'removed' members (nothing to read) but lists them
# so the curator can prune their playbook entries.
set -euo pipefail

diff="${1:?usage: gather-context.sh <diff.json> [prev_manifest.json]}"
[ -f "$diff" ] || { echo "gather-context: no such file: $diff" >&2; exit 2; }

touched="$(jq -r '[.added[]?, .renamed[]?, .updated[]?]
  | map(.full_name // .to) | unique | .[]' "$diff")"

bundle='[]'
while read -r full; do
  [ -n "$full" ] || continue
  readme="$(gh api "repos/${full}/readme" --jq '.content' 2>/dev/null | base64 -d 2>/dev/null | head -c 4000 || true)"
  # Recursive so EVERY path a curator might cite is captured — validate-citations.sh
  # rejects a file citation whose path is not present in this tree.
  tree="$(gh api "repos/${full}/git/trees/HEAD?recursive=1" --jq '[.tree[] | select(.type=="blob") | .path] | join("\n")' 2>/dev/null || true)"
  workflows="$(gh api "repos/${full}/contents/.github/workflows" --jq '[.[].name] | join(", ")' 2>/dev/null || true)"
  from_sha="$(jq -r --arg f "$full" '(.updated[]? | select(.full_name==$f) | .from) // ""' "$diff")"
  log="$( [ -n "$from_sha" ] && gh api "repos/${full}/commits?per_page=20" \
            --jq '[.[].commit.message | split("\n")[0]] | join("\n")' 2>/dev/null || true )"
  bundle="$(jq --arg full "$full" --arg readme "$readme" --arg tree "$tree" \
              --arg wf "$workflows" --arg log "$log" \
    '. + [{full_name:$full, readme_head:$readme, tree:$tree, workflows:$wf, recent_commits:$log}]' <<<"$bundle")"
done <<<"$touched"

# Removed members are emitted manifest-only with an explicit content_available:false
# marker — the curator may state their removal but must NOT make any content claim
# about them (they were not read this pass). The marker makes that contract
# machine-evident rather than implied by absence.
jq -n --argjson bundle "$bundle" --slurpfile d "$diff" \
  '{ removed: (($d[0].removed // []) | map(. + {content_available: false})), context: $bundle }'
