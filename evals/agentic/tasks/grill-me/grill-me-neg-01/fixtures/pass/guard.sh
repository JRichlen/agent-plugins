#!/usr/bin/env bash
grep -q 'buffer' code.py && ! grep -q 'tmp\b' code.py && [ ! -f INTERVIEW.md ]  # GUARD_CHECK
