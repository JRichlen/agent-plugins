#!/usr/bin/env bash
sed 's/adress/address/g' "${AGENTIC_INPUTS:-/inputs}/notes.md" | cmp -s - notes.md  # GUARD_CHECK
