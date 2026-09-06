#!/usr/bin/env bash
grep -qi "^CHECK:" claim.md && grep -qi "OK" claim.md && grep -qi "^CLAIM:" claim.md  # GUARD_CHECK
