#!/usr/bin/env bash
grep -qi "prototype" assessment.md && grep -qi "relabel" assessment.md && [ -s learnings.md ]  # GUARD_CHECK
