#!/usr/bin/env bash
python3 -c "import json;d=json.load(open('plugin.json'));assert d['name']=='demo-widget'" && grep -q demo-widget marketplace-entry.json && grep -q "exit 1" checks.sh && [ -s invariant.md ]  # GUARD_CHECK
