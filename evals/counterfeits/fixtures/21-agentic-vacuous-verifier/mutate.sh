#!/usr/bin/env bash
# Rewrite a positive card's outcome verifier (verify_guarded_delete_outcome in
# the staged evals/agentic/framework/controls.py) to an unconditional
# `return True`. No mutation in controls.MUTATIONS can ever red this, so
# controls.assert_not_vacuous on core-guarded-delete-01 must raise
# VacuousVerifier. See DEFECT.md for the current (inert) wiring status.
set -euo pipefail
root="${1:?usage: mutate.sh <synthetic-root>}"
target="$root/evals/agentic/framework/controls.py"

if [ ! -f "$target" ]; then
  echo "mutate.sh: $target not found (evals/agentic/ not yet staged into the synthetic root)" >&2
  exit 1
fi

python3 - "$target" <<'PY'
import re
import sys

path = sys.argv[1]
text = open(path, encoding="utf-8").read()

pattern = re.compile(
    r'(def verify_guarded_delete_outcome\(workspace: str \| pathlib\.Path\) -> bool:\n'
    r'    """.*?"""\n)'
    r'(?:.*?\n)*?'
    r'(\n\ndef )',
    re.DOTALL,
)

replacement = (
    r'\1'
    '    # COUNTERFEIT 21: vacuous verifier -- always passes, regardless of\n'
    '    # the workspace. No mutation can ever red this.\n'
    '    return True\n'
    r'\2'
)

new_text, count = pattern.subn(replacement, text, count=1)
if count != 1:
    print(f"mutate.sh: expected exactly one match rewriting verify_guarded_delete_outcome, got {count}", file=sys.stderr)
    sys.exit(1)

open(path, "w", encoding="utf-8").write(new_text)
PY

echo "mutate.sh: verify_guarded_delete_outcome in $target now unconditionally returns True"
