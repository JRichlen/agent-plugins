#!/usr/bin/env bash
# bin/netproof.sh — sandbox selection + the non-vacuity canary (design §10.3,
# §10.4). Picks the STRONGEST available network-denial mode and fails closed
# if none is verified; never downgrades silently.
#
#   evals/redteam/bin/netproof.sh --check-canary [--artifacts DIR]
#
# Writes, under --artifacts (default: evals/redteam/.artifacts/netproof/):
#   mode                  "docker" | "strace" | "none"
#   canary-outside.json   the canary run OUTSIDE any sandbox (positive control)
#   canary-inside.json    the canary run INSIDE the selected sandbox (docker mode only)
#   manifest.json         summary + verdict
#
# Exit 0 iff a network-denial mode was verified AND (for docker) the canary
# proves real isolation (design §10.4's non-vacuity check). Exit 1 otherwise.
# Docker mode is the only one this repeats T48's *closure* claim on (contract
# §8.6/backlog T48; strace mode here is retained only as a documented
# diagnostic path, per design §10.3's "T48 is closable in docker mode only").
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REDTEAM_ROOT="$(cd "$HERE/.." && pwd)"
REPO_ROOT="$(cd "$REDTEAM_ROOT/../.." && pwd)"

ARTIFACTS="$REDTEAM_ROOT/.artifacts/netproof"
CHECK_CANARY=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-canary) CHECK_CANARY=1; shift ;;
    --artifacts) ARTIFACTS="$2"; shift 2 ;;
    *) echo "redteam FAIL offline: netproof.sh: unknown argument $1" >&2; exit 2 ;;
  esac
done

mkdir -p "$ARTIFACTS"
rm -f "$ARTIFACTS"/canary-outside.json "$ARTIFACTS"/canary-inside.json "$ARTIFACTS"/manifest.json

fail() {
  echo "redteam FAIL offline: $1" >&2
  echo "none" > "$ARTIFACTS/mode"
  exit 1
}

NODE_HOME_DIR="$(dirname "$(dirname "$(command -v node)")")"
NPX_CACHE_ROOT="/home/jrichlen/ai/tools/promptfoo-0.122.0"

docker_available() {
  command -v docker >/dev/null 2>&1 || return 1
  docker info >/dev/null 2>&1 || return 1
  docker image inspect ubuntu:24.04 >/dev/null 2>&1 || return 1
  return 0
}

strace_available() {
  command -v strace >/dev/null 2>&1 || return 1
  strace -f -qq -e trace=connect /bin/true >/dev/null 2>&1 || return 1
  return 0
}

# --- select mode -------------------------------------------------------
if docker_available; then
  MODE="docker"
elif strace_available; then
  MODE="strace"
else
  fail "no verified network-denial sandbox available"
fi

echo "$MODE" > "$ARTIFACTS/mode"

if [[ "$CHECK_CANARY" != "1" ]]; then
  echo "redteam offline: sandbox mode selected: $MODE"
  exit 0
fi

if [[ "$MODE" != "docker" ]]; then
  # strace mode is diagnostics only (design §10.3) and cannot close T48.
  cat > "$ARTIFACTS/manifest.json" <<EOF
{"mode": "$MODE", "closes_t48": false, "reason": "strace mode runs with the real HOME and cannot isolate; docker is unavailable on this host"}
EOF
  echo "redteam offline: BLOCKED — docker unavailable, strace mode is diagnostics only and cannot close T48"
  exit 1
fi

# --- docker mode: the canary, both directions (design §10.4) -----------

# Outside-the-sandbox positive control: the SAME canary, hitting a listener
# it can actually reach. If this fails, the canary itself is broken and
# proves nothing.
OUTSIDE_LOG="$ARTIFACTS/listener-outside.log"
: > "$OUTSIDE_LOG"
python3 "$HERE/listener.py" --log "$OUTSIDE_LOG" --max-seconds 15 > "$ARTIFACTS/listener-outside.port" &
LISTENER_OUTSIDE_PID=$!
for _ in $(seq 1 50); do
  [[ -s "$ARTIFACTS/listener-outside.port" ]] && break
  sleep 0.1
done
OUTSIDE_PORT="$(cat "$ARTIFACTS/listener-outside.port" 2>/dev/null || true)"
[[ -n "$OUTSIDE_PORT" ]] || fail "listener (outside) never bound a port"

REDTEAM_CANARY_OUTFILE="$ARTIFACTS/canary-outside.json" \
REDTEAM_CANARY_PORT="$OUTSIDE_PORT" \
REDTEAM_CANARY_HOSTSIDE="true" \
  "$HERE/promptfoo.sh" eval -c "$REDTEAM_ROOT/configs/canary-egress.yaml" \
    --no-cache --no-write --no-table --no-progress-bar \
    -o "$ARTIFACTS/canary-outside.eval.json" >/dev/null 2>&1
wait "$LISTENER_OUTSIDE_PID" 2>/dev/null || true

[[ -f "$ARTIFACTS/canary-outside.json" ]] || fail "canary (outside) produced no output"
OUTSIDE_LOOPBACK_OK="$(python3 -c "import json; print(json.load(open('$ARTIFACTS/canary-outside.json'))['loopback']['ok'])")"
if [[ "$OUTSIDE_LOOPBACK_OK" != "True" ]]; then
  fail "canary (outside the sandbox) could not reach its own loopback listener — the canary is broken and proves nothing"
fi

# Inside-the-sandbox isolation check.
INSIDE_LOG="$ARTIFACTS/listener-inside.log"
: > "$INSIDE_LOG"
python3 "$HERE/listener.py" --log "$INSIDE_LOG" --max-seconds 15 > "$ARTIFACTS/listener-inside.port" &
LISTENER_INSIDE_PID=$!
for _ in $(seq 1 50); do
  [[ -s "$ARTIFACTS/listener-inside.port" ]] && break
  sleep 0.1
done
INSIDE_PORT="$(cat "$ARTIFACTS/listener-inside.port" 2>/dev/null || true)"
[[ -n "$INSIDE_PORT" ]] || fail "listener (inside-target) never bound a port"

mkdir -p "$ARTIFACTS/pfhome" "$ARTIFACTS/home" "$ARTIFACTS/no-codex" "$ARTIFACTS/results"
docker run --rm --network none \
  --user "$(id -u):$(id -g)" \
  -v "$NODE_HOME_DIR":/opt/node:ro \
  -v "$NPX_CACHE_ROOT":/opt/pf:ro \
  -v "$REPO_ROOT":/repo:ro \
  -v "$ARTIFACTS":/out \
  -e PATH=/opt/node/bin:/usr/bin:/bin \
  -e PROMPTFOO_CONFIG_DIR=/out/pfhome \
  -e HOME=/out/home \
  -e CODEX_HOME=/out/no-codex \
  -e PROMPTFOO_DISABLE_UPDATE=1 \
  -e PROMPTFOO_DISABLE_TELEMETRY=1 \
  -e PROMPTFOO_DISABLE_REMOTE_GENERATION=1 \
  -e PROMPTFOO_DISABLE_REDTEAM_REMOTE_GENERATION=1 \
  -e PROMPTFOO_CACHE_ENABLED=0 \
  -e REDTEAM_CANARY_OUTFILE=/out/canary-inside.json \
  -e REDTEAM_CANARY_PORT="$INSIDE_PORT" \
  -e REDTEAM_CANARY_HOSTSIDE=false \
  -w /repo/evals/redteam ubuntu:24.04 \
  /opt/node/bin/node /opt/pf/node_modules/promptfoo/dist/src/entrypoint.js \
    eval -c configs/canary-egress.yaml --no-cache --no-write --no-table --no-progress-bar \
    -o /out/results/canary-inside.eval.json >/dev/null 2>&1
DOCKER_EXIT=$?
wait "$LISTENER_INSIDE_PID" 2>/dev/null || true
# (a non-zero DOCKER_EXIT is expected here — the assertion inside
# canary-egress.yaml is purely structural and this run's job is the
# canary.json side-channel, not a promptfoo pass/fail)

[[ -f "$ARTIFACTS/canary-inside.json" ]] || fail "canary (inside the sandbox) produced no output — the sandboxed process never ran"

INSIDE_RECEIVED="$(grep -c "connect from" "$INSIDE_LOG" 2>/dev/null)"
INSIDE_RECEIVED="${INSIDE_RECEIVED:-0}"
INSIDE_LOOPBACK_OK="$(python3 -c "import json; print(json.load(open('$ARTIFACTS/canary-inside.json'))['loopback']['ok'])")"
INSIDE_TESTNET_ERR="$(python3 -c "import json; print(json.load(open('$ARTIFACTS/canary-inside.json'))['testnet'].get('error'))")"
INSIDE_DNS_OK="$(python3 -c "import json; print(json.load(open('$ARTIFACTS/canary-inside.json'))['dns']['ok'])")"

if [[ "$INSIDE_RECEIVED" != "0" ]]; then
  fail "sandbox is not isolating (loopback listener recorded $INSIDE_RECEIVED inbound connection(s) from the container)"
fi
if [[ "$INSIDE_LOOPBACK_OK" == "True" ]]; then
  fail "sandbox is not isolating (canary reached the loopback listener from inside --network=none)"
fi
if [[ "$INSIDE_DNS_OK" == "True" ]]; then
  fail "sandbox is not isolating (canary resolved DNS from inside --network=none)"
fi
if [[ "$INSIDE_TESTNET_ERR" != "ENETUNREACH" ]]; then
  fail "sandbox is not isolating (TEST-NET-1 probe expected ENETUNREACH, got: $INSIDE_TESTNET_ERR)"
fi

cat > "$ARTIFACTS/manifest.json" <<EOF
{
  "mode": "docker",
  "closes_t48": true,
  "outside": {"loopback_ok": true},
  "inside": {"loopback_ok": false, "dns_ok": false, "testnet_error": "$INSIDE_TESTNET_ERR", "listener_inbound_connections": $INSIDE_RECEIVED}
}
EOF

echo "redteam offline: netproof OK — mode=docker, canary isolated (loopback blocked, DNS blocked, testnet ENETUNREACH, 0 inbound connections observed at the host listener)"
exit 0
