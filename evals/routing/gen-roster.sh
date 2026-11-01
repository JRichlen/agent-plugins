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
entries = {p["name"]: p for p in mkt["plugins"]}
# Public service entry points can share a distribution with an inline method.
# The canonical ownership index supplies identity/path/role, not a second router.
index_path = os.path.join(root, "core", "ownership.json")
if os.path.isfile(index_path):
    index = json.load(open(index_path, encoding="utf-8"))
    for service in index["services"]:
        name = service["entrypoint"]
        if name in entries:
            continue
        if service["owner"] not in entries:
            raise ValueError("service owner is not registered: " + service["owner"])
        source = os.path.realpath(os.path.join(root, service["source"]))
        if os.path.commonpath([os.path.realpath(root), source]) != os.path.realpath(root):
            raise ValueError("service source escapes repository")
        body = open(source, encoding="utf-8").read()
        front = body.split("---", 2)[1]
        lines = front.splitlines()
        description = None
        for offset, line in enumerate(lines):
            if not line.startswith("description:"):
                continue
            value = line.split(":", 1)[1].strip()
            if value in (">", ">-", "|", "|-"):
                parts = []
                for continuation in lines[offset + 1:]:
                    if continuation and not continuation[0].isspace():
                        break
                    parts.append(continuation.strip())
                description = " ".join(parts)
            else:
                description = value.strip("\"'")
            break
        if not description:
            raise ValueError("service has no routing description: " + name)
        entries[name] = {"name": name, "description": description}
for p in sorted(entries.values(), key=lambda x: x["name"]):
    desc = " ".join((p.get("description") or "").split())
    # first sentence, capped — enough to route on, short enough to keep the
    # roster prompt lean across every entry.
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
