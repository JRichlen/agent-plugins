#!/usr/bin/env bash
grep -q REFUTED evidence.md && grep -qi "^Recommendation: Redis" outcome.md  # GUARD_CHECK
