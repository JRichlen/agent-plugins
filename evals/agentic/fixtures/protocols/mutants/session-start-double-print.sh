#!/usr/bin/env bash
# Mutant of voice's session-start.sh: prints the SAME JSON object twice.
#
# Negative control for T22: "A handler that emits ... two JSON objects ...
# breaks the harness contract while looking fine to a human reader." Proves
# run_hook()'s single-JSON-object parsing is not vacuous: this mutant's
# stdout must fail to parse as exactly one JSON object.
set -u
for _i in 1 2; do
cat <<'JSON'
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "duplicated on purpose"
  }
}
JSON
done
exit 0
