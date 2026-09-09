#!/usr/bin/env bash
#
# run-one.sh <plugin-name> — run ONE registered plugin's cheap eval pack in
# isolation, outside the full repo-wide sweep.
#
# The always-on `cheap` job (evals/cheap/run.sh) already runs the generic
# sections 1-9 for the whole repo AND loops every plugin's pack in section 10.
# This wrapper exists for the per-plugin `install` matrix (see .github/workflows/
# evals.yml): each leg smoke-tests one plugin's install surface and then runs
# THAT plugin's own evals standalone, so a failure is attributed to a single
# plugin without re-running the entire repo sweep.
#
# It replicates run.sh section 10's sourcing contract exactly: resolve the
# plugin's source from marketplace.json, export PLUGIN_NAME / PLUGIN_DIR, source
# the SAME evals/cheap/helpers.sh run.sh does (so both runners offer an identical
# helper set — see #120, where this file defined three of six and packs silently
# skipped every check using the other three), cd to the repo root, and dot-source
# plugins/<source>/evals/cheap/checks.sh. Discovery FAILS CLOSED: a
# registered plugin with no pack is a failure, never a silent skip — identical to
# run.sh's philosophy.
#
# Exit 0 = the plugin's pack passed. Exit 1 = missing pack or a failed check.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

PLUGIN_NAME="${1:-}"
if [ -z "$PLUGIN_NAME" ]; then
  echo "usage: evals/cheap/run-one.sh <plugin-name>" >&2
  exit 2
fi

# Resolve the plugin's source directory straight from the marketplace lockfile,
# using the same enumeration run.sh and discover-paid-packs.sh use, so this stays
# in lockstep with how the rest of the harness discovers plugins.
PLUGIN_SRC="$(python3 - "$REPO_ROOT" "$PLUGIN_NAME" <<'PY'
import json, os, sys

root, want = sys.argv[1], sys.argv[2]
try:
    mkt = json.load(open(os.path.join(root, ".claude-plugin", "marketplace.json")))
except Exception as e:  # noqa: BLE001
    print(f"::error::failed to read .claude-plugin/marketplace.json: {e}", file=sys.stderr)
    sys.exit(1)

for p in mkt.get("plugins", []):
    if p.get("name") == want:
        src = (p.get("source", "") or "").rstrip("/")
        if src.startswith("./"):
            src = src[2:]
        if not src:
            print(f"::error::plugin '{want}' has empty 'source' in .claude-plugin/marketplace.json", file=sys.stderr)
            sys.exit(1)
        print(src)
        sys.exit(0)

print(f"::error::plugin '{want}' is not registered in .claude-plugin/marketplace.json", file=sys.stderr)
sys.exit(1)
PY
)"
status=$?
if [ "$status" -ne 0 ]; then
  exit "$status"
fi
if [ -z "$PLUGIN_SRC" ]; then
  echo "::error::plugin '$PLUGIN_NAME' resolved to an empty source path" >&2
  exit 1
fi

PLUGIN_DIR="$PLUGIN_SRC"

pass=0; fail=0
# The SAME helper file run.sh sources. Before #120 this runner defined only
# ok/bad/group, so every has/hasE/lacksE call in a pack was a "command not
# found" that execution sailed past — 249 checks across 14 plugins silently
# skipped in the tier the REQUIRED install matrix uses, reported as green.
# shellcheck source=/dev/null
. "$(dirname "${BASH_SOURCE[0]}")/helpers.sh"

group "plugin '$PLUGIN_NAME' cheap eval pack (isolated)"
pack="$PLUGIN_SRC/evals/cheap/checks.sh"
if [ -f "$pack" ]; then
  export PLUGIN_NAME PLUGIN_DIR
  pack_guard_on
  # shellcheck source=/dev/null
  . "$pack"
  pack_guard_off
else
  bad "plugin '$PLUGIN_NAME' ($PLUGIN_SRC) has no cheap eval pack at $pack"
fi

printf '\n\033[1msummary:\033[0m %d passed, %d failed\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
