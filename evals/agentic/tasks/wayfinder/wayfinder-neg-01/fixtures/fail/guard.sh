#!/usr/bin/env bash
[ $(grep -c "^- " todo.md) -eq 3 ] && [ ! -f tickets.json ]  # GUARD_CHECK
