#!/usr/bin/env bash
# setup.sh <workspace> — stage a fresh copy of the task fixture into <workspace>.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ws="${1:?workspace path}"
mkdir -p "$ws"
cp -R "$here/fixture/." "$ws/"
# Record the tests' digests so verify.sh can prove they were not edited (reward-hack guard).
( cd "$ws" && find tests -type f -name '*.py' -print0 | sort -z | xargs -0 sha256sum ) > "$ws/.tests.sha256"
