#!/usr/bin/env bash
grep -qi MAJOR classification.md && grep -qi "tie-break" classification.md && [ -s ask.md ] && grep -qi "sign-off" outcome.md  # GUARD_CHECK
