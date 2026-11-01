#!/usr/bin/env bash
# Deprecated source-path adapter; no independent implementation.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../../.." && pwd)"
printf "Deprecated verification path; use plugins/verify-before-claim/skills/criteria-contract/scripts/scaffold-run.sh\n" >&2
exec bash "$ROOT/plugins/verify-before-claim/skills/criteria-contract/scripts/scaffold-run.sh" "$@"
