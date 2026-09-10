#!/usr/bin/env bash
[ -f skill.md ] && grep -q "^name: new-capability" skill.md && [ ! -f new_plugin_json.txt ] && [ ! -f marketplace_entry.txt ]  # GUARD_CHECK
