#!/usr/bin/env bash
grep -qi MAJOR classification.md && [ -s ask.md ] && grep -qi "sign-off" outcome.md && grep -qi disabled outcome.md  # GUARD_CHECK
