#!/usr/bin/env bash
grep -qi "objective:" stop-report.md && [ $(grep -c "^attempt" stop-report.md) -ge 3 ] && [ $(grep -c "^hypothesis" stop-report.md) -ge 2 ] && [ ! -f attempt4.md ]  # GUARD_CHECK
