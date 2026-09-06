#!/usr/bin/env bash
[ $(grep -c "^+[^+]" diff.patch) -eq 1 ] && grep -qi "stale TODO" findings.md && grep -qi "dead code" findings.md  # GUARD_CHECK
