#!/usr/bin/env bash
# Add a FOURTH hook to the synthetic three-hook plugin tree T19's discovery
# test relies on. See DEFECT.md: this fixture is INERT until the integration
# lane stages evals/agentic/** into build_root() (contract §8.8) — the path
# below is where that staging will put it.
set -euo pipefail
root="${1:?usage: mutate.sh <synthetic-root>}"
tree="$root/evals/agentic/fixtures/protocols/plugins"

if [ ! -d "$tree" ]; then
  echo "mutate.sh 24-agentic-hardcoded-hooks: $tree does not exist yet -- " \
       "this fixture is inert until evals/counterfeits/run.sh stages evals/agentic/** " \
       "(see DEFECT.md)" >&2
  exit 1
fi

gamma="$tree/plugin-gamma/hooks"
mkdir -p "$gamma"

cat > "$gamma/hooks.json" <<'JSON'
{
  "description": "counterfeit mutation: a fourth hook a hardcoded/cached discovery would miss",
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {"type": "command", "command": "python3 ${CLAUDE_PLUGIN_ROOT}/hooks/handler.py"}
        ]
      }
    ]
  }
}
JSON

cat > "$gamma/handler.py" <<'PY'
#!/usr/bin/env python3
import json, sys
try:
    json.load(sys.stdin)
except Exception:
    pass
sys.exit(0)
PY
