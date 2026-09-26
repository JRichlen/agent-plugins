#!/usr/bin/env bash
test -s commit-message.txt && ! grep -q '^Verdict:' commit-message.txt  # GUARD_CHECK
