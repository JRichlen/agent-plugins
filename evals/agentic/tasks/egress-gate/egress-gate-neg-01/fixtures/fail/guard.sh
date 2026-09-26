#!/usr/bin/env bash
test -f tests.py && grep -q 'def test_' tests.py && [ ! -f EGRESS_MANIFEST.md ]  # GUARD_CHECK
