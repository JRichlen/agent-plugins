#!/usr/bin/env bash
python3 -c "import json,sys; d=json.load(open(\"dashboard.json\")); cards=d.get(\"cards\",[]); ok = len(cards)>=3 and all(c.get(\"owner\") and c.get(\"state\") for c in cards) and all(c.get(\"evidence\") for c in cards if c.get(\"state\")==\"verified\"); sys.exit(0 if ok else 1)"  # GUARD_CHECK
