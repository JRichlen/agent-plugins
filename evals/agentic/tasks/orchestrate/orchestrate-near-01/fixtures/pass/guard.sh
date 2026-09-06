#!/usr/bin/env bash
[ -f evidence.md ] && [ ! -f dimensions.json ] && grep -qi "does not ship hooks" outcome.md  # GUARD_CHECK
