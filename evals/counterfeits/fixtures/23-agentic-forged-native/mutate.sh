#!/usr/bin/env bash
# Two forgeries of native provenance, applied to the staged copy of
# evals/agentic (contract §8.8, fixture 23). Either must red the agentic
# suite's provenance gate:
#   (a) an attempt record that asserts evidence_class: native-proven with
#       event ids and a session id no ledger ever carried;
#   (b) ReplaySession's witness guard removed, plus a driver that builds a
#       HostLedger(witness=HOST_OBSERVED) and replays a recorded stream
#       through it -- host-observed entries minted by a file reader.
#   (c) the same laundering with NO source edit at all: a legally-constructed
#       CALLER_ASSERTED ledger whose private _witness/_key are reassigned after
#       ReplaySession has already accepted it. Strictly cheaper than (b), so a
#       repair that only re-adds (b)'s guard must not turn this fixture green.
# See DEFECT.md for the current (inert) wiring status.
set -euo pipefail
root="${1:?usage: mutate.sh <synthetic-root>}"
agentic="$root/evals/agentic"
adapters="$agentic/framework/adapters.py"
attempts="$agentic/fixtures/native/attempts"

if [ ! -f "$adapters" ]; then
  echo "mutate.sh: $adapters not found (evals/agentic/ not yet staged into the synthetic root)" >&2
  exit 1
fi

# --- (a) an attempt that asserts its own provenance --------------------------
mkdir -p "$attempts"
cat > "$attempts/run-claimed-native.json" <<'JSON'
{
  "attempt_id": "attempt-counterfeit-23",
  "run_id": "run-counterfeit-23",
  "card_id": "redgate-pos-01",
  "arm_id": "treatment",
  "role": "treatment",
  "control_kind": null,
  "parent_attempt_id": null,
  "terminal_state": "delivered",
  "evidence_class": "native-proven",
  "adapter_class": "native",
  "requested": {"provider": "anthropic", "model": "m", "revision": "r", "effort": "n/a", "harness": "claude-cli"},
  "realized": {"provider": "anthropic", "model": "m", "revision": "r", "effort": "n/a", "harness": "claude-cli"},
  "fallback_flags": [],
  "usage": {
    "model_id": "m",
    "reported_by": "counterfeit/23",
    "input_tokens": "UNKNOWN",
    "output_tokens": "UNKNOWN",
    "cache_read_input_tokens": "UNKNOWN",
    "cache_creation_input_tokens": "UNKNOWN",
    "reasoning_tokens": "UNKNOWN",
    "total_tokens": "UNKNOWN",
    "wall_clock_ms": "UNKNOWN",
    "cost_usd": null
  },
  "outcome": {"passed": true, "verifier_id": "counterfeit", "reason": "asserted", "hack_class": null, "evidence_digest": null},
  "adoption": {"passed": true, "verifier_id": "counterfeit", "reason": "asserted", "hack_class": null, "evidence_digest": null},
  "started_at": "2026-09-06T12:00:00.000Z",
  "ended_at": "2026-09-06T12:00:10.000Z",
  "session_id": "harness-sess-NEVER-ACKED",
  "event_ids": ["22222222-2222-4222-8222-222222222222"],
  "arrived_after_terminal": false,
  "notes": "counterfeit 23 mutation (a)"
}
JSON

# --- (b) let a replay hold a host-observed ledger -----------------------------
python3 - "$adapters" <<'PY'
import sys

path = sys.argv[1]
text = open(path, encoding="utf-8").read()

needle = '        if ledger.witness is SignatureClass.HOST_OBSERVED:\n            raise EvidencePromotionRefused(\n                "ReplaySession:'
if needle not in text:
    print("mutate.sh: ReplaySession witness guard not found in adapters.py", file=sys.stderr)
    sys.exit(1)

# Keep the raise reachable-looking but dead: the structure of the file is
# unchanged, which is exactly why a structural gate cannot see this.
text = text.replace(
    needle,
    '        if False:  # COUNTERFEIT 23(b): witness guard defeated\n'
    '            raise EvidencePromotionRefused(\n'
    '                "ReplaySession:',
    1,
)
open(path, "w", encoding="utf-8").write(text)
PY

cat > "$agentic/fixtures/native/replay/forge.py" <<'PY'
#!/usr/bin/env python3
"""COUNTERFEIT 23(b): launder a replayed stream into host-observed entries."""
from __future__ import annotations

import pathlib
import sys
import tempfile

from evals.agentic.framework.adapters import HostLedger, LedgerReader, ReplaySession
from evals.agentic.framework.contract import SignatureClass

HERE = pathlib.Path(__file__).resolve().parent


def main() -> int:
    grammar_raw = __import__("json").loads(
        (HERE / "synthetic-offline-form.grammar.json").read_text(encoding="utf-8")
    )
    from evals.agentic.framework.adapters import JsonPathSpec, StreamGrammar

    grammar = StreamGrammar(
        name=grammar_raw["name"],
        session_ack=JsonPathSpec(**grammar_raw["session_ack"]),
        turn_ack=JsonPathSpec(**grammar_raw["turn_ack"]),
        usage=JsonPathSpec(**grammar_raw["usage"]),
        session_id_field=grammar_raw["session_id_field"],
        turn_index_field=grammar_raw["turn_index_field"],
    )
    scratch = pathlib.Path(tempfile.mkdtemp(prefix="counterfeit-23-"))
    ledger = HostLedger(
        scratch / "events.jsonl", run_id="run-counterfeit-23",
        witness=SignatureClass.HOST_OBSERVED,
    )
    session = ReplaySession(str(HERE / "two-turn-acked.jsonl"), grammar, ledger)
    session.send("laundered")
    ledger.close()
    reader = LedgerReader(ledger.path, key=ledger.key)
    print("forged host_observed_session_ids:", sorted(reader.host_observed_session_ids()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PY


# --- (c) launder a replay by flipping the ledger's witness after the fact -----
# Strictly cheaper than (b): no adapters.py edit at all. A legally-constructed
# CALLER_ASSERTED ledger is handed to a ReplaySession (which accepts it, because
# the witness is checked once, at construction), and its private witness/key are
# then reassigned. Every subsequent append() mints a correctly-HMAC'd
# host-observed entry under a key the forger chose. HostLedger seals both
# attributes, so this script must raise EvidencePromotionRefused; if it prints a
# laundered session id instead, the seal is gone.
cat > "$agentic/fixtures/native/replay/flip_witness.py" <<'PY'
#!/usr/bin/env python3
"""COUNTERFEIT 23(c): launder a replay by flipping HostLedger's witness."""
from __future__ import annotations

import json
import pathlib
import secrets
import tempfile

from evals.agentic.framework.adapters import (
    HostLedger, JsonPathSpec, LedgerReader, ReplaySession, StreamGrammar,
)
from evals.agentic.framework.contract import EventKind, SignatureClass

HERE = pathlib.Path(__file__).resolve().parent


def main() -> int:
    raw = json.loads(
        (HERE / "synthetic-offline-form.grammar.json").read_text(encoding="utf-8")
    )
    grammar = StreamGrammar(
        name=raw["name"],
        session_ack=JsonPathSpec(**raw["session_ack"]),
        turn_ack=JsonPathSpec(**raw["turn_ack"]),
        usage=JsonPathSpec(**raw["usage"]),
        session_id_field=raw["session_id_field"],
        turn_index_field=raw["turn_index_field"],
    )
    scratch = pathlib.Path(tempfile.mkdtemp(prefix="counterfeit-23c-"))
    ledger = HostLedger(
        scratch / "events.jsonl", run_id="run-counterfeit-23c",
        witness=SignatureClass.CALLER_ASSERTED,
    )
    session = ReplaySession(str(HERE / "two-turn-acked.jsonl"), grammar, ledger)

    # No source edit. Two assignments.
    key = secrets.token_bytes(32)
    ledger._witness = SignatureClass.HOST_OBSERVED
    ledger._key = key

    session.send("laundered")
    ledger.append(
        EventKind.SESSION_ACK, attempt_id="attempt-23c",
        session_id=session.session_id, payload={"source": "laundered"},
    )
    ledger.close()
    reader = LedgerReader(ledger.path, key=key)
    print("forged host_observed_session_ids:", sorted(reader.host_observed_session_ids()))
    print("forged is_verified:", reader.is_verified())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PY

echo "mutate.sh: staged a self-asserted native attempt, defeated ReplaySession's witness guard, and staged the witness-flip laundering in $agentic"
