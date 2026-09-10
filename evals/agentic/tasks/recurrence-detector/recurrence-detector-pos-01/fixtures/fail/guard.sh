#!/usr/bin/env bash
grep -q "PROMOTED" candidates.md && [ $(grep -c "cite:" candidates.md) -ge 3 ] && grep -qi "PROPOSAL ONLY" candidates.md  # GUARD_CHECK
