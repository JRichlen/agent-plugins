#!/usr/bin/env bash
grep -q '_fmt_timestamp' utils/time.py && ! grep -q '_fmt_ts\b' utils/time.py  # GUARD_CHECK
