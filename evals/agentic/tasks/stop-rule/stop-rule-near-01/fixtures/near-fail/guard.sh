#!/usr/bin/env bash
grep -qi "confirmed root cause" diagnosis.md && grep -qi "flag B" outcome.md  # GUARD_CHECK
