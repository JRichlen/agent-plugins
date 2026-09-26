# CRITERIA — config-validator

## #1 config.py exists
layers: artifacts
red-because: absent — the artifact does not exist yet
check_cmd: test -f artifacts/config.py

## #2 config.py defines validate_config
layers: artifacts
red-because: absent — nothing produces this yet
check_cmd: grep -q 'def validate_config' artifacts/config.py

## #3 validate_config raises KeyError when the required 'name' key is missing
layers: artifacts
red-because: absent — nothing raises on the missing key yet
check_cmd: grep -q 'raise KeyError' artifacts/config.py
