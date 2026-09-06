#!/usr/bin/env bash
# evals/redteam/run.sh — the only entry point for the red-team lane
# (T42-T48, design/contract §6, §8.6). `--offline` is the default: it runs
# with NO network, no `npx`, no model call, ever (design §10).
#
#   evals/redteam/run.sh                     # == --offline
#   evals/redteam/run.sh --offline
#   evals/redteam/run.sh --assert-offline    # --offline + the docker netproof canary (T48)
#   evals/redteam/run.sh --id T44            # a single backlog item's test module
#   evals/redteam/run.sh --paid --approve-token <T>   # refused without a valid token
#   evals/redteam/run.sh --hosted --approve-token <T> # refused without a valid token (design §12)
#
# IMPORTANT — read before trusting a green run (design §11): the offline
# environment below (PROMPTFOO_DISABLE_REMOTE_GENERATION and friends) is
# DEFENSE IN DEPTH, NOT THE PROOF. The proof is `--assert-offline`'s real
# network-denied sandbox (bin/netproof.sh) plus its canary. A config flag by
# itself is a claim; this repo has an actual, measured egress path (the
# version-update check against api.promptfoo.dev) that none of these env
# vars alone would catch without the sandbox — see README.md.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REDTEAM_ROOT="$HERE"
REPO_ROOT="$(cd "$REDTEAM_ROOT/../.." && pwd)"

MODE="offline"
ASSERT_OFFLINE=0
SINGLE_ID=""
APPROVE_TOKEN=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --offline) MODE="offline"; shift ;;
    --assert-offline) MODE="offline"; ASSERT_OFFLINE=1; shift ;;
    --id) SINGLE_ID="$2"; shift 2 ;;
    --paid) MODE="paid"; shift ;;
    --hosted) MODE="hosted"; shift ;;
    --approve-token) APPROVE_TOKEN="$2"; shift 2 ;;
    *) echo "redteam FAIL usage: unknown argument $1" >&2; exit 2 ;;
  esac
done

fail() {
  # Frozen ordering per contract §8.8's fixture-26 row and §8.6's success
  # tail (both put the lane name FIRST: "redteam: PASS -- ...",
  # "redteam FAIL offline: ..."), which this lane follows throughout even
  # though the red-team DESIGN document's own prose examples used the
  # opposite ("FAIL redteam ...") -- the contract is frozen and wins.
  echo "${1/redteam /redteam FAIL }" >&2
  exit 1
}

# --- paid / hosted: refuse without an explicit approval token, run nothing ---
if [[ "$MODE" == "paid" || "$MODE" == "hosted" ]]; then
  if [[ -z "$APPROVE_TOKEN" ]]; then
    echo "redteam BLOCKED — approval required: $MODE mode needs --approve-token (same authority as T25)." >&2
    exit 1
  fi
  # No further-approved paid/hosted execution path exists in this delivery.
  # This lane never spends money or reaches a network endpoint on its own —
  # closing T45/T46 for real is a separate, explicitly-approved action.
  echo "redteam BLOCKED — approval required: $MODE mode has a token but no approved execution path is wired in this delivery (T45/T46 remain paid-required)." >&2
  exit 1
fi

echo "=== redteam offline: pin check (T42) ==="
# bin/promptfoo.sh itself reads pin.json (not a literal here) and is the
# authority on version drift, node-engine floor, and install presence; this
# step surfaces ITS failure verbatim rather than re-deriving a second,
# differently-worded check against a hardcoded literal.
VERSION_TMP="$(mktemp)"
if ! "$REDTEAM_ROOT/bin/promptfoo.sh" --version > "$VERSION_TMP" 2>&1; then
  cat "$VERSION_TMP" >&2
  rm -f "$VERSION_TMP"
  fail "redteam pin: bin/promptfoo.sh --version failed (see the message above)"
fi
VERSION_OUT="$(tr -d '\n' < "$VERSION_TMP")"
rm -f "$VERSION_TMP"
echo "redteam pin: OK — pinned promptfoo $VERSION_OUT"

echo "=== redteam offline: no npx anywhere (T42) ==="
# Targets the actual INVOCATION shape counterfeit fixture 26 inserts
# (design §10.5) -- the resolver, followed (through any flags) by the
# package it would fetch over the network -- not the bare word: this file's
# own diagnostic strings below necessarily NAME the ban ("npx reference in
# evals/redteam", "0 npx references"), and a blind word-boundary grep over
# source would flag its own error message. Comment lines are excluded too,
# so this header's own worked example does not self-trigger.
NPX_HITS="$(python3 "$REDTEAM_ROOT/bin/npxcheck.py" "$REDTEAM_ROOT")"
if [[ -n "$NPX_HITS" ]]; then
  fail "redteam offline: npx reference in evals/redteam ($NPX_HITS)"
fi
echo "redteam offline: OK — 0 npx references outside documentation"

echo "=== redteam offline: environment assertions (T48/§11) ==="
for var in PROMPTFOO_REMOTE_GENERATION_URL PROMPTFOO_UNALIGNED_INFERENCE_ENDPOINT PROMPTFOO_CLOUD_API_URL PROMPTFOO_API_KEY; do
  if [[ -n "${!var:-}" ]]; then
    fail "redteam offline: $var is set"
  fi
done
echo "redteam offline: OK — no remote-generation override vars set"

echo "=== redteam corpus: frozen-corpus integrity (T44) ==="
python3 "$REDTEAM_ROOT/bin/freeze.py" --check || exit 1

echo "=== redteam design: control configs match the frozen corpus (T45 offline form) ==="
python3 "$REDTEAM_ROOT/bin/render_controls.py" --check || exit 1

echo "=== redteam design: 2x2 generated configs match the frozen corpus, no drift, no dominance defect (T46) ==="
python3 "$REDTEAM_ROOT/bin/generate.py" --check || exit 1

echo "=== redteam offline: validating every config against promptfoo 0.122.0 (T42) ==="
CONFIG_COUNT=0
while IFS= read -r -d '' cfg; do
  CONFIG_COUNT=$((CONFIG_COUNT + 1))
  if ! "$REDTEAM_ROOT/bin/promptfoo.sh" validate -c "$cfg" >/dev/null 2>/tmp/redteam-validate.$$; then
    cat /tmp/redteam-validate.$$ >&2
    rm -f /tmp/redteam-validate.$$
    fail "redteam offline: config invalid under promptfoo 0.122.0: $cfg"
  fi
  rm -f /tmp/redteam-validate.$$
done < <(find "$REDTEAM_ROOT" -path "$REDTEAM_ROOT/.artifacts" -prune -o \
              -path "$REDTEAM_ROOT/configs/hosted" -prune -o \
              -path "$REDTEAM_ROOT/configs/paid" -prune -o \
              -name '*.yaml' -type f -print0)
echo "redteam offline: OK — $CONFIG_COUNT configs valid"

echo "=== redteam offline: running the offline test suite ==="
if [[ -n "$SINGLE_ID" ]]; then
  echo "redteam offline: --id is accepted but this delivery does not yet map every"
  echo "  backlog ID to a single test selector; running the full offline suite for $SINGLE_ID."
fi
(
  cd "$REPO_ROOT" && \
  python3 -m unittest \
    evals.agentic.tests.test_redteam_provider \
    evals.agentic.tests.test_redteam_corpus \
    evals.agentic.tests.test_redteam_controls \
    evals.agentic.tests.test_redteam_design \
    -v
)
TEST_EXIT=$?
if [[ "$TEST_EXIT" != "0" ]]; then
  fail "redteam offline: test suite failed (exit $TEST_EXIT)"
fi

if [[ "$ASSERT_OFFLINE" == "1" ]]; then
  echo "=== redteam offline: --assert-offline: docker network-denial proof (T48) ==="
  "$REDTEAM_ROOT/bin/netproof.sh" --check-canary || fail "redteam offline: netproof did not verify isolation"
fi

echo "redteam: PASS — $CONFIG_COUNT configs validated against promptfoo 0.122.0, corpus hashes match, 0 npx references"
exit 0
