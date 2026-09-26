#!/usr/bin/env bash
[ $(grep -c "^+[^+]" diff.patch) -eq 2 ] && [ ! -f findings.md ]  # GUARD_CHECK
