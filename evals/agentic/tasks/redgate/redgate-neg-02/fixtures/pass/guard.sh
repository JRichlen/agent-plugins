#!/usr/bin/env bash
grep -q 'raw_input' artifacts/loader.py && ! grep -qw tmp artifacts/loader.py  # GUARD_CHECK
