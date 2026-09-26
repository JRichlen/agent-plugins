"""evals.agentic.fixtures.measurement.builders -- shared Attempt/Usage/Verdict
construction helpers for the measurement lane's tests (test_accounting.py,
test_analysis.py, test_reporting.py). Not a test module itself; owned by the
measurement lane under fixtures/measurement/**.

Fixtures under this directory are compact JSON specs (row counts, per-card
pass/fail patterns) rather than fully-spelled-out Attempt records one field at
a time -- most fields (session_id, event_ids, timestamps, ...) are irrelevant
to the statistic under test and a hand-written 100-row attempt.schema.json
document would be mostly filler. `attempts_from_conservation_rows` and the
other loaders below turn such a spec into real `contract.Attempt` objects,
which is what every measurement test actually exercises.
"""
from __future__ import annotations

import itertools
from collections.abc import Mapping, Sequence
from typing import Any

from evals.agentic.framework.contract import (
    AdapterClass,
    ArmRole,
    Attempt,
    ControlKind,
    EvidenceClass,
    Stratum,
    TerminalState,
    Usage,
    Verdict,
)

_COUNTER = itertools.count()

DEFAULT_STRATUM = Stratum(
    provider="anthropic", model="claude-sonnet-5", revision="6d5342c",
    effort="high", harness="claude-code/2.1.263",
)


def make_usage(*, model_id: str = "claude-sonnet-5", **overrides: Any) -> Usage:
    fields: dict[str, Any] = dict(
        model_id=model_id, reported_by="claude-cli/2.1.263",
        input_tokens=100, output_tokens=200, cache_read_input_tokens=0,
        cache_creation_input_tokens=0, reasoning_tokens=0, total_tokens=300,
        wall_clock_ms=1000, cost_usd=0.01,
    )
    fields.update(overrides)
    return Usage(**fields)


def make_verdict(*, passed: bool | None = True, verifier_id: str = "v", reason: str = "ok", **overrides: Any) -> Verdict:
    fields: dict[str, Any] = dict(
        passed=passed, verifier_id=verifier_id, reason=reason,
        hack_class=None, evidence_digest=None,
    )
    fields.update(overrides)
    return Verdict(**fields)


def make_attempt(
    *,
    card_id: str = "fixture-pos-01",
    arm_id: str = "treatment",
    role: ArmRole = ArmRole.TREATMENT,
    control_kind: ControlKind | None = None,
    terminal_state: TerminalState = TerminalState.DELIVERED,
    outcome: bool | None | Verdict = True,
    adoption: bool | None | Verdict = True,
    usage: Usage | None = None,
    requested: Stratum | None = None,
    realized: Stratum | None = None,
    fallback_flags: Sequence[str] = (),
    parent_attempt_id: str | None = None,
    evidence_class: EvidenceClass = EvidenceClass.FRAMEWORK,
    adapter_class: AdapterClass = AdapterClass.STUB,
    session_id: str | None = None,
    event_ids: Sequence[str] = (),
    arrived_after_terminal: bool = False,
    run_id: str = "run-fixture",
    attempt_id: str | None = None,
    notes: str = "",
) -> Attempt:
    n = next(_COUNTER)
    requested = requested or DEFAULT_STRATUM
    realized = realized or requested
    usage = usage if usage is not None else make_usage(model_id=realized.model)
    outcome_v = outcome if isinstance(outcome, Verdict) else make_verdict(passed=outcome, verifier_id="outcome-v")
    adoption_v = adoption if isinstance(adoption, Verdict) else make_verdict(passed=adoption, verifier_id="adoption-v")
    return Attempt(
        attempt_id=attempt_id or f"attempt-{n:06d}",
        run_id=run_id,
        card_id=card_id,
        arm_id=arm_id,
        role=role,
        control_kind=control_kind,
        parent_attempt_id=parent_attempt_id,
        terminal_state=terminal_state,
        evidence_class=evidence_class,
        adapter_class=adapter_class,
        requested=requested,
        realized=realized,
        fallback_flags=tuple(fallback_flags),
        usage=usage,
        outcome=outcome_v,
        adoption=adoption_v,
        started_at="2026-09-06T00:00:00.000Z",
        ended_at="2026-09-06T00:00:01.000Z",
        session_id=session_id,
        event_ids=tuple(event_ids),
        arrived_after_terminal=arrived_after_terminal,
        notes=notes,
    )


_STATE_BY_NAME = {s.value: s for s in TerminalState}


def attempts_from_conservation_rows(rows: Sequence[Mapping[str, Any]]) -> list[Attempt]:
    """Turns benchmark-spec §1.2's compact row spec
    ({"n": 65, "terminal_state": "delivered", "coordination_n": 2}, ...) into
    real Attempt objects: `n - coordination_n` role=TREATMENT rows and
    `coordination_n` role=COORDINATION rows per terminal state."""
    out: list[Attempt] = []
    for row in rows:
        state = _STATE_BY_NAME[row["terminal_state"]]
        total = int(row["n"])
        coord = int(row.get("coordination_n", 0))
        for _ in range(total - coord):
            out.append(make_attempt(terminal_state=state, role=ArmRole.TREATMENT))
        for _ in range(coord):
            out.append(make_attempt(terminal_state=state, role=ArmRole.COORDINATION))
    return out


def attempts_for_card(
    card_id: str,
    outcomes: Sequence[str],
    *,
    adoption: Sequence[bool | None] | None = None,
    score: str = "outcome",
) -> list[Attempt]:
    """outcomes is a sequence of "pass" | "fail" | "fault" | "cancel", one per
    trial -- the vocabulary benchmark-spec §3's worked examples use directly
    ("3 pass, 1 fail, 1 fault")."""
    out: list[Attempt] = []
    for i, o in enumerate(outcomes):
        adopt = adoption[i] if adoption is not None else True
        if o == "pass":
            out.append(make_attempt(card_id=card_id, terminal_state=TerminalState.DELIVERED, outcome=True, adoption=adopt))
        elif o == "fail":
            out.append(make_attempt(card_id=card_id, terminal_state=TerminalState.DELIVERED, outcome=False, adoption=adopt))
        elif o == "fault":
            out.append(make_attempt(card_id=card_id, terminal_state=TerminalState.FAULT, outcome=None, adoption=None))
        elif o == "cancel":
            out.append(make_attempt(card_id=card_id, terminal_state=TerminalState.CANCELLED, outcome=None, adoption=None))
        else:
            raise ValueError(f"attempts_for_card: unknown outcome token {o!r}")
    return out
