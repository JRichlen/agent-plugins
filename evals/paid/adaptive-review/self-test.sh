#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
COMPILER="$ROOT/plugins/agent-compiler/scripts/compile.py"
RENDERER="$ROOT/plugins/agent-compiler/scripts/render_claude_agent.py"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

for arm in baseline candidate; do
  python3 "$COMPILER" compile \
    --registry "$HERE/registry" \
    --query "$HERE/queries/$arm.json" \
    --out "$tmp/$arm.image.json"
  diff -u "$HERE/compiled/$arm.image.json" "$tmp/$arm.image.json"
  python3 "$RENDERER" --image "$tmp/$arm.image.json" --out "$tmp/$arm.md"
  diff -u "$HERE/compiled/$arm.md" "$tmp/$arm.md"
done

(cd "$HERE" && sha256sum -c corpus.sha256)
python3 "$HERE/evaluate.py" --self-test
python3 - "$HERE/status.json" <<'PY'
import json, sys
status = json.load(open(sys.argv[1], encoding="utf-8"))
assert status["outcome"] == "inconclusive"
assert status["advance"] is False
assert status["evidence"] == "not-run"
PY
