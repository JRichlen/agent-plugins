#!/usr/bin/env bash
grep -q "Restore path:" rehearsal.md && grep -qi "0 differences" rehearsal.md && grep -qi "force-push proceeded" outcome.md  # GUARD_CHECK
