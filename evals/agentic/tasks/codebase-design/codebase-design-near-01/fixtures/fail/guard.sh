#!/usr/bin/env bash
[ -f docs/design-notes.md ] && [ "$(grep -c '^## Candidate' docs/design-notes.md)" -ge 3 ] && grep -q 'Chosen:' docs/design-notes.md  # GUARD_CHECK
