#!/usr/bin/env bash
test -f status.md && grep -q '^owner:' status.md && grep -q '^size:' status.md && grep -q '^last_push:' status.md  # GUARD_CHECK
