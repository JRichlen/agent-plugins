#!/usr/bin/env bash
grep -q "WATCHED" candidates.md && ! grep -q "PROMOTED" candidates.md && [ $(grep -c "cite:" candidates.md) -eq 2 ]  # GUARD_CHECK
