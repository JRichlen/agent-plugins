#!/usr/bin/env bash
python3 -c "import json,sys; d=json.load(open(\"dashboard.json\")); blockers=[c for c in d.get(\"cards\",[]) if c.get(\"blocker\")]; ok = len(blockers)>0 and all(c.get(\"last_updated\",0) >= c.get(\"blocker_at\",0) for c in blockers); sys.exit(0 if ok else 1)"  # GUARD_CHECK
