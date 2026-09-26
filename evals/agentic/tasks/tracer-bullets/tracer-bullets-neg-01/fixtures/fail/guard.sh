#!/usr/bin/env bash
grep -qi "^Answer:" answer.md && [ ! -f slice.md ]  # GUARD_CHECK
