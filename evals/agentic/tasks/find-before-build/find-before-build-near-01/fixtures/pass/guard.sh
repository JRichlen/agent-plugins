#!/usr/bin/env bash
test -f RECEIPT.md && grep -qi 'legacy_retry' RECEIPT.md && grep -Eqi 'block|synchronous|event.loop' RECEIPT.md && test -f async_retry.py  # GUARD_CHECK
