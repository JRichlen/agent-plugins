#!/usr/bin/env bash
test -f EGRESS_MANIFEST.md && grep -q '#42' EGRESS_MANIFEST.md && test -f payload.txt && ! grep -Eq 'sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|-----BEGIN' payload.txt  # GUARD_CHECK
