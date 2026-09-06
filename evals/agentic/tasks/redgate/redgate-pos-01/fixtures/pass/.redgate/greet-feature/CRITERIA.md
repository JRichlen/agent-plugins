# CRITERIA — greet-feature

## #1 greet.txt exists
layers: artifacts
red-because: absent — the artifact does not exist yet
check_cmd: test -f artifacts/greet.txt

## #2 greet.txt contains PROOF
layers: artifacts
red-because: absent — nothing produces this yet
check_cmd: grep -q PROOF artifacts/greet.txt
