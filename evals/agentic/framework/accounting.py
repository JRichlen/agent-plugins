"""evals.agentic.framework.accounting -- the attempt ledger and conservation
identity (measurement lane, contract §3.5).

Every attempt is counted, including failed/cancelled/faulted/retried and
coordination (worker spawn, verifier run, judge call) attempts. Unknown usage
(`contract.UNKNOWN`) is never silently treated as zero: `sum_usage` and
`cost_of` track a separate `unknown_count` and refuse to fold it into `known`.

No cross-model raw pooling happens here either: `sum_usage`/`cost_of` require
the caller to state `model_id` and raise `CrossModelPoolingRefused` the moment
an attempt's own usage disagrees with it.
"""
from __future__ import annotations

import dataclasses
from collections.abc import Iterable, Mapping
from typing import Any

from .contract import (
    UNKNOWN,
    AccountingLeak,
    ArmRole,
    Attempt,
    ContractError,
    CrossModelPoolingRefused,
    SCORING_VALID_STATES,
    TerminalState,
)

__all__ = [
    "USAGE_FIELDS",
    "Total",
    "MoneyTotal",
    "AttemptLedger",
    "Denominators",
    "sum_usage",
    "cost_of",
    "coordination_attempts",
    "denominators",
]

# The Usage fields that carry a TokenCount/Millis (i.e. `int | UNKNOWN`) value,
# in the order contract.Usage declares them. cost_usd is handled separately
# below because its "unknown" spelling is `None`, not `UNKNOWN` (contract §2.3).
USAGE_FIELDS: tuple[str, ...] = (
    "input_tokens",
    "output_tokens",
    "cache_read_input_tokens",
    "cache_creation_input_tokens",
    "reasoning_tokens",
    "total_tokens",
    "wall_clock_ms",
)


@dataclasses.dataclass(frozen=True, slots=True)
class Total:
    """A sum over a TokenCount/Millis field, honest about what it does not know."""

    known: int
    unknown_count: int
    contributors: int

    @property
    def partial(self) -> bool:
        return self.unknown_count > 0

    def render(self) -> str:
        base = f"{self.known:,}"
        if self.partial:
            return f"{base}+ ({self.unknown_count} of {self.contributors} attempts unknown)"
        return base

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True, slots=True)
class MoneyTotal:
    """A USD sum. Separate from Total because Total.known is an int."""

    known: float
    unknown_count: int
    contributors: int

    @property
    def partial(self) -> bool:
        return self.unknown_count > 0

    def render(self) -> str:
        if self.partial:
            return "not computed"
        return f"${self.known:,.2f}"

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


class AttemptLedger:
    """Every attempt in a run, keyed by attempt_id, insertion order preserved."""

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self._attempts: dict[str, Attempt] = {}
        self._order: list[str] = []

    def add(self, attempt: Attempt) -> None:
        if attempt.attempt_id in self._attempts:
            raise AccountingLeak(
                f"AttemptLedger.add: duplicate attempt_id {attempt.attempt_id!r}"
            )
        self._attempts[attempt.attempt_id] = attempt
        self._order.append(attempt.attempt_id)

    def attempts(self) -> tuple[Attempt, ...]:
        return tuple(self._attempts[i] for i in self._order)

    def by_terminal_state(self) -> Mapping[TerminalState, int]:
        out: dict[TerminalState, int] = {s: 0 for s in TerminalState}
        for a in self.attempts():
            out[a.terminal_state] += 1
        return out

    def by_role(self) -> Mapping[ArmRole, int]:
        out: dict[ArmRole, int] = {r: 0 for r in ArmRole}
        for a in self.attempts():
            out[a.role] += 1
        return out

    def retries(self) -> Mapping[str, tuple[Attempt, ...]]:
        out: dict[str, list[Attempt]] = {}
        for a in self.attempts():
            if a.parent_attempt_id is not None:
                out.setdefault(a.parent_attempt_id, []).append(a)
        return {k: tuple(v) for k, v in out.items()}

    def conserve(self) -> None:
        """Raises AccountingLeak unless every row is accounted for exactly once
        and every parent_attempt_id resolves to a ledger member."""
        attempts = self.attempts()
        total_states = sum(self.by_terminal_state().values())
        if total_states != len(attempts):
            raise AccountingLeak(
                f"AttemptLedger.conserve: sum(by_terminal_state)={total_states} "
                f"!= len(attempts)={len(attempts)}"
            )
        ids = set(self._attempts)
        for a in attempts:
            if a.parent_attempt_id is not None and a.parent_attempt_id not in ids:
                raise AccountingLeak(
                    f"AttemptLedger.conserve: {a.attempt_id!r} has "
                    f"parent_attempt_id {a.parent_attempt_id!r}, which is not a "
                    "member of this ledger"
                )

    def to_dict(self) -> dict[str, Any]:
        return {"run_id": self.run_id, "attempts": [a.to_dict() for a in self.attempts()]}


def _require_model(attempt: Attempt, model_id: str, caller: str) -> None:
    if attempt.usage.model_id != model_id:
        raise CrossModelPoolingRefused(
            f"{caller}: attempt {attempt.attempt_id!r} has usage.model_id "
            f"{attempt.usage.model_id!r}, which does not match the requested "
            f"model_id {model_id!r} -- raw counts are never pooled across models"
        )


def sum_usage(attempts: Iterable[Attempt], field: str, *, model_id: str) -> Total:
    """Sum one TokenCount/Millis field. UNKNOWN never becomes 0; it is tallied
    separately in `unknown_count` and the render() carries the caveat.

    Raises CrossModelPoolingRefused the instant any attempt's usage.model_id
    disagrees with `model_id` -- this is the un-skippable primitive guard;
    analysis.pool_tokens is where the by="model"/"stratum" grouping happens.
    """
    if field not in USAGE_FIELDS:
        raise ContractError(
            f"sum_usage: field must be one of {USAGE_FIELDS!r}, got {field!r}"
        )
    known = 0
    unknown_count = 0
    contributors = 0
    for a in attempts:
        _require_model(a, model_id, "sum_usage")
        contributors += 1
        value = getattr(a.usage, field)
        if value is UNKNOWN:
            unknown_count += 1
        else:
            known += value
    return Total(known=known, unknown_count=unknown_count, contributors=contributors)


def cost_of(attempts: Iterable[Attempt], *, model_id: str) -> MoneyTotal | None:
    """None when the iterable is empty. A None cost_usd on any contributing
    attempt makes the whole total render "not computed", never "$0.00"."""
    attempts = list(attempts)
    if not attempts:
        return None
    known = 0.0
    unknown_count = 0
    contributors = 0
    for a in attempts:
        _require_model(a, model_id, "cost_of")
        contributors += 1
        if a.usage.cost_usd is None:
            unknown_count += 1
        else:
            known += a.usage.cost_usd
    return MoneyTotal(known=known, unknown_count=unknown_count, contributors=contributors)


def coordination_attempts(attempts: Iterable[Attempt]) -> tuple[Attempt, ...]:
    return tuple(a for a in attempts if a.role is ArmRole.COORDINATION)


@dataclasses.dataclass(frozen=True, slots=True)
class Denominators:
    accounting: int
    scoring_valid: int
    scoring_trials: int
    coordination: int
    coordination_total: int
    faults: int
    cancels: int

    def assert_reconciles(self) -> None:
        expected = self.scoring_trials + self.coordination + self.faults + self.cancels
        if self.accounting != expected:
            raise AccountingLeak(
                "Denominators.assert_reconciles: "
                f"accounting={self.accounting} != scoring_trials={self.scoring_trials} "
                f"+ coordination={self.coordination} + faults={self.faults} "
                f"+ cancels={self.cancels} (={expected})"
            )

    def render(self) -> str:
        return (
            f"accounting {self.accounting} / scoring trials {self.scoring_trials} "
            f"/ coordination {self.coordination} / faults {self.faults} "
            f"/ cancels {self.cancels}"
        )

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def denominators(attempts: Iterable[Attempt]) -> Denominators:
    attempts = tuple(attempts)
    accounting = len(attempts)
    scoring_valid = sum(1 for a in attempts if a.terminal_state in SCORING_VALID_STATES)
    coordination_scoring_valid = sum(
        1
        for a in attempts
        if a.role is ArmRole.COORDINATION and a.terminal_state in SCORING_VALID_STATES
    )
    coordination_total = sum(1 for a in attempts if a.role is ArmRole.COORDINATION)
    scoring_trials = scoring_valid - coordination_scoring_valid
    faults = sum(1 for a in attempts if a.terminal_state is TerminalState.FAULT)
    cancels = sum(1 for a in attempts if a.terminal_state is TerminalState.CANCELLED)
    return Denominators(
        accounting=accounting,
        scoring_valid=scoring_valid,
        scoring_trials=scoring_trials,
        coordination=coordination_scoring_valid,
        coordination_total=coordination_total,
        faults=faults,
        cancels=cancels,
    )
