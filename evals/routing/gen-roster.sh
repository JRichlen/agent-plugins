#!/usr/bin/env bash
#
# gen-roster.sh — emit the skill-routing roster the routing behavioral eval
# gives the model. One line per marketplace plugin: "name: <first sentence of
# its description>". Deterministic and sorted, so the cheap tier can assert
# roster.txt is in sync (a plugin added or re-described without regenerating
# the roster is a drift the routing eval would otherwise silently miss).
#
# Usage:  gen-roster.sh            # print roster to stdout
#         gen-roster.sh --check    # exit 1 if evals/routing/roster.txt is stale
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"

render() {
  python3 - "$ROOT" <<'PY'
import json, os, re, sys
root = sys.argv[1]
mkt = json.load(open(os.path.join(root, ".claude-plugin", "marketplace.json")))
for p in sorted(mkt["plugins"], key=lambda x: x["name"]):
    desc = " ".join((p.get("description") or "").split())
    # first sentence, capped — enough to route on, short enough to keep the
    # roster prompt lean across all 23 entries.
    first = re.split(r'(?<=[.:])\s', desc)[0] if desc else ""
    if len(first) > 200:
        first = first[:197].rstrip() + "..."
    print(f"{p['name']}: {first}")
PY
}

if [ "${1:-}" = "--check" ]; then
  cur="$HERE/roster.txt"
  if [ ! -f "$cur" ]; then echo "routing: roster.txt missing — run gen-roster.sh > roster.txt" >&2; exit 1; fi
  if ! diff -q <(render) "$cur" >/dev/null; then
    echo "routing: roster.txt is STALE — a plugin was added or re-described without regenerating it." >&2
    echo "         fix: evals/routing/gen-roster.sh > evals/routing/roster.txt" >&2
    exit 1
  fi
  echo "routing: roster.txt in sync"
  exit 0
fi
render
