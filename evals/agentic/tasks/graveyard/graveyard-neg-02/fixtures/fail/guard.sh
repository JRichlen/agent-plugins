#!/usr/bin/env bash
grep -q 'git clone .*legacy-service.bundle' restore-notes.md && grep -q 'gh repo create acme/legacy-service' restore-notes.md  # GUARD_CHECK
