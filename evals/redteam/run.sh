#!/usr/bin/env bash
# evals/redteam/run.sh — the only entry point for the red-team lane
# (T42-T48, design/contract §6, §8.6). `--offline` is the default: no `npx`,
# no model call, and every outbound request failed closed at a dead loopback
# proxy before it can leave this host (design §10, and see "measured egress"
# below -- the earlier "NO network ... ever" wording here was FALSE and is
# deliberately gone).
#
#   evals/redteam/run.sh                     # == --offline
#   evals/redteam/run.sh --offline
#   evals/redteam/run.sh --gate              # repo-root-portable subset, <5s (see below;
#                                            #   still requires the pinned install at
#                                            #   PROMPTFOO_HOME -- portable across repo
#                                            #   roots, not across hosts)
#   evals/redteam/run.sh --assert-offline    # --offline + the docker netproof canary (T48)
#   evals/redteam/run.sh --id T44            # a single backlog item's test module
#   evals/redteam/run.sh --paid --approve-token <T>   # refused without a valid token
#   evals/redteam/run.sh --hosted --approve-token <T> # refused without a valid token (design §12)
#
# IMPORTANT — read before trusting a green run (design §11): the offline
# environment bin/promptfoo.sh exports (PROMPTFOO_DISABLE_REMOTE_GENERATION
# and friends) is DEFENSE IN DEPTH, NOT THE PROOF. The proof is
# `--assert-offline`'s real network-denied sandbox (bin/netproof.sh) plus its
# canary. A config flag by itself is a claim, and this lane has TWO measured
# egress paths that prove it:
#
#   1. the version-update check against api.promptfoo.dev, closed by
#      PROMPTFOO_DISABLE_UPDATE=1; and
#   2. an unconditional telemetry POST to https://r.promptfoo.app/ that
#      PROMPTFOO_DISABLE_TELEMETRY=1 does NOT close -- setting that flag makes
#      the pinned build send a "telemetry disabled" event to the SAME endpoint
#      (dist/src/telemetry-VjpZ13i_.js:112-152). Measured 2026-09-06 with a
#      loopback CONNECT sink: one `promptfoo validate` through
#      bin/promptfoo.sh made 5 `CONNECT r.promptfoo.app:443` attempts while
#      this script printed a fully green "redteam: PASS".
#
# (2) is now failed closed on the host by bin/promptfoo.sh forcing
# HTTP_PROXY/HTTPS_PROXY/ALL_PROXY at a dead loopback port with an empty
# no_proxy; re-measured after the fix, strace records exactly one connect(),
# to 127.0.0.1:1, and zero packets naming promptfoo.app. See README.md's "A
# real, measured egress path" section.
#
# --gate (integration lane, coordinator's integration-cost-decisions.md
# decision 3; contract §9.1's cheap-tier section 22 calls this) is a
# DELIBERATELY NARROWER check than the default --offline suite above: pin
# version read from the pinned package.json (no promptfoo entrypoint exec'd
# beyond a single --version call), the corpus freeze check, the
# npx-invocation grep, a static "every provider exports a class" scan,
# "the generated-configs directory exists and its index is valid JSON
# naming files that exist", an in-process dominance ALLOWLIST scan (the
# whole defaultTest shape: threshold 1, exactly the three deterministic
# `javascript` assertions at weight 1, and no per-row override of `assert`
# or `threshold` -- widened 2026-09-06 from a three-pattern denylist that
# missed every OTHER model-graded assertion type the pinned build routes to
# a grading provider, and never looked at `threshold` at all), an
# in-process native-provenance forgery guard against committed ledger
# fixtures, and a static per-row vacuity scan (below).
#
# EXACTLY ONE promptfoo process runs in --gate: the pin check's single
# `bin/promptfoo.sh --version`, which ends in `exec node
# $PROMPTFOO_HOME/dist/src/entrypoint.js --version`. It evaluates nothing.
# This sentence used to assert, in capitals, that no promptfoo process ran
# in --gate whatsoever, which was FALSE and contradicted this same file a
# few lines up ("no promptfoo entrypoint exec'd beyond a single --version
# call" -- that one was the accurate half all along); corrected
# 2026-09-07 for review finding R11 after
# `strace -f -e trace=execve ./run.sh --gate` recorded
# `execve(.../bin/node, ["node", ".../promptfoo-0.122.0/.../entrypoint.js",
# "--version"])` alongside three `node -e` package.json/version reads.
#
# One consequence is deliberate and is NOT papered over with a skip: --gate
# HARD-DEPENDS on the pinned install being present at PROMPTFOO_HOME (the
# absolute path in pin.json is only this host's default; every other machine
# must export it -- see README.md's "Run it"). On a host without it, --gate
# FAILS with "redteam FAIL pin: ..." rather than reporting SKIP. That is the
# intended behaviour: a gate that passes because it could not find the thing
# it pins is worse than one that says so out loud.
#
# What --gate does NOT run is a promptfoo EVAL. An earlier version of this
# file ran one real `promptfoo eval` here to catch the one vacuity shape
# (`testCase.options.disableDefaultAsserts`) invisible to static analysis;
# removed
# (2026-09-06, coordinator decision) after it intermittently misclassified
# a real provider FAULT as VACUOUS under heavy host CPU contention -- see
# bin/verdict.py's classify_row fix and the integration report for the full
# account. A flaky always-on gate is worse than a documented gap, so the
# static scan below catches only the STATICALLY VISIBLE vacuity shape
# (disableDefaultAsserts with no per-row assert); the runtime VACUOUS
# classification itself (a row promptfoo actually scored a perfect,
# assertion-free pass) is exercised only by `--offline`'s real
# `evals.agentic.tests.test_redteam_design` run, never by --gate. --gate
# also deliberately does NOT run `promptfoo validate` over every config
# (T42's full form: ~30 real subprocess invocations), does NOT run docker
# (T48), and does NOT run `generate.py --check`'s live-tree regeneration
# (T46: that reads the real, live 25-plugin marketplace tree, which the
# counterfeit corpus's synthetic root does not have — the same reason
# contract §9.3 excludes T11/T12/T19-23 from evals/agentic's own --gate).
# Those remain exercised for real by this script's own --offline default
# and by `unittest discover`. Target: <5s -- MEASURED 0.94s and 0.97s on two
# consecutive runs, 2026-09-07 -- with exactly one promptfoo process, the
# `--version` call described above, and no docker (that half of the old
# claim did hold: no docker execve appears in the strace).
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
    --gate) MODE="gate"; shift ;;
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

# --- --gate: root-portable subset, see the header comment for what this
# deliberately excludes and why. Runs to completion in well under 5s. --------
if [[ "$MODE" == "gate" ]]; then
  echo "=== redteam gate: pin check (T42, package.json comparison only) ==="
  # Delegates to bin/promptfoo.sh --version -- the ONE place the pinned
  # entrypoint is named (see that file's own header) -- rather than
  # reimplementing the pin.json-vs-installed-package.json comparison here a
  # second time with different wording. This is what makes counterfeit
  # fixture 28's frozen EXPECT_FAIL_SUBSTRING ("redteam FAIL pin: version
  # drift") reachable from --gate: that exact string is emitted by
  # bin/promptfoo.sh's OWN fail() (prefix "redteam FAIL pin: "), the same
  # mechanism the --offline default path already relies on below. A single
  # `--version` invocation prints the pinned version after that check passes
  # -- it does not validate any config and is not the "promptfoo validate"
  # this file's header comment excludes.
  GATE_PIN_TMP="$(mktemp)"
  if ! "$REDTEAM_ROOT/bin/promptfoo.sh" --version > "$GATE_PIN_TMP" 2>&1; then
    cat "$GATE_PIN_TMP" >&2
    rm -f "$GATE_PIN_TMP"
    exit 1
  fi
  GATE_PIN_VERSION="$(tr -d '\n' < "$GATE_PIN_TMP")"
  rm -f "$GATE_PIN_TMP"
  echo "redteam gate: OK — pinned promptfoo $GATE_PIN_VERSION"

  echo "=== redteam gate: corpus freeze check (T44, pure hashing) ==="
  python3 "$REDTEAM_ROOT/bin/freeze.py" --check || fail "redteam gate: corpus freeze check failed"
  echo "redteam gate: OK — corpus freeze check passed"

  echo "=== redteam gate: no npx anywhere (T42) ==="
  NPX_HITS="$(python3 "$REDTEAM_ROOT/bin/npxcheck.py" "$REDTEAM_ROOT")"
  [[ -z "$NPX_HITS" ]] || fail "redteam offline: npx reference in evals/redteam ($NPX_HITS)"
  echo "redteam gate: OK — 0 npx references"

  echo "=== redteam gate: provider files export a class (T43, static scan) ==="
  PROVIDER_FAIL="$(python3 - "$REDTEAM_ROOT/providers" <<'PYEOF'
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
bad = []
for p in sorted(root.glob("*.js")):
    text = p.read_text(encoding="utf-8")
    if "module.exports = " not in text or not re.search(r"class \w+", text):
        bad.append(str(p))
print("\n".join(bad))
PYEOF
)"
  [[ -z "$PROVIDER_FAIL" ]] || fail "redteam gate: provider(s) do not export a class: $PROVIDER_FAIL"
  echo "redteam gate: OK — every provider exports a class"

  echo "=== redteam gate: generated configs directory present and parseable (T46, no live-tree read) ==="
  GEN_DIR="$REDTEAM_ROOT/configs/generated"
  [[ -d "$GEN_DIR" ]] || fail "redteam gate: $GEN_DIR is missing"
  python3 -c "
import json
import sys
from pathlib import Path

gen_dir = Path(sys.argv[1])
idx_path = gen_dir / '_index.json'
if not idx_path.is_file():
    print('_index.json missing', file=sys.stderr)
    sys.exit(1)
doc = json.loads(idx_path.read_text(encoding='utf-8'))
plugins = doc.get('plugins')
if not isinstance(plugins, dict) or not plugins:
    print('no non-empty plugins mapping in _index.json', file=sys.stderr)
    sys.exit(1)
for name in plugins:
    cfg = gen_dir / f'{name}.yaml'
    if not cfg.is_file() or cfg.stat().st_size == 0:
        print(f'{cfg} missing or empty', file=sys.stderr)
        sys.exit(1)
" "$GEN_DIR" || fail "redteam gate: generated configs directory not parseable"
  echo "redteam gate: OK — generated configs present, index parseable"

  echo "=== redteam gate: assertion weight map / dominance (T46, no live-tree read) ==="
  # bin/generate.py's check_dominance() is a pure static scan of whatever is
  # ALREADY on disk under configs/generated/ -- it never reads the live
  # plugin tree (that only happens in cmd_check()'s later drift-regeneration
  # half, which --gate deliberately excludes: "NO generate.py --check", the
  # header comment above). Importing the module and calling this one
  # function directly is root-portable and fast; it is what produces
  # counterfeit fixture 29's frozen substring ("redteam FAIL design:
  # assertion weight map") verbatim, since cmd_check() uses the exact same
  # f-string prefix.
  DOMINANCE_OUT="$(python3 -c "
import sys
sys.path.insert(0, '$REDTEAM_ROOT/bin')
import generate

problems = generate.check_dominance(generate.GENERATED_DIR)
for p in problems:
    print(f'redteam FAIL design: assertion weight map {p}')
sys.exit(1 if problems else 0)
")"
  DOMINANCE_CODE=$?
  if [[ "$DOMINANCE_CODE" -ne 0 ]]; then
    printf '%s\n' "$DOMINANCE_OUT" >&2
    exit 1
  fi
  echo "redteam gate: OK — every generated config carries threshold 1 and exactly the three deterministic assertions, each at weight 1"

  echo "=== redteam gate: native-provenance forgery guard on committed ledger fixtures (T47, no live-tree read) ==="
  # bin/verdict.py's qualify()/row_provenance_entry() run purely in-process
  # against committed JSON row fixtures under fixtures/ledgers/** -- no
  # promptfoo, no docker, no live plugin tree. This is what makes
  # counterfeit fixture 30's frozen substring ("redteam qualify: native
  # provenance not attested by an adapter ledger") reachable from --gate:
  # qualify() raises it verbatim whenever any attempt in the denominator
  # CLAIMS provenance='native' with no host_ledger_reader supplied (exactly
  # fixture 30's mutation), and does NOT raise it for the unmutated fixture
  # (which is legitimately provenance='simulated' throughout, design §9).
  FORGERY_OUT="$(python3 -c "
import json
import sys
sys.path.insert(0, '$REDTEAM_ROOT/bin')
import verdict

path = '$REDTEAM_ROOT/fixtures/ledgers/disagreement-rubric-vs-effect.json'
doc = json.load(open(path, encoding='utf-8'))
rows = doc['results']
entries = {}
ids = []
for r in rows:
    e = verdict.row_provenance_entry(r)
    entries[e['attempt_id']] = e
    ids.append(e['attempt_id'])
try:
    verdict.qualify('safety', ids, entries, host_ledger_reader=None)
except verdict.NativeProofRequired as exc:
    msg = str(exc)
    if 'native provenance not attested by an adapter ledger' in msg:
        print(msg)
        sys.exit(1)
    if 'no verifiable host ledger' in msg:
        sys.exit(0)
    print(f'redteam FAIL design: unexpected qualify() message: {msg}')
    sys.exit(1)
print('redteam FAIL design: qualify() unexpectedly succeeded on an unattested claim', file=sys.stderr)
sys.exit(1)
")"
  FORGERY_CODE=$?
  if [[ "$FORGERY_CODE" -ne 0 ]]; then
    printf '%s\n' "$FORGERY_OUT" >&2
    exit 1
  fi
  echo "redteam gate: OK — native-provenance forgery guard fires only on an unattested 'native' claim"

  echo "=== redteam gate: static vacuous-row scan (T44/T47, no promptfoo process) ==="
  # Coordinator decision (2026-09-06): a real promptfoo eval used to run
  # here to catch fixture 31's `testCase.options.disableDefaultAsserts`
  # shape; removed after it intermittently misclassified a real provider
  # FAULT as VACUOUS under heavy host CPU contention (bin/verdict.py's
  # classify_row ordering bug, now fixed separately -- see that function's
  # docstring). A flaky always-on gate is worse than a documented gap, so
  # this step is a pure static, subprocess-free text scan of the already-
  # generated YAML (same regex-over-committed-text technique
  # bin/generate.py's own check_dominance() already uses, and the same
  # GENERATED_DIR the dominance step above already resolved): for every
  # already-generated config, split the `tests:` section into per-row
  # blocks (each starts with the literal "  - description:" bin/generate.py
  # always emits, contract-frozen render shape) and fail on any row that
  # carries `disableDefaultAsserts: true` -- since bin/generate.py NEVER
  # emits a per-row `assert:` override (every row relies entirely on
  # `defaultTest.assert`, contract §7.4/§8.1), a row that disables the
  # default asserts and has none of its own has, by construction, ZERO
  # effective assertions: exactly the statically-visible half of fixture
  # 31's defect. The runtime half -- a row promptfoo itself actually SCORES
  # as a vacuous "No assertions" perfect pass at eval time -- is real and
  # still tested, just not from --gate: evals.agentic.tests.
  # test_redteam_design.ProtectedEffectDominanceAndNativeGate's real-eval
  # test exercises it under --offline.
  VACUOUS_SCAN_OUT="$(python3 -c "
import re
import sys
sys.path.insert(0, '$REDTEAM_ROOT/bin')
import generate

ROW_RE = re.compile(r'(?m)^  - description:.*(?:\n(?!  - description:).*)*')
problems = []
for cfg in sorted(generate.GENERATED_DIR.glob('*.yaml')):
    text = cfg.read_text(encoding='utf-8')
    tests_idx = text.find('\ntests:\n')
    if tests_idx == -1:
        continue
    tests_text = text[tests_idx:]
    for row in ROW_RE.findall(tests_text):
        if 'disableDefaultAsserts' not in row:
            continue
        if not re.search(r'disableDefaultAsserts:\s*true', row):
            continue
        if re.search(r'(?m)^\s{4}assert:', row):
            # A row overriding disableDefaultAsserts AND supplying its own
            # assert: list is NOT vacuous -- bin/generate.py never emits
            # this shape today, but the check stays precise rather than
            # banning a combination that was never the actual defect.
            continue
        desc_match = re.match(r'  - description:\s*(.*)', row)
        desc = desc_match.group(1) if desc_match else '<unknown row>'
        problems.append(f'{cfg}: row {desc} sets disableDefaultAsserts with no assert of its own')
for p in problems:
    print(f'redteam FAIL design: vacuous row {p}')
sys.exit(1 if problems else 0)
")"
  VACUOUS_SCAN_CODE=$?
  if [[ "$VACUOUS_SCAN_CODE" -ne 0 ]]; then
    printf '%s\n' "$VACUOUS_SCAN_OUT" >&2
    exit 1
  fi
  echo "redteam gate: OK — no generated config row disables its default assertions without one of its own"

  echo "redteam: PASS — gate subset (pin, corpus freeze, npx grep, provider shape, generated-config presence, dominance, forgery guard, static vacuous-row scan)"
  exit 0
fi

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
# The provider-credential vars are in this loop as well as bin/promptfoo.sh's
# `unset` list: the wrapper stops a key reaching the CHILD, and this loop
# stops an offline run being STARTED in a shell that holds one at all
# (hasCodexDefaultCredentials() reads CODEX_API_KEY / OPENAI_API_KEY, and the
# pinned tree ships @openai/codex-sdk, so canLoadCodexSdkPackage() is already
# satisfied). Both halves are needed; neither is redundant.
for var in PROMPTFOO_REMOTE_GENERATION_URL PROMPTFOO_UNALIGNED_INFERENCE_ENDPOINT \
           PROMPTFOO_CLOUD_API_URL PROMPTFOO_API_KEY \
           OPENAI_API_KEY CODEX_API_KEY ANTHROPIC_API_KEY; do
  if [[ -n "${!var:-}" ]]; then
    fail "redteam offline: $var is set"
  fi
done
echo "redteam offline: OK — no remote-generation override or provider-credential vars set"

echo "=== redteam corpus: frozen-corpus integrity (T44) ==="
python3 "$REDTEAM_ROOT/bin/freeze.py" --check || exit 1

echo "=== scanner quality measurement (separate from harness correctness) ==="
node "$REDTEAM_ROOT/providers/lib/calibration.js" || exit 1

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
