# CRITERIA — notify-service

## #1 notify.py defines send
layers: artifacts
red-because: absent — the artifact does not exist yet
check_cmd: grep -q 'def send' artifacts/notify.py

## #2 send() writes the message to sent.log
layers: artifacts
red-because: absent — nothing produces this yet
check_cmd: grep -q 'sent.log' artifacts/notify.py
