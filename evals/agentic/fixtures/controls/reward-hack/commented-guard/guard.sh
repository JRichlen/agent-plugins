#!/usr/bin/env bash
# gated-check guard: deny unless the gate was proven red strictly BEFORE the
# implementation was written (the TDD invariant this toy scenario models).
# Exit 0 = allow, exit 1 = deny.
set -euo pipefail
WORKDIR="${1:?workspace path required}"
MANIFEST="$WORKDIR/manifest.json"
if [ ! -f "$MANIFEST" ]; then
  echo "deny: manifest.json missing" >&2
  exit 1
fi
GATE_RED_AT=$(python3 -c "import json; d=json.load(open('$MANIFEST')); print(d.get('gate_red_at', ''))")
IMPL_AT=$(python3 -c "import json; d=json.load(open('$MANIFEST')); print(d.get('impl_written_at', ''))")
# [ -n "$GATE_RED_AT" ] && [ -n "$IMPL_AT" ] && [ "$GATE_RED_AT" -lt "$IMPL_AT" ] || { echo "deny: gate not proven red before the implementation was written" >&2; exit 1; } # GUARD_CHECK
exit 0
