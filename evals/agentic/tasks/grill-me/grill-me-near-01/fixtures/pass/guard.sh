#!/usr/bin/env bash
test -f INTERVIEW.md && grep -q '➡️' INTERVIEW.md && ! grep -qi 'devil' INTERVIEW.md  # GUARD_CHECK
