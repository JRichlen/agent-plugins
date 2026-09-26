#!/usr/bin/env bash
set -euo pipefail

root="$1"
target="$root/evals/redteam/corpus/adversarial/secret-exfil/001.txt"

if [[ ! -f "$target" ]]; then
  echo "27-redteam-corpus-drift: $target not staged -- inert until build_root() stages evals/redteam/** (see DEFECT.md)" >&2
  exit 0
fi

# Flip one byte, leaving corpus/manifest.json (also staged) untouched, so
# the drift is between the manifest's declared hash and the file's real one
# -- exactly what bin/freeze.py --check's clause 1 (design §5.3) exists to
# catch. Python for a portable single-byte flip (no dependence on a
# particular `xxd`/`printf` byte-editing idiom being present).
python3 - "$target" <<'PY'
import sys
p = sys.argv[1]
with open(p, "rb") as f:
    data = bytearray(f.read())
data[0] ^= 0xFF
with open(p, "wb") as f:
    f.write(data)
PY
