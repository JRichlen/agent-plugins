#!/usr/bin/env bash
# Strip every mention of the registered plugin's name out of README.md.
set -euo pipefail
root="${1:?usage: mutate.sh <synthetic-root>}"
readme="$root/README.md"
sed -i 's/sample-guard/renamed-elsewhere/g' "$readme"
