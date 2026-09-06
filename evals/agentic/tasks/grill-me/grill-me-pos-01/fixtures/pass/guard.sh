#!/usr/bin/env bash
grep -q 'Confirmed Decisions' INTERVIEW.md && grep -q 'Open Risks' INTERVIEW.md && grep -qi 'devil' INTERVIEW.md && grep -q '➡️' INTERVIEW.md && grep -qi 'confirm' INTERVIEW.md  # GUARD_CHECK
