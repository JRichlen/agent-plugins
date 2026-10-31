#!/usr/bin/env bash
grep -q "Restore path:" rehearsal.md && grep -qi "0 differences" rehearsal.md  # GUARD_CHECK
