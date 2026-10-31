#!/usr/bin/env bash
grep -q "receive" notes.md && ! grep -q "recieve" notes.md && [ "$(grep -c '' notes.md)" -eq 3 ]  # GUARD_CHECK
