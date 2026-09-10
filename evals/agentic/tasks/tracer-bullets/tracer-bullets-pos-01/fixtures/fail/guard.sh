#!/usr/bin/env bash
grep -qi "KEEP" slice.md && grep -qi "end-to-end" slice.md && grep -qi UI slice.md && grep -qi API slice.md && grep -qi DB slice.md  # GUARD_CHECK
