#!/usr/bin/env bash
# oracle.sh <workspace> — apply the known-correct fixes WITHOUT a model. Used only by
# self-test.sh to prove verify.sh can pass (calibration ceiling); never by a benchmark arm.
set -euo pipefail
ws="${1:?workspace path}"
python3 - "$ws" <<'PY'
import sys, pathlib
ws = pathlib.Path(sys.argv[1])
def sub(path, old, new):
    p = ws / path; s = p.read_text(); assert old in s, (path, old); p.write_text(s.replace(old, new, 1))
sub("calc/stats.py", "sum(values) / (len(values) + 1)", "sum(values) / len(values)")
sub("calc/textutil.py", 'text = re.sub(r"[^A-Za-z0-9]+", "-", text)', 'text = re.sub(r"[^A-Za-z0-9]+", "-", text.lower())')
sub("calc/dates.py", "return (b - a).days", "return abs((b - a).days)")
PY
