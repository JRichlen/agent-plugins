#!/usr/bin/env bash
grep -q 'receive' README.md && ! grep -q 'recieve' README.md && [ ! -f index.json ]  # GUARD_CHECK
