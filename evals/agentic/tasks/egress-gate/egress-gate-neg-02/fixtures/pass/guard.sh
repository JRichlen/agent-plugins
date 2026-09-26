#!/usr/bin/env bash
test -f RENAME_LOG.txt && grep -q '_compute' RENAME_LOG.txt && [ ! -f EGRESS_MANIFEST.md ]  # GUARD_CHECK
