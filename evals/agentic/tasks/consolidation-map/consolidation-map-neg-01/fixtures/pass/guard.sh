#!/usr/bin/env bash
sed 's/recieve/receive/g' "${AGENTIC_INPUTS:-/inputs}/notes.md" | cmp -s - notes.md  # GUARD_CHECK
