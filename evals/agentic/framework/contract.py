"""evals.agentic.framework.contract — the frozen vocabulary (core lane).

This module has NO imports from any other framework module. It is the interface
every other lane imports, per the implementation contract §2. Its content is the
contract; nothing here is negotiable without an update to
`agent-plugins-implementation-contract.md`.
"""
from __future__ import annotations

import dataclasses
import enum
import hashlib
import json
import re
import types
import typing
import uuid
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any, Iterator

__all__ = [
    # enums (§2.1)
    "TerminalState", "EvidenceClass", "ControlKind", "ArmRole", "AdapterClass",
    "Estimand", "CardKind", "SignatureClass", "EventKind", "GraderKind",
    "ApprovalGate",
    # UNKNOWN sentinel (§2.2)
    "_Unknown", "UNKNOWN", "TokenCount", "Millis",
    # dataclasses (§2.3)
    "Stratum", "Capability", "Usage", "Verdict", "Judgement", "HostSignature",
    "Event", "Attempt", "Card", "Manifest",
    # constants and helpers (§2.4)
    "SCORING_VALID_STATES", "SCORING_INVALID_STATES", "ACCOUNTING_STATES",
    "ALL_IDS", "GENESIS_HASH",
    "canonical_json", "digest", "now_rfc3339", "new_id",
    "LedgerView", "assert_native_backed",
    # exceptions (§2.5)
    "ContractError", "SchemaError", "ValidationError", "UnsupportedKeyword",
    "UnclassifiableRun", "ForgedProvenance", "EvidencePromotionRefused",
    "ApprovalRequired", "FlagNotSupported", "LedgerTampered",
    "NativeProofRequired", "CrossModelPoolingRefused", "InsufficientClusters",
    "MarginMissing", "AccountingLeak", "CoverageGap",
    "ExposureParityViolation", "CatalogUnresolvable", "VacuousVerifier",
    "LeakageDetected",
]


# ---------------------------------------------------------------------------
# 2.5 Exceptions — defined first so everything below can raise them.
# ---------------------------------------------------------------------------

class ContractError(Exception):
    """Base of every exception raised anywhere under evals/agentic/framework."""


class SchemaError(ContractError):
    """A schema document itself is malformed (bad $schema, bad $ref, bad regex)."""


class ValidationError(ContractError):
    """An instance failed to validate against a schema.

    Carries pointer (RFC 6901 against the *instance*), keyword, schema_id, message.
    """

    def __init__(self, pointer: str, keyword: str, schema_id: str, message: str) -> None:
        self.pointer = pointer
        self.keyword = keyword
        self.schema_id = schema_id
        self.message = message
        super().__init__(str(self))

    def __str__(self) -> str:  # noqa: D105
        return f"{self.schema_id}{self.pointer}: {self.keyword}: {self.message}"


class UnsupportedKeyword(ContractError):
    """A schema uses a JSON-Schema keyword outside io.py's supported subset."""


class UnclassifiableRun(ContractError):
    """classify.py was handed a fact combination absent from the truth table."""


class ForgedProvenance(ContractError):
    """An attempt claims native provenance the host ledger does not back (T09)."""


class EvidencePromotionRefused(ContractError):
    """Something attempted to relabel a non-native attempt as native-proven (T31)."""


class ApprovalRequired(ContractError):
    """An action needs an approval token that was not presented."""


class FlagNotSupported(ContractError):
    """A driver would emit a CLI flag the installed binary's --help does not list."""


class LedgerTampered(ContractError):
    """verify_chain() found a bad index in the event ledger."""


class NativeProofRequired(ContractError):
    """reporting.assert_native_claims refused to emit a native-behavior sentence."""


class CrossModelPoolingRefused(ContractError):
    """An aggregation attempted to average raw tokens/costs across models."""


class InsufficientClusters(ContractError):
    """Fewer clusters than min_clusters; no interval can be reported."""


class MarginMissing(ContractError):
    """A noninferiority test ran with no declared margin."""


class AccountingLeak(ContractError):
    """An attempt fell out of every accounting denominator."""


class CoverageGap(ContractError):
    """The corpus does not cover a required plugin/card-kind combination."""


class ExposureParityViolation(ContractError):
    """The baseline and treatment arms were not given equivalent exposure."""


class CatalogUnresolvable(ContractError):
    """A catalog ID does not resolve to an executable (module, class, test)."""


class VacuousVerifier(ContractError):
    """A hidden verifier has no mutation that can drive it from green to red."""


class LeakageDetected(ContractError):
    """A holdout card's content leaked into a non-holdout stratum."""


# ---------------------------------------------------------------------------
# 2.1 Enums
# ---------------------------------------------------------------------------

class TerminalState(enum.Enum):
    DELIVERED = "delivered"
    INCOMPLETE = "incomplete"
    CANCELLED = "cancelled"
    FAULT = "fault"
    TIMEOUT_AFTER_DELIVERY = "timeout-after-delivery"


class EvidenceClass(enum.Enum):
    FRAMEWORK = "framework"
    REAL_FIXTURE = "real-fixture"
    SIMULATED = "simulated"
    NATIVE_PROVEN = "native-proven"
    PAID_REQUIRED = "paid-required"


class ControlKind(enum.Enum):  # BASELINE is deliberately absent
    NOP = "nop"
    INVERSION = "inversion"
    ORACLE = "oracle"
    MUTATION = "mutation"


class ArmRole(enum.Enum):
    TREATMENT = "treatment"
    BASELINE = "baseline"       # no-skill arm — NOT a control
    CONTROL = "control"
    COORDINATION = "coordination"


class AdapterClass(enum.Enum):
    NATIVE = "native"
    REPLAY = "replay"
    STUB = "stub"


class Estimand(enum.Enum):
    FULL_PACKAGE = "full-package"
    GUIDANCE_ONLY = "guidance-only"
    COMPOSITION = "composition"
    VERSION = "version"
    BASELINE = "baseline"


class CardKind(enum.Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEAR_MISS = "near-miss"


class SignatureClass(enum.Enum):
    HOST_OBSERVED = "host-observed"
    CALLER_ASSERTED = "caller-asserted"


class EventKind(enum.Enum):
    RUN_START = "run-start"
    RUN_END = "run-end"
    SESSION_OPEN = "session-open"
    SESSION_ACK = "session-ack"
    TURN_START = "turn-start"
    TURN_ACK = "turn-ack"
    TURN_END = "turn-end"
    SPAWN = "spawn"
    EXIT = "exit"
    CANCEL_ISSUED = "cancel-issued"
    CANCEL_OBSERVED = "cancel-observed"
    LATE_OUTPUT = "late-output"
    APPROVAL_GRANTED = "approval-granted"
    CORRECTION = "correction"
    COMPACTION = "compaction"
    VERIFIER_RUN = "verifier-run"
    USAGE = "usage"


class GraderKind(enum.Enum):
    DETERMINISTIC = "deterministic"
    LLM = "llm"
    HUMAN = "human"


class ApprovalGate(enum.Enum):
    NONE = "none"
    NATIVE_REQUIRED = "native-required"
    PAID_REQUIRED = "paid-required"


# ---------------------------------------------------------------------------
# 2.2 The UNKNOWN sentinel
# ---------------------------------------------------------------------------

class _Unknown:
    __slots__ = ()

    def __repr__(self) -> str:
        return "UNKNOWN"

    def __bool__(self) -> bool:
        return False

    def __eq__(self, other: object) -> bool:
        return other is self

    def __hash__(self) -> int:
        return hash("__evals.agentic.framework.contract.UNKNOWN__")


UNKNOWN: _Unknown = _Unknown()
TokenCount = int | _Unknown
Millis = int | _Unknown


# ---------------------------------------------------------------------------
# to_dict / from_dict machinery shared by every dataclass below.
#
# Generic by design: dispatch is driven by typing.get_type_hints(cls), so each
# dataclass need only define `to_dict`/`from_dict` as one-line delegations.
# from_dict is strict (extra key -> ContractError) and enforces the wire rule
# that a TokenCount/Millis field is either a JSON integer or the literal
# string "UNKNOWN" -- never null (null silently becomes 0 in careless code;
# "UNKNOWN" cannot).
# ---------------------------------------------------------------------------

def _enum_from(enum_cls: type[enum.Enum], value: Any, field_name: str) -> enum.Enum:
    try:
        return enum_cls(value)
    except ValueError as exc:
        raise ContractError(
            f"{field_name}: {value!r} is not a valid {enum_cls.__name__}"
        ) from exc


def _token(raw: Any, field_name: str) -> int | _Unknown:
    if isinstance(raw, str):
        if raw == "UNKNOWN":
            return UNKNOWN
        raise ContractError(
            f"{field_name}: string value must be exactly 'UNKNOWN', got {raw!r}"
        )
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise ContractError(
            f"{field_name}: expected an integer or 'UNKNOWN', got {raw!r}"
        )
    return raw


def _decode_by_hint(hint: Any, raw: Any, field_name: str) -> Any:
    origin = typing.get_origin(hint)

    if origin is types.UnionType or origin is typing.Union:
        args = typing.get_args(hint)
        non_none = [a for a in args if a is not type(None)]
        if raw is None:
            if type(None) in args:
                return None
            raise ContractError(f"{field_name}: null is not allowed here")
        if _Unknown in non_none:
            return _token(raw, field_name)
        if len(non_none) == 1:
            return _decode_by_hint(non_none[0], raw, field_name)
        raise ContractError(f"{field_name}: unsupported union {hint!r}")

    if origin is tuple:
        args = typing.get_args(hint)
        elem_hint = args[0] if args else Any
        if not isinstance(raw, (list, tuple)):
            raise ContractError(f"{field_name}: expected an array")
        return tuple(_decode_by_hint(elem_hint, x, field_name) for x in raw)

    if origin is not None and isinstance(origin, type) and issubclass(origin, Mapping):
        if not isinstance(raw, Mapping):
            raise ContractError(f"{field_name}: expected an object")
        args = typing.get_args(hint)
        if len(args) == 2 and args[1] is not Any:
            _, vhint = args
            return {k: _decode_by_hint(vhint, v, field_name) for k, v in raw.items()}
        return dict(raw)

    if isinstance(hint, type) and dataclasses.is_dataclass(hint):
        if not isinstance(raw, Mapping):
            raise ContractError(f"{field_name}: expected an object for {hint.__name__}")
        return hint.from_dict(raw)  # type: ignore[attr-defined]

    if isinstance(hint, type) and issubclass(hint, enum.Enum):
        return _enum_from(hint, raw, field_name)

    if hint is _Unknown:
        return _token(raw, field_name)

    if hint is str:
        if not isinstance(raw, str):
            raise ContractError(f"{field_name}: expected a string")
        return raw

    if hint is bool:
        if not isinstance(raw, bool):
            raise ContractError(f"{field_name}: expected a boolean")
        return raw

    if hint is int:
        if isinstance(raw, bool) or not isinstance(raw, int):
            raise ContractError(f"{field_name}: expected an integer")
        return raw

    if hint is float:
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise ContractError(f"{field_name}: expected a number")
        return float(raw)

    # Any, or anything not specifically handled: pass through verbatim.
    return raw


def _generic_from_dict(cls: type, d: Mapping[str, Any]) -> Any:
    if not isinstance(d, Mapping):
        raise ContractError(f"{cls.__name__}.from_dict expects a mapping, got {type(d)!r}")
    fields = dataclasses.fields(cls)
    field_names = {f.name for f in fields}
    extra = set(d.keys()) - field_names
    if extra:
        raise ContractError(f"{cls.__name__}: unknown key(s) {sorted(extra)!r}")
    hints = typing.get_type_hints(cls)
    kwargs: dict[str, Any] = {}
    for f in fields:
        if f.name in d:
            kwargs[f.name] = _decode_by_hint(hints[f.name], d[f.name], f.name)
        else:
            has_default = (
                f.default is not dataclasses.MISSING
                or f.default_factory is not dataclasses.MISSING  # type: ignore[misc]
            )
            if not has_default:
                raise ContractError(f"{cls.__name__}: missing required key {f.name!r}")
    return cls(**kwargs)


def _encode_value(v: Any) -> Any:
    if v is UNKNOWN:
        return "UNKNOWN"
    if isinstance(v, enum.Enum):
        return v.value
    if dataclasses.is_dataclass(v) and not isinstance(v, type):
        return v.to_dict()  # type: ignore[attr-defined]
    if isinstance(v, tuple):
        return [_encode_value(x) for x in v]
    if isinstance(v, list):
        return [_encode_value(x) for x in v]
    if isinstance(v, Mapping):
        return {k: _encode_value(x) for k, x in v.items()}
    return v


def _generic_to_dict(obj: Any) -> dict[str, Any]:
    return {f.name: _encode_value(getattr(obj, f.name)) for f in dataclasses.fields(obj)}


# ---------------------------------------------------------------------------
# 2.3 Dataclasses
# ---------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True, slots=True)
class Stratum:
    provider: str
    model: str
    revision: str
    effort: str
    harness: str

    def key(self) -> str:
        return "|".join((self.provider, self.model, self.revision, self.effort, self.harness))

    @staticmethod
    def parse(key: str) -> "Stratum":
        parts = key.split("|")
        if len(parts) != 5:
            raise ContractError(
                f"Stratum.parse: expected 5 '|'-separated fields, got {len(parts)} in {key!r}"
            )
        return Stratum(*parts)

    def to_dict(self) -> dict[str, Any]:
        return _generic_to_dict(self)

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "Stratum":
        return _generic_from_dict(cls, d)


@dataclasses.dataclass(frozen=True, slots=True)
class Capability:
    name: str
    kind: str
    source_plugin: str | None
    generic_equivalent: str | None

    def to_dict(self) -> dict[str, Any]:
        return _generic_to_dict(self)

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "Capability":
        return _generic_from_dict(cls, d)


@dataclasses.dataclass(frozen=True, slots=True)
class Usage:
    model_id: str
    reported_by: str
    input_tokens: TokenCount
    output_tokens: TokenCount
    cache_read_input_tokens: TokenCount
    cache_creation_input_tokens: TokenCount
    reasoning_tokens: TokenCount
    total_tokens: TokenCount
    wall_clock_ms: Millis
    cost_usd: float | None

    _TOKEN_FIELDS: typing.ClassVar[tuple[str, ...]] = (
        "input_tokens", "output_tokens", "cache_read_input_tokens",
        "cache_creation_input_tokens", "reasoning_tokens", "total_tokens",
        "wall_clock_ms",
    )

    @staticmethod
    def from_stream(d: Mapping[str, Any], model_id: str, reported_by: str) -> "Usage":
        def field(name: str) -> int | _Unknown:
            if name not in d or d[name] is None:
                return UNKNOWN
            raw = d[name]
            if isinstance(raw, str) and raw == "UNKNOWN":
                return UNKNOWN
            if isinstance(raw, bool) or not isinstance(raw, int):
                raise ContractError(
                    f"Usage.from_stream: {name} must be an int or absent/None/'UNKNOWN', "
                    f"got {raw!r}"
                )
            return raw

        raw_cost = d.get("cost_usd")
        if raw_cost is not None:
            if isinstance(raw_cost, bool) or not isinstance(raw_cost, (int, float)):
                raise ContractError(f"Usage.from_stream: cost_usd must be numeric or None, got {raw_cost!r}")
            cost = float(raw_cost)
        else:
            cost = None

        return Usage(
            model_id=model_id,
            reported_by=reported_by,
            input_tokens=field("input_tokens"),
            output_tokens=field("output_tokens"),
            cache_read_input_tokens=field("cache_read_input_tokens"),
            cache_creation_input_tokens=field("cache_creation_input_tokens"),
            reasoning_tokens=field("reasoning_tokens"),
            total_tokens=field("total_tokens"),
            wall_clock_ms=field("wall_clock_ms"),
            cost_usd=cost,
        )

    def unknown_fields(self) -> tuple[str, ...]:
        return tuple(name for name in self._TOKEN_FIELDS if getattr(self, name) is UNKNOWN)

    @property
    def any_unknown(self) -> bool:
        return bool(self.unknown_fields())

    def to_dict(self) -> dict[str, Any]:
        return _generic_to_dict(self)

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "Usage":
        return _generic_from_dict(cls, d)


@dataclasses.dataclass(frozen=True, slots=True)
class Verdict:
    passed: bool | None
    verifier_id: str
    reason: str
    hack_class: str | None = None
    evidence_digest: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _generic_to_dict(self)

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "Verdict":
        return _generic_from_dict(cls, d)


@dataclasses.dataclass(frozen=True, slots=True)
class Judgement:
    judgement_id: str
    attempt_id: str
    grader_id: str
    grader_kind: GraderKind
    label: str
    rationale: str
    sample_hash: str
    protected_effect: bool | None
    at: str

    def to_dict(self) -> dict[str, Any]:
        return _generic_to_dict(self)

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "Judgement":
        return _generic_from_dict(cls, d)


@dataclasses.dataclass(frozen=True, slots=True)
class HostSignature:
    value_class: SignatureClass
    algo: str
    key_id: str | None
    value: str | None

    def to_dict(self) -> dict[str, Any]:
        return _generic_to_dict(self)

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "HostSignature":
        return _generic_from_dict(cls, d)


@dataclasses.dataclass(frozen=True, slots=True)
class Event:
    index: int
    event_id: str
    run_id: str
    attempt_id: str | None
    session_id: str | None
    kind: EventKind
    at: str
    payload: Mapping[str, Any]
    prev_hash: str
    sha256: str
    host_signature: HostSignature

    def to_dict(self) -> dict[str, Any]:
        return _generic_to_dict(self)

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "Event":
        return _generic_from_dict(cls, d)


@dataclasses.dataclass(frozen=True, slots=True)
class Attempt:
    attempt_id: str
    run_id: str
    card_id: str
    arm_id: str
    role: ArmRole
    control_kind: ControlKind | None
    parent_attempt_id: str | None
    terminal_state: TerminalState
    evidence_class: EvidenceClass
    adapter_class: AdapterClass
    requested: Stratum
    realized: Stratum
    fallback_flags: tuple[str, ...]
    usage: Usage
    outcome: Verdict
    adoption: Verdict
    started_at: str
    ended_at: str
    session_id: str | None
    event_ids: tuple[str, ...]
    arrived_after_terminal: bool
    notes: str = ""

    def __post_init__(self) -> None:
        has_control_kind = self.control_kind is not None
        is_control_role = self.role is ArmRole.CONTROL
        if has_control_kind != is_control_role:
            raise ContractError(
                "Attempt: (control_kind is not None) must equal (role is ArmRole.CONTROL); "
                f"got role={self.role!r} control_kind={self.control_kind!r}"
            )

    @property
    def claims_native(self) -> bool:
        return self.session_id is not None or self.evidence_class is EvidenceClass.NATIVE_PROVEN

    @property
    def scoring_valid(self) -> bool:
        return self.terminal_state in SCORING_VALID_STATES

    def to_dict(self) -> dict[str, Any]:
        return _generic_to_dict(self)

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "Attempt":
        return _generic_from_dict(cls, d)


@dataclasses.dataclass(frozen=True, slots=True)
class Card:
    card_id: str
    plugin: str
    kind: CardKind
    task_path: str
    outcome_verifier: str
    adoption_verifier: str
    pass_fixture: str
    fail_fixture: str
    expected_boundary_verdict: str
    capabilities: tuple[Capability, ...]
    mutations: tuple[str, ...]
    holdout: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _generic_to_dict(self)

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "Card":
        return _generic_from_dict(cls, d)


@dataclasses.dataclass(frozen=True, slots=True)
class Manifest:
    run_id: str
    created_at: str
    git_commit: str
    branch: str
    offline: bool
    toolchain: Mapping[str, str]
    lanes: tuple[str, ...]
    estimands: tuple[Estimand, ...]
    noninferiority_margin: float
    min_valid: int
    min_clusters: int
    planned_n: Mapping[str, int]
    holdout_seed: int
    catalog_digest: str
    skipped: tuple[Mapping[str, str], ...]
    approvals: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return _generic_to_dict(self)

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "Manifest":
        return _generic_from_dict(cls, d)


# ---------------------------------------------------------------------------
# 2.4 Constants and helpers
# ---------------------------------------------------------------------------

SCORING_VALID_STATES: frozenset[TerminalState] = frozenset(
    {TerminalState.DELIVERED, TerminalState.INCOMPLETE, TerminalState.TIMEOUT_AFTER_DELIVERY}
)
SCORING_INVALID_STATES: frozenset[TerminalState] = frozenset(
    {TerminalState.FAULT, TerminalState.CANCELLED}
)
ACCOUNTING_STATES: frozenset[TerminalState] = frozenset(TerminalState)
ALL_IDS: tuple[str, ...] = tuple(f"T{i:02d}" for i in range(1, 53))
GENESIS_HASH: str = "0" * 64


def canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj)).hexdigest()


def now_rfc3339() -> str:
    dt = datetime.now(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


class LedgerView(typing.Protocol):
    """What contract.py may know about a ledger without importing adapters.py."""

    def has_event(self, event_id: str) -> bool: ...

    def session_ids(self) -> frozenset[str]:
        """EVERY session id in the ledger, host-observed and caller-asserted alike.

        A header statistic. NEVER the native gate — see host_observed_session_ids().
        """
        ...

    def host_observed_session_ids(self) -> frozenset[str]:
        """Only ids carried by a SESSION_ACK event whose signature_class is HOST_OBSERVED."""
        ...

    def is_verified(self) -> bool: ...

    def signature_class(self, event_id: str) -> SignatureClass | None: ...


def assert_native_backed(attempt: Attempt, ledger: LedgerView) -> None:
    """T09: refuse an attempt's claim of native provenance unless the ledger backs it.

    Raises ForgedProvenance when the attempt claims native provenance (a non-None
    session_id, a non-empty event_ids tuple, or evidence_class == NATIVE_PROVEN) that
    the ledger does not corroborate: an unverified chain, an event_id absent from the
    ledger, an event whose signature_class is CALLER_ASSERTED rather than
    HOST_OBSERVED, a session_id absent from host_observed_session_ids(), or a
    NATIVE_PROVEN evidence_class backed by neither a session id nor any event id.
    """
    if not attempt.claims_native:
        return

    if not ledger.is_verified():
        raise ForgedProvenance(
            f"{attempt.attempt_id}: claims native provenance but the ledger chain is not verified"
        )

    if attempt.session_id is not None and attempt.session_id not in ledger.host_observed_session_ids():
        raise ForgedProvenance(
            f"{attempt.attempt_id}: session_id {attempt.session_id!r} is not in "
            "ledger.host_observed_session_ids()"
        )

    for event_id in attempt.event_ids:
        if not ledger.has_event(event_id):
            raise ForgedProvenance(
                f"{attempt.attempt_id}: event_id {event_id!r} does not exist in the ledger"
            )
        sig = ledger.signature_class(event_id)
        if sig is not SignatureClass.HOST_OBSERVED:
            raise ForgedProvenance(
                f"{attempt.attempt_id}: event_id {event_id!r} has signature_class "
                f"{sig!r}, not HOST_OBSERVED"
            )

    if (
        attempt.evidence_class is EvidenceClass.NATIVE_PROVEN
        and attempt.session_id is None
        and not attempt.event_ids
    ):
        raise ForgedProvenance(
            f"{attempt.attempt_id}: evidence_class is NATIVE_PROVEN but the attempt "
            "carries neither a session_id nor any event_ids for the ledger to back"
        )
