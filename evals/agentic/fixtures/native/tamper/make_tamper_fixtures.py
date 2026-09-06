#!/usr/bin/env python3
"""Regenerate `fixtures/native/ledgers/*.jsonl` and `fixtures/native/tamper/*.jsonl`.

Run from the repo root:

    python3 evals/agentic/fixtures/native/tamper/make_tamper_fixtures.py

The fixtures are committed, so this script is not run by any test. It is
committed alongside them because *how each tamper was produced* is the load-bearing
part: a fixture whose provenance nobody can reproduce is a fixture nobody can
argue with. Reading this file is how a reviewer checks that
`LedgerReader.verify_chain`'s four tamper classes are being told apart by the
right evidence and not by a giveaway the generator left behind.

Note what is deliberately NOT generated: a genuine `witness=HOST_OBSERVED`
ledger. Its HMACs are only meaningful against a 32-byte run-scoped key, and §5.3
forbids that key ever reaching the workspace. A committed host-observed ledger
would either be unverifiable (no key) or would require committing the key, which
is the forgery this lane exists to prevent. Host-observed ledgers are therefore
built at test time in a temp dir with a freshly minted in-memory key.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import sys
import tempfile
from hashlib import sha256

REPO = pathlib.Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO))

from evals.agentic.framework.adapters import (  # noqa: E402
    HostLedger, _body_of, _chain_message,
)
from evals.agentic.framework.contract import EventKind, SignatureClass  # noqa: E402

NATIVE = REPO / "evals" / "agentic" / "fixtures" / "native"
LEDGERS = NATIVE / "ledgers"
TAMPER = NATIVE / "tamper"

RUN_ID = "run-fixture-genuine"
SESSION_ID = "harness-sess-AAAA"


def _build_genuine() -> list[dict]:
    scratch = pathlib.Path(tempfile.mkdtemp(prefix="agentic-ledger-fixture-"))
    try:
        path = scratch / "events.jsonl"
        ledger = HostLedger(path, run_id=RUN_ID, witness=SignatureClass.CALLER_ASSERTED)
        ledger.append(EventKind.RUN_START, attempt_id=None, session_id=None,
                      payload={"offline": True, "lane": "adapter"})
        ledger.append(EventKind.SESSION_OPEN, attempt_id="attempt-0001", session_id=None,
                      payload={"stream": "replay/two-turn-acked.jsonl"})
        ledger.append(EventKind.SESSION_ACK, attempt_id="attempt-0001", session_id=SESSION_ID,
                      payload={"source": "replayed-stream", "record_index": 0})
        ledger.append(EventKind.TURN_START, attempt_id="attempt-0001", session_id=SESSION_ID,
                      payload={"index": 0, "chars": 12})
        ledger.append(EventKind.TURN_ACK, attempt_id="attempt-0001", session_id=SESSION_ID,
                      payload={"index": 0, "source": "replayed-stream"})
        ledger.append(EventKind.USAGE, attempt_id="attempt-0001", session_id=SESSION_ID,
                      payload={"index": 0, "unknown_fields": ["reasoning_tokens"]})
        ledger.append(EventKind.TURN_END, attempt_id="attempt-0001", session_id=SESSION_ID,
                      payload={"index": 0, "acked": True})
        ledger.append(EventKind.RUN_END, attempt_id=None, session_id=None,
                      payload={"attempts": 1})
        ledger.close()
        return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def _relink(records: list[dict], start: int, *, prev: str) -> list[dict]:
    """Recompute sha256 (and prev_hash) from ``start`` on, as a real forger would.

    A forger has the hash algorithm — it is in this repository. What they do not
    have is the HMAC key, so this relinking produces a chain that
    `verify_chain()` calls intact and `is_verified()` still refuses.
    """
    out = records[:start]
    running = prev
    for record in records[start:]:
        fixed = dict(record)
        fixed["prev_hash"] = running
        body = _body_of(fixed)
        fixed["sha256"] = sha256(_chain_message(running, body)).hexdigest()
        running = fixed["sha256"]
        out.append(fixed)
    return out


def _write(path: pathlib.Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False) + "\n")
    print(f"wrote {path.relative_to(REPO)} ({len(records)} entries)")


def main() -> int:
    genuine = _build_genuine()
    _write(LEDGERS / "genuine-caller-asserted.jsonl", genuine)

    # (1) edited-field: a payload value changed, hash NOT recomputed. The most
    # naive tamper, and the one a plain re-walk catches on its own.
    edited = [dict(r) for r in genuine]
    edited[3] = dict(edited[3])
    edited[3]["payload"] = dict(edited[3]["payload"]) | {"chars": 999999}
    _write(TAMPER / "edited-field.jsonl", edited)

    # (2) deleted-entry: entry 3 removed. Every survivor keeps its own valid
    # hash, so only the index gap plus the broken prev_hash link shows it.
    _write(TAMPER / "deleted-entry.jsonl", [r for i, r in enumerate(genuine) if i != 3])

    # (3) inserted-entry: a fabricated TURN_ACK spliced in after entry 2, with
    # its own hash correctly computed over the real predecessor. Nothing was
    # removed, so the indices stay dense-but-shifted and the break lands on the
    # entry AFTER the splice.
    fabricated = dict(genuine[4])
    fabricated["index"] = 3
    fabricated["event_id"] = "cafe0000-0000-4000-8000-000000000001"
    fabricated["payload"] = {"index": 0, "source": "fabricated-ack"}
    fabricated["prev_hash"] = genuine[2]["sha256"]
    fabricated["sha256"] = sha256(
        _chain_message(fabricated["prev_hash"], _body_of(fabricated))
    ).hexdigest()
    inserted = genuine[:3] + [fabricated] + genuine[3:]
    _write(TAMPER / "inserted-entry.jsonl", inserted)

    # (4) swapped-pair: entries 3 and 4 exchanged, both hashes left untouched.
    swapped = list(genuine)
    swapped[3], swapped[4] = swapped[4], swapped[3]
    _write(TAMPER / "swapped-pair.jsonl", swapped)

    # (5) forged-host-observed: the interesting one. Entry 2 (the SESSION_ACK)
    # is relabelled host-observed with a plausible key_id and 64 hex of noise
    # for a signature, and the whole tail is relinked so the HASH CHAIN IS
    # INTACT. verify_chain().ok is True. What refuses it is the HMAC: a reader
    # holding the run key finds entry 2's signature wrong, is_verified() is
    # False, and signature_class() downgrades it to caller-asserted so
    # assert_native_backed raises. A reader WITHOUT the key also refuses, because
    # is_verified() requires a key. Neither can be talked into blessing it.
    forged = [dict(r) for r in genuine]
    forged[2] = dict(forged[2])
    forged[2]["host_signature"] = {
        "value_class": SignatureClass.HOST_OBSERVED.value,
        "algo": "hmac-sha256",
        "key_id": f"run-{RUN_ID}",
        "value": "de" * 32,
    }
    forged = _relink(forged, 2, prev=genuine[1]["sha256"])
    _write(TAMPER / "forged-host-observed.jsonl", forged)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
