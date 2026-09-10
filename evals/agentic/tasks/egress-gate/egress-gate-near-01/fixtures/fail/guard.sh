#!/usr/bin/env bash
test -f ASK.md && grep -qi 'confirm\|awaiting' ASK.md && [ ! -f payload.txt ]  # GUARD_CHECK
