#!/usr/bin/env bash
test -f QUESTIONS.md && grep -qi 'jwt' QUESTIONS.md && grep -qi 'api.key' QUESTIONS.md  # GUARD_CHECK
