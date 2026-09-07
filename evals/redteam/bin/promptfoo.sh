#!/usr/bin/env bash
# bin/promptfoo.sh — the ONE place the pinned promptfoo entrypoint is named.
#
# There is deliberately no `npx` anywhere in evals/redteam/**: npx resolves
# `promptfoo@latest` over the network and would both un-pin the version and
# break the offline default (T42, T48). Every other script in this tree calls
# THIS file; nothing else names dist/src/entrypoint.js.
#
# Every invocation of this wrapper — test, freeze check, or a real run.sh
# invocation — carries the offline environment (settled-unknowns.md #5) and a
# fail-closed version check against the pinned 0.122.0 and the node engine
# floor, BEFORE the real binary is exec'd. This is intentionally redundant
# with run.sh's own offline-environment setup (design §10.2): it is what makes
# "invoked by path, not npx" something more than a location — see T42's third
# control, which mutates exactly this file's exported disable-vars.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REDTEAM_ROOT="$(cd "$HERE/.." && pwd)"
PIN_JSON="$REDTEAM_ROOT/pin.json"

: "${PROMPTFOO_HOME:=/home/jrichlen/ai/tools/promptfoo-0.122.0/node_modules/promptfoo}"
PF_ENTRY="$PROMPTFOO_HOME/dist/src/entrypoint.js"
PF_PKG="$PROMPTFOO_HOME/package.json"
MIN_NODE_MAJOR=22
MIN_NODE_MINOR=22
MIN_NODE_PATCH=0

fail() {
  # Frozen ordering (lane name first): contract §8.8/§8.6.
  echo "redteam FAIL pin: $1" >&2
  exit 1
}

command -v node >/dev/null 2>&1 || fail "node is not on PATH"

# --- pin.json is the source of truth for the expected version, not a
# hardcoded literal in this script -- so a mutated pin.json (counterfeit
# fixture 28-redteam-pin-drift) actually changes this check's outcome. ---
[[ -f "$PIN_JSON" ]] || fail "pin.json missing at $PIN_JSON"
EXPECTED_VERSION="$(node -e "process.stdout.write(require(process.argv[1]).promptfoo.version || '')" "$PIN_JSON" 2>/dev/null || true)"
[[ -n "$EXPECTED_VERSION" ]] || fail "unreadable promptfoo.version field in $PIN_JSON"

# --- check 1: package.json exists ------------------------------------------
[[ -f "$PF_PKG" ]] || fail "promptfoo not installed at $PROMPTFOO_HOME"
[[ -f "$PF_ENTRY" ]] || fail "promptfoo not installed at $PROMPTFOO_HOME"

# --- check 2: package.json .version == pin.json's declared version ---------
PKG_VERSION="$(node -e "process.stdout.write(require(process.argv[1]).version || '')" "$PF_PKG" 2>/dev/null || true)"
[[ -n "$PKG_VERSION" ]] || fail "unreadable version field in $PF_PKG"
[[ "$PKG_VERSION" == "$EXPECTED_VERSION" ]] || fail "version drift $PKG_VERSION != $EXPECTED_VERSION"

# --- node engine floor (dist/src/entrypoint.js hardcodes >=22.22.0, design §2.3) ---
NODE_VERSION_RAW="$(node -e 'process.stdout.write(process.versions.node)')"
IFS='.' read -r NV_MAJOR NV_MINOR NV_PATCH <<<"$NODE_VERSION_RAW"
NV_MAJOR="${NV_MAJOR:-0}"; NV_MINOR="${NV_MINOR:-0}"; NV_PATCH="${NV_PATCH:-0}"
node_ok=1
if (( NV_MAJOR > MIN_NODE_MAJOR )); then
  node_ok=0
elif (( NV_MAJOR == MIN_NODE_MAJOR )); then
  if (( NV_MINOR > MIN_NODE_MINOR )); then
    node_ok=0
  elif (( NV_MINOR == MIN_NODE_MINOR )) && (( NV_PATCH >= MIN_NODE_PATCH )); then
    node_ok=0
  fi
fi
[[ "$node_ok" == "0" ]] || fail "node v$NODE_VERSION_RAW below promptfoo engine floor >=22.22.0"

# --- the offline environment (design §10.2) --------------------------------
# Forced, not defaulted: T42's third control mutates this file to remove
# these two exports and the run must then fail under T48's sandbox on the
# update-check egress.
export PROMPTFOO_DISABLE_UPDATE=1
export PROMPTFOO_DISABLE_TELEMETRY=1
export PROMPTFOO_DISABLE_REMOTE_GENERATION=1
export PROMPTFOO_DISABLE_REDTEAM_REMOTE_GENERATION=1
export PROMPTFOO_DISABLE_SHARING=1
export PROMPTFOO_DISABLE_SHARE_EMAIL_REQUEST=1
export PROMPTFOO_CACHE_ENABLED=0
export PROMPTFOO_TRACING_ENABLED=0
export PROMPTFOO_OTEL_ENABLED=0

# These must never be allowed to redirect a future remote path (design §10.2).
unset PROMPTFOO_REMOTE_GENERATION_URL PROMPTFOO_UNALIGNED_INFERENCE_ENDPOINT \
      PROMPTFOO_CLOUD_API_URL PROMPTFOO_API_KEY

# Redirect HOME/CODEX_HOME/PROMPTFOO_CONFIG_DIR so the file-based credential
# fallback (~/.codex/auth.json) is never reachable, even when this wrapper is
# invoked directly (a test, a freeze check) rather than through run.sh, which
# sets its own distinct per-run directories. Caller-set values win (":=").
_ADHOC="$REDTEAM_ROOT/.artifacts/adhoc"
: "${PROMPTFOO_CONFIG_DIR:=$_ADHOC/pfhome}"
: "${HOME:=$_ADHOC/home}"
: "${CODEX_HOME:=$_ADHOC/no-codex}"
export PROMPTFOO_CONFIG_DIR HOME CODEX_HOME
mkdir -p "$PROMPTFOO_CONFIG_DIR" "$HOME" "$CODEX_HOME"

exec node "$PF_ENTRY" "$@"
