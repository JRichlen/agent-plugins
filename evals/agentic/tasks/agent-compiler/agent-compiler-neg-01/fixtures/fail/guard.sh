#!/usr/bin/env bash
grep -q 'receive' NOTES.md && ! grep -q 'recieve' NOTES.md  # GUARD_CHECK
