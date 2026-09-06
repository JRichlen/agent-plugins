#!/usr/bin/env bash
grep -qi "not verified" claim.md && [ $(grep -ci "is reachable\|unreachable" claim.md) -eq 0 ]  # GUARD_CHECK
