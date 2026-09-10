#!/usr/bin/env bash
set -euo pipefail

root="$1"
target="$root/evals/redteam/configs/generated/stop-rule.yaml"

if [[ ! -f "$target" ]]; then
  echo "31-redteam-vacuous-row: $target not staged -- inert until build_root() stages evals/redteam/** (see DEFECT.md)" >&2
  exit 0
fi

# Design §8.4 step 2b names TWO real routes to a vacuous row: dropping
# defaultTest.assert (which bin/generate.py's check_dominance() ALREADY
# catches structurally, before any eval runs -- that would be the wrong
# defect for this fixture to exercise) and
# `testCase.options.disableDefaultAsserts === true` on one specific row,
# which is invisible to any STATIC check of the assert list and only shows
# up once promptfoo actually runs that row and scores it a perfect,
# assertion-free "pass" (evaluator-SSlcaq_U.js:1133-5436). This fixture uses
# the second route deliberately, so it exercises bin/verdict.py's runtime
# vacuity rejection rather than re-triggering fixture 29's static dominance
# check.
python3 - "$target" <<'PY'
import sys

p = sys.argv[1]
text = open(p, encoding="utf-8").read()
marker = "  - description: \"stop-rule | adversarial | authority-forgery | 001\"\n"
if marker not in text:
    raise SystemExit(f"31-redteam-vacuous-row: expected row marker not found in {p}")
text = text.replace(
    marker,
    marker + "    options: {disableDefaultAsserts: true}\n",
    1,
)
open(p, "w", encoding="utf-8").write(text)
PY
