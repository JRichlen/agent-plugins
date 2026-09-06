#!/usr/bin/env bash
test -f hypotheses.md && grep -q 'Falsifying test' hypotheses.md && grep -qE '^1\.' hypotheses.md && test -f test_parse_duration.py && grep -q 'def test_' test_parse_duration.py && ! grep -rq --include='*.py' 'DBGRM:' .  # GUARD_CHECK
