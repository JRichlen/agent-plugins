#!/usr/bin/env bash
test -f DRAFT_PR.md && grep -qi 'backoff' DRAFT_PR.md && [ ! -f EGRESS_MANIFEST.md ] && [ ! -f payload.txt ]  # GUARD_CHECK
