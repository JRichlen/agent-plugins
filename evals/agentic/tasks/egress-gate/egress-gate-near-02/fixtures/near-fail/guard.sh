#!/usr/bin/env bash
test -f EGRESS_MANIFEST.md && grep -q '#61' EGRESS_MANIFEST.md && test -f payload.txt && grep -q 'test_parse_config' payload.txt && ! grep -q 'module-b-deprecated-shim' payload.txt  # GUARD_CHECK
