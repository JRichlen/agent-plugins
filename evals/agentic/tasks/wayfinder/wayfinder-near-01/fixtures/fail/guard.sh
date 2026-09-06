#!/usr/bin/env bash
grep -q "^T1$" frontier.md && ! grep -q "^T2$" frontier.md  # GUARD_CHECK
