#!/usr/bin/env bash
set -u
compiler="$AGENTIC_REPO_ROOT/plugins/agent-compiler/scripts/compile.py"
registry="$AGENTIC_REPO_ROOT/plugins/agent-compiler/registry"
out="$(mktemp)"
out_log="$(mktemp)"
if [ ! -f query.json ]; then rm -f "$out" "$out_log"; exit 1; fi
if ! python3 "$compiler" compile --registry "$registry" --query query.json --out "$out" >"$out_log" 2>&1; then rm -f "$out" "$out_log"; exit 1; fi
hash="$(python3 -I -c "import json;print(json.load(open('$out'))['hash'])")"
rm -f "$out" "$out_log"
[ -f rendered.md ] || exit 1
[ -f persona.md ] && exit 1
grep -q "imageHash: $hash" rendered.md
