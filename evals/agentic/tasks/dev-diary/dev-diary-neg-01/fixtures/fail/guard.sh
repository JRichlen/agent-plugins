#!/usr/bin/env bash
test -f status-report.md && grep -qi 'sprint' status-report.md && [ ! -d entries ]  # GUARD_CHECK
