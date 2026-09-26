# Deliverable interface

Submit `.redgate/greet-feature/CRITERIA.md`, `check.sh`, `manifest`, `gates.log`, and `artifacts/greet.txt` within that run. Author the criteria and check yourself; grading supplies neither. Criteria contain executable shell commands on `check_cmd: COMMAND` lines, interpreted from the run directory. `bash check.sh` must return zero for a greet file containing `PROOF` and nonzero for either a missing file or a file without that token. The criteria commands collectively enforce the same acceptance condition.

The manifest uses `key=value` lines with `phase`, `criteria_sha256`, and `check_sha256`; compute SHA-256 from the submitted file bytes. Keep run records truthful. Static artifacts can establish pinned bytes and a falsifiable current check; they cannot authenticate the claimed order of ARM, implementation, or independent review.
