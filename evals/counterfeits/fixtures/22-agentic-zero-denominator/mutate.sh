#!/usr/bin/env bash
set -euo pipefail

root="$1"
target="$root/evals/agentic/framework/analysis.py"

if [ ! -f "$target" ]; then
  echo "22-agentic-zero-denominator: $target not found -- build_root() must stage" \
       "evals/agentic before this fixture can mutate it (contract §8.8); this" \
       "fixture is inert until the integration lane wires that staging" >&2
  exit 1
fi

# Rate.render's zero-denominator branch:
#     if self.value is None:
#         return f"unavailable ({self.unavailable_reason})"
# becomes a banned numeric rendering, exactly the failure mode T38 exists to
# catch (benchmark-spec §7): a card with no valid samples must never print
# 0%, which reads as "the plugin failed" rather than "nothing was measured".
python3 - "$target" <<'PY'
import sys

path = sys.argv[1]
text = open(path, "r", encoding="utf-8").read()
needle = 'return f"unavailable ({self.unavailable_reason})"'
replacement = 'return "0%"  # MUTATED by 22-agentic-zero-denominator'

count = text.count(needle)
if count == 0:
    raise SystemExit(
        f"22-agentic-zero-denominator: mutate.sh target string not found in {path} "
        "-- Rate.render's source changed shape; update this fixture"
    )

text = text.replace(needle, replacement)
with open(path, "w", encoding="utf-8") as f:
    f.write(text)
PY
