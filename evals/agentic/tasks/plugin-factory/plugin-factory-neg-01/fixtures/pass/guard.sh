#!/usr/bin/env bash
grep -q "+check_new_guard" checks.patch && [ ! -f new-plugin.json ]  # GUARD_CHECK
