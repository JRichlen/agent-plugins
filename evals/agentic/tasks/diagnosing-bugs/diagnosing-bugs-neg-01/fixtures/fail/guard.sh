#!/usr/bin/env bash
grep -q 'color: green' style.css && [ ! -f hypotheses.md ]  # GUARD_CHECK
