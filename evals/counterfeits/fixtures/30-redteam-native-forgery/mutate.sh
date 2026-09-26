#!/usr/bin/env bash
set -euo pipefail

root="$1"
target="$root/evals/redteam/fixtures/ledgers/disagreement-rubric-vs-effect.json"

if [[ ! -f "$target" ]]; then
  echo "30-redteam-native-forgery: $target not staged -- inert until build_root() stages evals/redteam/** (see DEFECT.md)" >&2
  exit 0
fi

# This fixture's row is legitimately provenance='simulated' (this lane's
# providers hard-code that value; design §9). Flip it to 'native' -- a bare
# claim with no backing adapters.LedgerReader -- and bin/verdict.py's
# qualify() must refuse with the SPECIFIC forgery message, not just its
# generic "no host ledger" one:
# test_native_proof_required_before_any_safety_qualification (T47,
# evals.agentic.tests.test_redteam_design) asserts the message contains
# "no verifiable host ledger" for THIS fixture when unmutated; once mutated,
# that assertion fails because qualify() now (correctly) raises the
# forgery-specific message instead -- and unittest's own assertIn failure
# report prints the actual (mutated) message verbatim, which is what
# carries this fixture's EXPECT_FAIL_SUBSTRING into the tool's output.
python3 - "$target" <<'PY'
import json
import sys

p = sys.argv[1]
with open(p) as f:
    data = json.load(f)
for row in data["results"]:
    row["response"]["metadata"]["provenance"] = "native"
with open(p, "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
PY
