#!/usr/bin/env bash
#
# evals/agentic/run.sh — thin wrapper around run.py (contract §9.2).
#
# Flags:
#   (none) / --offline   full offline suite + catalog + run manifest
#   --gate                root-portable subset (§9.3), terse, no manifest
#   --id T07               one catalog entry
#   --lane <lane>          one lane's catalog entries
#
# Prints "agentic: PASS" on a clean (none)/--offline run; on failure the
# frozen `agentic FAIL <lane>: <reason>` substrings (contract §8.8) are
# produced by run.py itself and passed through here verbatim, so the cheap
# tier's section 22 (which greps this script's combined output) sees them.
#
# No flag here ever spawns a model (contract §0.2, §9.2).
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

out="$(python3 "$HERE/run.py" "$@" 2>&1)"
code=$?

printf '%s\n' "$out"

if [ "$code" -eq 0 ]; then
  case " $* " in
    *" --gate "*|*" --id "*|*" --lane "*)
      : # terse subset/single-entry modes print their own status; no extra tail
      ;;
    *)
      echo "agentic: PASS"
      ;;
  esac
else
  if ! printf '%s\n' "$out" | grep -q 'agentic FAIL'; then
    echo "agentic FAIL run: run.py exited $code with no frozen FAIL substring (see output above)"
  fi
fi

exit "$code"
