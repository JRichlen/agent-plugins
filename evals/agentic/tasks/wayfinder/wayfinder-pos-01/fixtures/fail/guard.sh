#!/usr/bin/env bash
python3 -c "import json;d=json.load(open('tickets.json'));assert all('type' in t and 'depends_on' in t for t in d)" && grep -qi "T1" frontier.md && ! grep -qi "T2" frontier.md  # GUARD_CHECK
