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

# PROMPTFOO_HOME is the pinned install's `node_modules/promptfoo` directory.
# It is a HOST FACT, not a repo fact: this tree ships no vendored copy, so the
# path below is only the default measured on the machine this lane was built
# on. It is documented as a required environment variable in README.md's
# "Run it" section; every other machine must export PROMPTFOO_HOME (and, for
# bin/netproof.sh's docker bind-mount, NPX_CACHE_ROOT -- which now defaults to
# PROMPTFOO_HOME's grandparent rather than a second hardcoded absolute path).
: "${PROMPTFOO_HOME:=/home/jrichlen/ai/tools/promptfoo-0.122.0/node_modules/promptfoo}"
PF_ENTRY="$PROMPTFOO_HOME/dist/src/entrypoint.js"
PF_PKG="$PROMPTFOO_HOME/package.json"
# A CLOSED loopback port. Nothing may bind port 1 in this lane, and the
# canary/listener paths use ephemeral ports, so this can never accidentally
# become a working tunnel.
OFFLINE_PROXY="http://127.0.0.1:1"
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

# These must never be allowed to redirect a future remote path (design §10.2),
# and no provider credential may reach the child: hasCodexDefaultCredentials()
# consults CODEX_API_KEY / OPENAI_API_KEY (remoteGeneration-BLmiGTEn.js), and
# @openai/codex-sdk IS installed in the pinned tree, so canLoadCodexSdkPackage()
# is already satisfied -- the key vars were the only thing left.
unset PROMPTFOO_REMOTE_GENERATION_URL PROMPTFOO_UNALIGNED_INFERENCE_ENDPOINT \
      PROMPTFOO_CLOUD_API_URL PROMPTFOO_API_KEY \
      OPENAI_API_KEY CODEX_API_KEY ANTHROPIC_API_KEY

# --- fail-closed egress (the disable-vars above are NOT enough) ------------
# MEASURED 2026-09-06 with a loopback CONNECT sink: ONE `promptfoo validate`
# through THIS wrapper -- with PROMPTFOO_DISABLE_TELEMETRY=1 and
# PROMPTFOO_DISABLE_UPDATE=1 already exported -- still issued 5
# `CONNECT r.promptfoo.app:443` attempts. Cause in the pinned build
# (dist/src/telemetry-VjpZ13i_.js:112-152): record() calls
# recordTelemetryDisabled() *because* PROMPTFOO_DISABLE_TELEMETRY is set,
# which calls sendEvent(), whose trailing
# fetchWithProxy(R_ENDPOINT = "https://r.promptfoo.app/") POST is
# unconditional and `.catch(() => {})`-swallowed. The disable flag changes
# the PAYLOAD, not whether the POST happens -- so a run could look, and did
# look, perfectly green while talking to a vendor endpoint on every
# invocation.
#
# Every outbound request in the pinned build funnels through fetchWithProxy
# (dist/src/fetch-CxxpLUCt.js:1228), which resolves a proxy per URL with
# proxy-from-env's getProxyForUrl() and honours it for the telemetry POST,
# the update check, PostHog (which is itself constructed with
# `fetch: fetchWithProxy`) and any provider fetch alike. Pointing that at a
# CLOSED loopback port fails every request closed ON THIS HOST, before a
# packet can leave it. no_proxy is forced EMPTY so nothing can carve an
# exception back out.
#
# This is defense in depth beside T48's real `--network=none` sandbox, never
# a replacement for it: a proxy variable is still a claim, and
# bin/netproof.sh is still the proof.
export HTTP_PROXY="$OFFLINE_PROXY" HTTPS_PROXY="$OFFLINE_PROXY" ALL_PROXY="$OFFLINE_PROXY"
export http_proxy="$OFFLINE_PROXY" https_proxy="$OFFLINE_PROXY" all_proxy="$OFFLINE_PROXY"
export NO_PROXY="" no_proxy=""

# Redirect HOME/CODEX_HOME so the file-based credential fallback
# (~/.codex/auth.json -- present on this host, mode 0600) is never reachable,
# even when this wrapper is invoked directly (a test, a freeze check) rather
# than through run.sh.
#
# FORCED, not defaulted (fixed 2026-09-06): these were `: "${HOME:=...}"`,
# which never fires, because HOME is always already set in a real shell --
# `.artifacts/adhoc/` contained pfhome/ and no-codex/ but no home/ at all,
# which is exactly the proof it never fired. CODEX_HOME happened to be
# covered only because it is normally unset; a caller that sets it (running
# this suite inside a Codex session) restored reachability of the real
# ~/.codex/auth.json. getCodexHome() prefers CODEX_HOME over
# os.homedir()/.codex (dist/src/remoteGeneration-BLmiGTEn.js:38-43), so both
# have to be pinned, not defaulted. The earlier comment also claimed run.sh
# "sets its own distinct per-run directories" -- it sets no environment at
# all; this wrapper is the only place these are set, which is why forcing
# them here is load-bearing rather than redundant.
#
# PROMPTFOO_CONFIG_DIR stays caller-overridable (":="): it holds no
# credential fallback path, and the test suite points it at a per-test temp
# dir on purpose.
_ADHOC="$REDTEAM_ROOT/.artifacts/adhoc"
: "${PROMPTFOO_CONFIG_DIR:=$_ADHOC/pfhome}"
HOME="$_ADHOC/home"
CODEX_HOME="$_ADHOC/no-codex"
export PROMPTFOO_CONFIG_DIR HOME CODEX_HOME
mkdir -p "$PROMPTFOO_CONFIG_DIR" "$HOME" "$CODEX_HOME"

exec node "$PF_ENTRY" "$@"
