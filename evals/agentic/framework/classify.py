"""evals.agentic.framework.classify — the terminal-state classifier (core lane,
contract §3.3).

`classify()` is a total, disjoint decision procedure over observable run facts.
There is NO `else: return FAULT` (or any other) tail: every branch is an
explicit, named predicate, and a fact combination this module cannot make
sense of (a genuine contradiction -- e.g. a process that both exited AND was
signalled, or a verifier claiming to have gone green with no deliverable to
verify) raises `UnclassifiableRun` rather than being coerced into some
default state. `fixtures/classify/truth-table.json` is golden data exercised
by `tests/test_classify.py`, not the mechanism `classify()` itself consults.
"""
from __future__ import annotations

import dataclasses
import pathlib
from collections.abc import Mapping
from typing import Any

from . import io
from .contract import (
    SCORING_VALID_STATES,
    ContractError,
    TerminalState,
    UnclassifiableRun,
    digest,
)

__all__ = [
    "RunFacts",
    "TruthRow",
    "TRUTH_TABLE_PATH",
    "load_truth_table",
    "classify",
    "counts_as_fault",
    "counts_in_scoring",
    "counts_in_accounting",
    "facts_digest",
]

TRUTH_TABLE_PATH: str = "evals/agentic/fixtures/classify/truth-table.json"


@dataclasses.dataclass(frozen=True, slots=True)
class RunFacts:
    exit_status: int | None
    signalled: str | None
    deliverable_present: bool
    verifier_verdict: bool | None
    verifier_green_at_ms: int | None
    cancel_issued_at_ms: int | None
    wall_clock_ms: int
    wall_clock_limit_ms: int
    transport_error: str | None
    bytes_out: int

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "RunFacts":
        field_names = {f.name for f in dataclasses.fields(cls)}
        given = set(d.keys())
        extra = given - field_names
        if extra:
            raise ContractError(f"RunFacts.from_dict: unknown key(s) {sorted(extra)!r}")
        missing = field_names - given
        if missing:
            raise ContractError(f"RunFacts.from_dict: missing required key(s) {sorted(missing)!r}")
        return cls(**{name: d[name] for name in field_names})

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def facts_digest(facts: RunFacts) -> str:
    return digest(facts.to_dict())


@dataclasses.dataclass(frozen=True, slots=True)
class TruthRow:
    facts: RunFacts
    expected: TerminalState
    note: str


def _resolve(path: str | pathlib.Path) -> pathlib.Path:
    p = pathlib.Path(path)
    return p if p.is_absolute() else io.repo_root() / p


def load_truth_table(path: str | pathlib.Path = TRUTH_TABLE_PATH) -> tuple[TruthRow, ...]:
    raw = io.load_json(_resolve(path))
    rows_raw = raw["rows"] if isinstance(raw, Mapping) else raw
    rows: list[TruthRow] = []
    for entry in rows_raw:
        facts = RunFacts.from_dict(entry["facts"])
        expected = TerminalState(entry["expected"])
        note = entry.get("note", "")
        rows.append(TruthRow(facts=facts, expected=expected, note=note))
    return tuple(rows)


# ---------------------------------------------------------------------------
# The classifier itself.
# ---------------------------------------------------------------------------

def _contradiction(facts: RunFacts) -> str | None:
    """Fact combinations that cannot describe a real run. Anything caught
    here raises UnclassifiableRun rather than being routed to some state by
    accident."""
    if facts.verifier_green_at_ms is not None and not facts.deliverable_present:
        return "verifier_green_at_ms is set but deliverable_present is False"
    if facts.verifier_green_at_ms is not None and facts.verifier_verdict is not True:
        return "verifier_green_at_ms is set but verifier_verdict is not True"
    if facts.exit_status is not None and facts.signalled is not None:
        return "a process cannot both report an exit_status and have been signalled"
    if facts.cancel_issued_at_ms is not None and facts.cancel_issued_at_ms > facts.wall_clock_ms:
        return "cancel_issued_at_ms postdates wall_clock_ms -- a cancel cannot arrive after the run ended"
    if facts.wall_clock_ms < 0 or facts.wall_clock_limit_ms < 0 or facts.bytes_out < 0:
        return "a duration or byte count is negative"
    return None


def classify(facts: RunFacts) -> TerminalState:
    """Total and disjoint over the fact patterns below. No default tail:
    anything that reaches the end of this function without matching a named
    rule raises UnclassifiableRun."""
    reason = _contradiction(facts)
    if reason is not None:
        raise UnclassifiableRun(f"{reason} (facts_digest={facts_digest(facts)})")

    # Rule 1 -- a user-issued cancel always wins, even over a simultaneous
    # transport error or signal. T02/T03: "a user stop is not an
    # infrastructure excuse."
    cancelled = (
        facts.cancel_issued_at_ms is not None
        and facts.wall_clock_ms >= facts.cancel_issued_at_ms
    )
    if cancelled:
        return TerminalState.CANCELLED

    # Rule 2 -- the deliverable was already verified green, inside the
    # budget, before the harness's own end-of-budget SIGKILL/timeout landed.
    # This must be checked BEFORE the fault rules below: the same SIGKILL
    # that enforces the wall-clock limit must not be read as an infra fault
    # when the work was already done and verified.
    timeout_after_delivery = (
        facts.deliverable_present
        and facts.verifier_verdict is True
        and facts.verifier_green_at_ms is not None
        and facts.verifier_green_at_ms <= facts.wall_clock_limit_ms
        and facts.wall_clock_ms > facts.wall_clock_limit_ms
    )
    if timeout_after_delivery:
        return TerminalState.TIMEOUT_AFTER_DELIVERY

    # Rule 3 -- a transport error with zero bytes out: the call never
    # completed. Never INCOMPLETE: crediting a start that never happened is
    # exactly the failure this rule exists to stop.
    transport_fault = bool(facts.transport_error) and facts.bytes_out == 0
    if transport_fault:
        return TerminalState.FAULT

    # Rule 4 -- the process was never reaped (no exit_status, no signal) and
    # nothing above explains why: the harness itself failed to observe the
    # outcome.
    if facts.exit_status is None and facts.signalled is None:
        return TerminalState.FAULT

    # Rule 5 -- killed by a signal that was not our own cancel.
    if facts.signalled is not None:
        return TerminalState.FAULT

    # Rule 6 -- reaped with a non-zero exit status.
    if facts.exit_status != 0:
        return TerminalState.FAULT

    # From here exit_status == 0: a clean, observed, non-cancelled exit.
    if facts.wall_clock_ms <= facts.wall_clock_limit_ms:
        return TerminalState.DELIVERED if facts.deliverable_present else TerminalState.INCOMPLETE

    # Ran past the wall-clock limit on a clean exit with no verified-green
    # deliverable to exempt it (that case was Rule 2): the agent did not stop
    # properly, and did not finish either.
    return TerminalState.INCOMPLETE


def counts_as_fault(state: TerminalState) -> bool:
    return state is TerminalState.FAULT


def counts_in_scoring(state: TerminalState) -> bool:
    return state in SCORING_VALID_STATES


def counts_in_accounting(state: TerminalState) -> bool:
    return True
