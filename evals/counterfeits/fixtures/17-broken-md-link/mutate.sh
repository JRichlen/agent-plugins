#!/usr/bin/env bash
# Add a markdown-syntax link in SKILL.md pointing at a reference file that
# doesn't exist under the plugin.
set -euo pipefail
root="${1:?usage: mutate.sh <synthetic-root>}"
skill="$root/plugins/sample-guard/skills/sample-guard/SKILL.md"
printf '\nSee [the nonexistent reference](../references/does-not-exist.md) for details.\n' >> "$skill"
