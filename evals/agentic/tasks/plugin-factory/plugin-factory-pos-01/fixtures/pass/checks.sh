#!/usr/bin/env bash
set -eu
python3 -I - "$1" <<'PY_CHECK'
import json,pathlib,re,sys
root=pathlib.Path(sys.argv[1])
try:
    plugin=json.loads((root/'plugin.json').read_text())
    entry=json.loads((root/'marketplace-entry.json').read_text())
    valid=(plugin.get('name')=='demo-widget'
           and re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+',plugin.get('version',''))
           and entry.get('name')=='demo-widget'
           and entry.get('source')=='./plugins/demo-widget')
except (OSError,ValueError,TypeError):
    valid=False
raise SystemExit(0 if valid else 1)
PY_CHECK
