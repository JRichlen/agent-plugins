#!/usr/bin/env bash
test -f RECEIPT.md && [ "$(grep -c '^- Searched' RECEIPT.md)" -ge 2 ] && grep -q 'utils/retry.py' RECEIPT.md && grep -Eq 'from utils\.retry import|import utils\.retry' client.py && ! grep -qi 'def retry' client.py  # GUARD_CHECK
