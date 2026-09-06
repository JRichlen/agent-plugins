# CRITERIA — user-criteria

## #1 auth-helper.py exists
layers: artifacts
red-because: absent — the artifact does not exist yet
check_cmd: test -f artifacts/auth-helper.py

## #2 auth-helper.py defines verify_token
layers: artifacts
red-because: absent — nothing produces this yet
check_cmd: grep -q 'def verify_token' artifacts/auth-helper.py
