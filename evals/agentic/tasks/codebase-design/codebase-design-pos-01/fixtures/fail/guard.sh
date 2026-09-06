#!/usr/bin/env bash
[ -f docs/design-notes.md ] && [ "$(grep -c '^## Candidate' docs/design-notes.md)" -ge 3 ] && grep -qi 'seam' docs/design-notes.md && grep -q 'Chosen:' docs/design-notes.md && [ -f rate_limiter.py ]  # GUARD_CHECK
