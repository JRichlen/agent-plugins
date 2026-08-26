# CRITERIA — slice 3: hooks, the compile layer

<!-- Derived from approved plan slice 3: "hooks: the protocol compiles —
     deny writes to .redgate/** when the manifest says MIDDLE
     (reviewer-lockout + out-of-bounds-ledger, enforced rather than asked);
     SessionStart surfaces an unfinished run; portability caveat required." -->

## #1 hooks.json exists and is valid JSON declaring PreToolUse and SessionStart
layers: config
red-because: absent — no hooks directory exists
check_cmd: python3 -c "import json,sys; d=json.load(open('../../plugins/redgate/hooks/hooks.json'))['hooks']; sys.exit(0 if 'PreToolUse' in d and 'SessionStart' in d else 1)"

## #2 Both handlers exist and parse as bash
layers: script
red-because: absent — no handlers exist
check_cmd: bash -n ../../plugins/redgate/hooks/hooks-handlers/guard-redgate-paths.sh && bash -n ../../plugins/redgate/hooks/hooks-handlers/session-start.sh

## #3 The guard DENIES a write to a pinned run's CRITERIA.md during MIDDLE
layers: script, protocol
red-because: absent — nothing enforces the out-of-bounds ledger
check_cmd: R=../../plugins/redgate; d=$(mktemp -d); $R/skills/criteria-contract/scripts/scaffold-run.sh --slug t --root "$d" >/dev/null 2>&1; $R/skills/criteria-contract/scripts/scaffold-run.sh --pin t --root "$d" >/dev/null 2>&1; out=$(printf '{"tool_name":"Write","tool_input":{"file_path":"%s/.redgate/t/CRITERIA.md"}}' "$d" | $R/hooks/hooks-handlers/guard-redgate-paths.sh 2>&1); rc=$?; rm -rf "$d"; [ "$rc" -ne 0 ] && printf '%s' "$out" | grep -qi 'deny'

## #4 The guard ALLOWS the same write while the run is still in BEGIN
layers: script, protocol
red-because: absent — no phase awareness exists
check_cmd: R=../../plugins/redgate; d=$(mktemp -d); $R/skills/criteria-contract/scripts/scaffold-run.sh --slug t --root "$d" >/dev/null 2>&1; printf '{"tool_name":"Write","tool_input":{"file_path":"%s/.redgate/t/CRITERIA.md"}}' "$d" | $R/hooks/hooks-handlers/guard-redgate-paths.sh >/dev/null 2>&1; rc=$?; rm -rf "$d"; [ "$rc" -eq 0 ]

## #5 The guard is indifferent to paths outside .redgate/
layers: script
red-because: absent — nothing to be indifferent yet
check_cmd: R=../../plugins/redgate; printf '{"tool_name":"Write","tool_input":{"file_path":"/tmp/whatever.txt"}}' | $R/hooks/hooks-handlers/guard-redgate-paths.sh >/dev/null 2>&1

## #6 hooks prose carries a portability caveat (hooks are Claude-Code-only)
layers: prose
red-because: absent — no hooks prose exists
check_cmd: R=../../plugins/redgate; grep -rqi 'another harness\|harness-agnostic\|not a dependency' $R/hooks/
