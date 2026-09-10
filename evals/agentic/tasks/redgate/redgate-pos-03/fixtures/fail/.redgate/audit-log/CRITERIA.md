# CRITERIA — audit-log

## #1 audit.log exists after the demo action runs
layers: artifacts
red-because: absent — the artifact does not exist yet
check_cmd: test -f artifacts/audit.log

## #2 audit.log records the demo action as a structured entry
layers: artifacts
red-because: absent — nothing produces this yet
check_cmd: grep -q 'action=demo' artifacts/audit.log

## #3 the log line is readable in a plain terminal
layers: taste
WITNESS: human confirms the audit.log line reads clearly, unquoted, in a terminal
