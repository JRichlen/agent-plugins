#!/usr/bin/env bash
python3 -c "import sys; t=open(\"response.md\").read().lower(); bad=[p for p in [\"not just that\", \"delve\", \"leverage\", \"ensuring seamless\", \"fast-paced world\"] if p in t]; ok = t.strip().startswith(\"verdict:\"); sys.exit(0 if (ok and not bad) else 1)"  # GUARD_CHECK
