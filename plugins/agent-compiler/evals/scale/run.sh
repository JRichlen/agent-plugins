#!/usr/bin/env bash
# Scale/stress tier for agent-compiler — see stress.py for what it proves.
# Offline, stdlib-only, isolated in temp dirs. Not part of the cheap tier
# (it takes minutes, not milliseconds); CI runs it via .github/workflows/scale.yml
# and it can always be run by hand:
#
#   plugins/agent-compiler/evals/scale/run.sh                      # defaults
#   plugins/agent-compiler/evals/scale/run.sh --sizes 40 --seeds 1 # quick pass
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/stress.py" "$@"
