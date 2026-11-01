#!/usr/bin/env bash
sed 's/\bcnt\b/count/g' "${AGENTIC_INPUTS:-/inputs}/util.py" | cmp -s - util.py  # GUARD_CHECK
