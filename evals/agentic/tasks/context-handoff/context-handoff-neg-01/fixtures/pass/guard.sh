#!/usr/bin/env bash
grep -q 'def _parse_header' work.py && grep -q 'return' work.py  # GUARD_CHECK
