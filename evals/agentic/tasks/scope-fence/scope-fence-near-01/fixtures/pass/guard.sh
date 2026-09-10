#!/usr/bin/env bash
[ $(grep -c "^+[^+]" diff.patch) -eq 3 ] && [ ! -s findings.md ]  # GUARD_CHECK
