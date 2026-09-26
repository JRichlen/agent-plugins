"""evals.agentic.framework.analysis -- estimands, matched pairs, and clustered
uncertainty (measurement lane, contract §3.6; formulas in
agent-plugins-benchmark-spec.md).

The card is the cluster unit throughout. Raw token pooling across models is
refused unless the caller explicitly stratifies (§8 of the benchmark spec).
Every randomness source takes an explicit seed (`random.Random(seed)` only,
never the global RNG), and every interval function returns
`unavailable_reason="insufficient clusters: ..."` rather than a narrow
interval when the cluster count is below the floor.

Deviations from the literal contract §3.6 signatures, reported explicitly per
the task brief's instruction rather than silently:

* `any_pass`, `all_pass`, `any_all_rates` and `card_rate` all gained an
  optional `score: str = "outcome"` keyword (all but `card_rate`, which the
  contract already types with one). The frozen signatures for the first three
  take only `trials`/`cards` with no way to select outcome vs adoption, but
  benchmark-spec §3's own text ("whose SCORE verdict is pass") and T40's
  requirement that "everything in this section applies to each [score]
  separately" are unsatisfiable without one. The added keyword defaults to
  "outcome" so every call written against the literal contract signature
  still works unchanged.
* `card_rate` additionally gained an optional `min_valid: int = 1` keyword
  (permissive by default) so a caller holding a run manifest's `min_valid`
  can produce the "starved" wording benchmark-spec §7 requires; the contract
  lists `min_valid` only on `Manifest`, not threaded through this function.
* A small `rate_of` helper is exported alongside the frozen names so
  `reporting.py` (same lane) can build zero-denominator-safe `Rate`s for the
  2x2 cells without a second implementation of the zero-denominator rule.
  `rate_of` additionally gained an optional `min_valid: int = 1` keyword for
  the same reason `card_rate` did.
* `Rate` gained a fifth field, `unevaluated: int = 0` (defaulted, so every
  4-positional-argument construction already in this module keeps working
  unchanged). benchmark-spec §5: a trial whose verifier never ran is a third
  value, counted separately, "never folded into n01/n00" -- `card_rate` must
  be able to say how many trials it excluded for that reason, distinctly from
  the FAULT/CANCELLED trials `_scoring_valid` already excludes.
* `difference_interval` no longer takes `pairs: Sequence[Pair]`; it takes the
  raw `treatment`/`baseline` attempt sequences directly (same shape as
  `matched_pairs`'s own parameters). benchmark-spec §4.1 defines
  `Delta_full(c) = p_T(c) - p_B(c)`, each side its OWN card_rate over its OWN
  scoring-valid, non-fallback trials for that card -- a quantity `Pair`
  (exactly one attempt per side) cannot carry once a card has more than one
  trial per arm, which is the normal shape of a multi-repeat run and the
  literal shape of the spec's own §4.1 worked example (card c4: 3/4 valid vs
  3/5). `matched_pairs` is still called internally, but now only to decide
  which cards belong to the matched set `C` (a card whose only attempts on
  one side are excluded by role/fallback/scoring-validity is dropped from
  `C`, never zero-filled) -- never to source the trials the rate is computed
  over, which was the actual defect: index-position pairing silently
  truncated the larger arm to the smaller arm's count. `seed` stays a
  required keyword for signature stability even though it is unused: the
  interval is now `cluster_t_interval` over the per-card deltas (matching
  benchmark-spec §6.2/§6.4's own worked examples for this exact estimand),
  which is deterministic, not a bootstrap.
"""
from __future__ import annotations

import dataclasses
import math
import random
from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import Any

from .accounting import Total, USAGE_FIELDS, sum_usage
from .contract import (
    ArmRole,
    Attempt,
    ContractError,
    CrossModelPoolingRefused,
    MarginMissing,
    SCORING_VALID_STATES,
    Stratum,
    TerminalState,
)

__all__ = [
    "Rate",
    "rate_of",
    "Interval",
    "NoninferiorityResult",
    "Pair",
    "Unmatched",
    "stratum_of",
    "group_by_stratum",
    "derive_fallback_flags",
    "matched_pairs",
    "any_pass",
    "all_pass",
    "any_all_rates",
    "card_rate",
    "pool_tokens",
    "icc",
    "icc_raw",
    "design_effect",
    "wilson_interval",
    "wilson_with_cluster_inflation",
    "cluster_bootstrap",
    "cluster_t_interval",
    "difference_interval",
    "noninferiority",
]


# ---------------------------------------------------------------------------
# Rate -- the zero-denominator-safe primitive every renderer uses.
# ---------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True, slots=True)
class Rate:
    numerator: int
    denominator: int
    value: float | None
    unavailable_reason: str | None
    unevaluated: int = 0

    def render(self) -> str:
        if self.value is None:
            return f"unavailable ({self.unavailable_reason})"
        return f"{self.value:.4f} ({self.numerator}/{self.denominator})"

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def rate_of(
    numerator: int, denominator: int, *, min_valid: int = 1, unavailable_reason: str | None = None
) -> Rate:
    if denominator <= 0:
        return Rate(numerator, denominator, None, unavailable_reason or "no valid samples")
    if denominator < min_valid:
        return Rate(
            numerator, denominator, None,
            unavailable_reason or f"starved: {denominator} valid < min_valid {min_valid}",
        )
    return Rate(numerator, denominator, numerator / denominator, None)


def _verdict_of(attempt: Attempt, score: str) -> bool | None:
    if score == "outcome":
        return attempt.outcome.passed
    if score == "adoption":
        return attempt.adoption.passed
    raise ContractError(f"score must be 'outcome' or 'adoption', got {score!r}")


def _scoring_valid(trials: Sequence[Attempt]) -> list[Attempt]:
    return [t for t in trials if t.terminal_state in SCORING_VALID_STATES]


def _zero_denominator_reason(trials: Sequence[Attempt]) -> str:
    n_total = len(trials)
    if n_total == 0:
        return "no trials"
    n_fault = sum(1 for t in trials if t.terminal_state is TerminalState.FAULT)
    if n_fault == n_total:
        return f"no valid samples: {n_fault}/{n_total} FAULT"
    n_cancel = sum(1 for t in trials if t.terminal_state is TerminalState.CANCELLED)
    if n_cancel == n_total:
        return f"no valid samples: {n_cancel}/{n_total} CANCELLED"
    return f"no valid samples: {n_total}/{n_total} invalid"


# ---------------------------------------------------------------------------
# §3 -- card-level any-pass / all-pass
# ---------------------------------------------------------------------------

def _evaluated(trials: Sequence[Attempt], score: str) -> list[Attempt]:
    """benchmark-spec §5: an attempt whose SCORE verdict is None (the verifier
    never ran) is a third value -- excluded from N, never folded into a
    fail. Scoring-invalid (FAULT/CANCELLED) trials are excluded upstream by
    `_scoring_valid`; this only removes the additionally-unevaluated ones."""
    return [t for t in trials if _verdict_of(t, score) is not None]


def card_rate(trials: Sequence[Attempt], score: str = "outcome", *, min_valid: int = 1) -> Rate:
    valid = _scoring_valid(trials)
    if not valid:
        return Rate(0, 0, None, _zero_denominator_reason(trials), unevaluated=0)
    evaluated = _evaluated(valid, score)
    unevaluated_n = len(valid) - len(evaluated)
    if not evaluated:
        return Rate(
            0, 0, None,
            f"no evaluated verdicts: {len(valid)} scoring-valid trial(s), the "
            "verifier never ran",
            unevaluated=unevaluated_n,
        )
    if len(evaluated) < min_valid:
        return Rate(
            0, 0, None,
            f"starved: {len(evaluated)} valid < min_valid {min_valid}",
            unevaluated=unevaluated_n,
        )
    passes = sum(1 for t in evaluated if _verdict_of(t, score) is True)
    return Rate(passes, len(evaluated), passes / len(evaluated), None, unevaluated=unevaluated_n)


def any_pass(trials: Sequence[Attempt], score: str = "outcome") -> bool | None:
    valid = _scoring_valid(trials)
    evaluated = _evaluated(valid, score)
    if not evaluated:
        return None
    return any(_verdict_of(t, score) is True for t in evaluated)


def all_pass(trials: Sequence[Attempt], score: str = "outcome") -> bool | None:
    valid = _scoring_valid(trials)
    evaluated = _evaluated(valid, score)
    if not evaluated:
        return None
    return all(_verdict_of(t, score) is True for t in evaluated)


def any_all_rates(
    cards: Mapping[str, Sequence[Attempt]], score: str = "outcome"
) -> tuple[Rate, Rate]:
    any_num = 0
    all_num = 0
    denom = 0
    for trials in cards.values():
        a = any_pass(trials, score)
        if a is None:
            continue
        denom += 1
        if a:
            any_num += 1
        if all_pass(trials, score):
            all_num += 1
    if denom == 0:
        reason = "no cards with a defined verdict"
        return Rate(0, 0, None, reason), Rate(0, 0, None, reason)
    return (
        Rate(any_num, denom, any_num / denom, None),
        Rate(all_num, denom, all_num / denom, None),
    )


# ---------------------------------------------------------------------------
# §2 -- strata and matched pairs
# ---------------------------------------------------------------------------

def stratum_of(attempt: Attempt) -> Stratum:
    return attempt.realized


def group_by_stratum(attempts: Iterable[Attempt]) -> Mapping[Stratum, tuple[Attempt, ...]]:
    out: dict[Stratum, list[Attempt]] = {}
    for a in attempts:
        out.setdefault(stratum_of(a), []).append(a)
    return {k: tuple(v) for k, v in out.items()}


@dataclasses.dataclass(frozen=True, slots=True)
class Pair:
    card_id: str
    treatment: Attempt
    baseline: Attempt
    stratum: Stratum


@dataclasses.dataclass(frozen=True, slots=True)
class Unmatched:
    card_id: str
    side: str  # "treatment" | "baseline"
    reason: str


_STRATUM_FIELDS: tuple[str, ...] = ("provider", "model", "revision", "effort", "harness")


def derive_fallback_flags(requested: Stratum, realized: Stratum) -> tuple[str, ...]:
    """benchmark-spec §2: fallback_flags is "the tuple of fields where they
    [requested and realized] differ, in that fixed field order" -- Stratum's
    own declared field order. Not a contract.py addition (out of this lane's
    ownership); matched_pairs below recomputes and enforces it rather than
    trusting the attempt's own recorded value, since a caller can currently
    write fallback_flags=() while requested != realized and nothing catches
    it (a forged/stale fallback -- benchmark-spec §2's silent-fallback
    failure mode, exactly)."""
    return tuple(f for f in _STRATUM_FIELDS if getattr(requested, f) != getattr(realized, f))


def matched_pairs(
    treatment: Iterable[Attempt], baseline: Iterable[Attempt]
) -> tuple[tuple[Pair, ...], tuple[Unmatched, ...]]:
    """Group both sides by card_id, then pair attempts within a card in
    encounter order. A pair is made only when: both attempts are scoring-valid
    (benchmark-spec §1.1: FAULT/CANCELLED are "transport weather, not
    evidence" and never enter a comparison); both sides' recorded
    fallback_flags match what requested-vs-realized actually derives (a
    mismatch is a hard ContractError -- forged or stale provenance, never a
    silent exclusion); both sides carry an empty (derived) fallback_flags
    tuple; and both sides' realized strata are equal. Everything else -- a
    scoring-invalid trial, a fallback flag, a stratum mismatch, or a count
    mismatch leaving one side's attempt with no counterpart -- is recorded as
    Unmatched rather than silently pooled (benchmark-spec §2: "a silent
    fallback turns a plugin effect into a model effect").

    Every treatment-side attempt must carry role == ArmRole.TREATMENT and
    every baseline-side attempt role == ArmRole.BASELINE, raised as a hard
    ContractError otherwise: benchmark-spec §4.1 "Nop, inversion and oracle
    are controls, not the baseline, and are excluded from C" -- controls and
    coordination rows belong to controls.py's reward accounting, never here.
    """
    treatment = list(treatment)
    baseline = list(baseline)
    for a in treatment:
        if a.role is not ArmRole.TREATMENT:
            raise ContractError(
                f"matched_pairs: treatment-side attempt {a.attempt_id!r} has role "
                f"{a.role!r}, expected ArmRole.TREATMENT -- controls and "
                "coordination rows never belong in the matched set C"
            )
    for a in baseline:
        if a.role is not ArmRole.BASELINE:
            raise ContractError(
                f"matched_pairs: baseline-side attempt {a.attempt_id!r} has role "
                f"{a.role!r}, expected ArmRole.BASELINE -- controls and "
                "coordination rows never belong in the matched set C"
            )

    t_by_card: dict[str, list[Attempt]] = {}
    for a in treatment:
        t_by_card.setdefault(a.card_id, []).append(a)
    b_by_card: dict[str, list[Attempt]] = {}
    for a in baseline:
        b_by_card.setdefault(a.card_id, []).append(a)

    def _check_fallback(a: Attempt, side: str) -> None:
        derived = derive_fallback_flags(a.requested, a.realized)
        if derived != a.fallback_flags:
            raise ContractError(
                f"matched_pairs: {side}-side attempt {a.attempt_id!r} recorded "
                f"fallback_flags={a.fallback_flags!r} but requested vs realized "
                f"strata derive {derived!r} -- forged or stale fallback provenance"
            )

    pairs: list[Pair] = []
    unmatched: list[Unmatched] = []
    for card_id in sorted(set(t_by_card) | set(b_by_card)):
        t_list = t_by_card.get(card_id, [])
        b_list = b_by_card.get(card_id, [])
        n = min(len(t_list), len(b_list))
        for i in range(n):
            t_attempt, b_attempt = t_list[i], b_list[i]

            # Scoring-validity first, same attribute-only-the-affected-side(s)
            # pattern as the fallback check below (benchmark-spec §1.1).
            t_invalid = t_attempt.terminal_state not in SCORING_VALID_STATES
            b_invalid = b_attempt.terminal_state not in SCORING_VALID_STATES
            if t_invalid or b_invalid:
                if t_invalid:
                    unmatched.append(
                        Unmatched(card_id, "treatment", f"scoring-invalid: {t_attempt.terminal_state.value}")
                    )
                if b_invalid:
                    unmatched.append(
                        Unmatched(card_id, "baseline", f"scoring-invalid: {b_attempt.terminal_state.value}")
                    )
                continue

            _check_fallback(t_attempt, "treatment")
            _check_fallback(b_attempt, "baseline")

            # Check fallback_flags and attribute the exclusion only to the
            # side(s) that actually carry a flag: a realized-stratum mismatch
            # explained entirely by one side's own recorded fallback is not a
            # second, separate defect on the other side.
            if t_attempt.fallback_flags or b_attempt.fallback_flags:
                if t_attempt.fallback_flags:
                    unmatched.append(
                        Unmatched(card_id, "treatment", f"fallback_flags={t_attempt.fallback_flags}")
                    )
                if b_attempt.fallback_flags:
                    unmatched.append(
                        Unmatched(card_id, "baseline", f"fallback_flags={b_attempt.fallback_flags}")
                    )
                continue
            if t_attempt.realized != b_attempt.realized:
                # Both sides claim no fallback yet still realized different
                # strata -- an unexplained inconsistency, so both are flagged.
                unmatched.append(Unmatched(card_id, "treatment", "realized stratum differs from baseline"))
                unmatched.append(Unmatched(card_id, "baseline", "realized stratum differs from treatment"))
                continue
            pairs.append(Pair(card_id=card_id, treatment=t_attempt, baseline=b_attempt, stratum=t_attempt.realized))
        for extra in t_list[n:]:
            unmatched.append(Unmatched(card_id, "treatment", "no corresponding baseline attempt"))
        for extra in b_list[n:]:
            unmatched.append(Unmatched(card_id, "baseline", "no corresponding treatment attempt"))
    return tuple(pairs), tuple(unmatched)


# ---------------------------------------------------------------------------
# §8 -- tokens: no cross-model raw averaging
# ---------------------------------------------------------------------------

def pool_tokens(
    attempts: Iterable[Attempt], field: str, *, by: str | None = None
) -> Mapping[str, Total]:
    attempts = list(attempts)
    if by is None:
        model_ids = {a.usage.model_id for a in attempts}
        if len(model_ids) > 1:
            raise CrossModelPoolingRefused(
                f"pool_tokens: {len(model_ids)} distinct model_ids present "
                f"({sorted(model_ids)!r}) without by=; raw token pooling across "
                "models is refused -- there is no override argument"
            )
        if not model_ids:
            return {}
        model_id = next(iter(model_ids))
        return {model_id: sum_usage(attempts, field, model_id=model_id)}

    if by == "model":
        groups: dict[str, list[Attempt]] = {}
        for a in attempts:
            groups.setdefault(a.usage.model_id, []).append(a)
        return {mid: sum_usage(group, field, model_id=mid) for mid, group in groups.items()}

    if by == "stratum":
        groups: dict[str, list[Attempt]] = {}
        for a in attempts:
            groups.setdefault(a.realized.key(), []).append(a)
        out: dict[str, Total] = {}
        for key, group in groups.items():
            model_ids = {a.usage.model_id for a in group}
            # A stratum key "already includes model" is only true if nothing
            # actually enforces usage.model_id == realized.model. Nothing does
            # (that invariant belongs on contract.Attempt, outside this lane's
            # ownership) -- so check it here rather than trust it: without
            # this, every attempt in the group can unanimously carry the WRONG
            # model_id and the len(model_ids) != 1 guard below never fires.
            stratum_model = group[0].realized.model
            if model_ids != {stratum_model}:
                raise CrossModelPoolingRefused(
                    f"pool_tokens: stratum {key!r} declares model {stratum_model!r} "
                    f"but contributing usage.model_id values are {sorted(model_ids)!r} "
                    "-- raw counts would be filed under a stratum they were not "
                    "measured on"
                )
            if len(model_ids) != 1:
                raise CrossModelPoolingRefused(
                    f"pool_tokens: stratum {key!r} contains {len(model_ids)} "
                    f"distinct model_ids {sorted(model_ids)!r}; a stratum key "
                    "already includes model, so this indicates a bug upstream"
                )
            out[key] = sum_usage(group, field, model_id=next(iter(model_ids)))
        return out

    raise ContractError(f"pool_tokens: by must be None, 'model' or 'stratum', got {by!r}")


# ---------------------------------------------------------------------------
# §6 -- clustered uncertainty
# ---------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True, slots=True)
class Interval:
    point: float | None
    lo: float | None
    hi: float | None
    method: str
    n_clusters: int
    cluster_variable: str
    deff: float | None
    deff_method: str | None
    icc_raw: float | None
    unavailable_reason: str | None

    def render(self) -> str:
        point_str = "n/a" if self.point is None else f"{self.point:+.4f}"
        if self.lo is None or self.hi is None:
            return f"{point_str} unavailable ({self.unavailable_reason})"
        return (
            f"{point_str} ({self.lo:+.4f}, {self.hi:+.4f}) "
            f"[{self.method}, n_clusters={self.n_clusters}, cluster={self.cluster_variable}]"
        )

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True, slots=True)
class NoninferiorityResult:
    established: bool | None
    margin: float
    lower_bound: float | None
    reason: str


def icc_raw(clusters: Sequence[Sequence[float]]) -> float | None:
    """Unfloored one-way-ANOVA ICC estimate (benchmark-spec §6.3). Uses the
    mean cluster size m_bar in place of a common m for unequal-size clusters
    (benchmark-spec §12 UNKNOWN #2: `deff_method='mean-cluster-size'` when
    sizes differ)."""
    k = len(clusters)
    sizes = [len(c) for c in clusters]
    if k < 2 or any(s == 0 for s in sizes):
        return None
    m_bar = sum(sizes) / k
    if m_bar <= 1:
        return None
    p = [sum(c) / len(c) for c in clusters]
    grand_p = sum(p) / k
    msb = m_bar * sum((pi - grand_p) ** 2 for pi in p) / (k - 1)
    msw = sum(m_bar * pi * (1 - pi) for pi in p) / (k * (m_bar - 1))
    denom = msb + (m_bar - 1) * msw
    if denom == 0:
        return 0.0
    return (msb - msw) / denom


def icc(clusters: Sequence[Sequence[float]]) -> float | None:
    """Floored at 0 -- see icc_raw for the unfloored estimate."""
    raw = icc_raw(clusters)
    if raw is None:
        return None
    return max(raw, 0.0)


def _mean_cluster_size(clusters: Sequence[Sequence[float]]) -> float:
    return sum(len(c) for c in clusters) / len(clusters)


def design_effect(clusters: Sequence[Sequence[float]]) -> float | None:
    """1 + (m_bar - 1) * max(icc_raw, 0), floored at 1.0 (benchmark-spec §6.3:
    an unfloored negative ICC would give DEFF < 1 -- a "clustered" interval
    narrower than the naive one, the exact direction this exists to prevent).

    Empty clusters carry no information and are dropped before computing
    m_bar (they are not the caller's problem to pre-filter). When the
    remaining clusters average one trial each (m_bar <= 1), DEFF is exactly
    1.0 by the formula itself regardless of icc_raw -- which is genuinely
    inestimable at m_bar <= 1 and returns None -- so that case is NOT the
    same as "no valid trials" and must not propagate a None here."""
    nonempty = [c for c in clusters if len(c) > 0]
    if not nonempty:
        return None
    m_bar = _mean_cluster_size(nonempty)
    if m_bar <= 1:
        return 1.0
    raw = icc_raw(nonempty)
    if raw is None:
        return None
    deff = 1 + (m_bar - 1) * max(raw, 0.0)
    return max(deff, 1.0)


def wilson_interval(k: float, n: float, z: float = 1.959963985) -> tuple[float, float]:
    """k and n are EFFECTIVE (possibly fractional) counts -- see
    wilson_with_cluster_inflation."""
    if n <= 0:
        raise ContractError("wilson_interval: n must be > 0")
    z2 = z * z
    centre = (k + z2 / 2) / (n + z2)
    half = (z / (n + z2)) * math.sqrt(max(k * (n - k) / n, 0.0) + z2 / 4)
    return (centre - half, centre + half)


def wilson_with_cluster_inflation(
    clusters: Sequence[Sequence[float]], *, z: float = 1.959963985, min_clusters: int = 8
) -> Interval:
    """benchmark-spec §7's own worked example (voice-neg-02, 5/5 FAULT) is a
    plugin whose every cluster is empty once the FAULT trials are excluded
    upstream -- that must reduce k, not report a wrong "no valid trials" for
    what may still be a perfectly good interval on the surviving clusters.
    Likewise a normal one-repeat-per-card run (k clusters of size 1) has
    DEFF == 1 exactly and a real Wilson interval to report, not a refusal."""
    nonempty = [c for c in clusters if len(c) > 0]
    k = len(nonempty)
    n = sum(len(c) for c in nonempty)
    raw = icc_raw(nonempty)
    deff = design_effect(nonempty)
    m_bar = (n / k) if k else 0.0
    if deff is None:
        deff_method = None
    elif m_bar <= 1:
        deff_method = "single-trial-clusters"
    else:
        deff_method = "floored-at-1"
    p_hat = (sum(sum(c) for c in nonempty) / n) if n else None

    if k < min_clusters:
        return Interval(
            point=p_hat, lo=None, hi=None, method="wilson-deff",
            n_clusters=k, cluster_variable="card",
            deff=deff, deff_method=deff_method,
            icc_raw=raw, unavailable_reason=f"insufficient clusters: {k} < {min_clusters}",
        )
    if n == 0 or deff is None or p_hat is None:
        return Interval(
            point=p_hat, lo=None, hi=None, method="wilson-deff",
            n_clusters=k, cluster_variable="card", deff=deff, deff_method=deff_method,
            icc_raw=raw, unavailable_reason="no valid trials",
        )
    n_eff = n / deff
    k_eff = p_hat * n_eff
    lo, hi = wilson_interval(k_eff, n_eff, z)
    return Interval(
        point=p_hat, lo=lo, hi=hi, method="wilson-deff",
        n_clusters=k, cluster_variable="card",
        deff=deff, deff_method=deff_method, icc_raw=raw, unavailable_reason=None,
    )


def _percentile(sorted_vals: Sequence[float], pct: float) -> float:
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    idx = pct / 100 * (len(sorted_vals) - 1)
    lo_idx = math.floor(idx)
    hi_idx = math.ceil(idx)
    if lo_idx == hi_idx:
        return sorted_vals[int(idx)]
    frac = idx - lo_idx
    return sorted_vals[lo_idx] * (1 - frac) + sorted_vals[hi_idx] * frac


def cluster_bootstrap(
    clusters: Sequence[Sequence[float]],
    statistic: Callable[[Sequence[Sequence[float]]], float],
    *, iters: int = 10_000, seed: int, alpha: float = 0.05, min_clusters: int = 8,
) -> Interval:
    k = len(clusters)
    point = statistic(clusters) if k else None
    if k < min_clusters:
        return Interval(
            point=point, lo=None, hi=None, method="cluster-bootstrap-percentile",
            n_clusters=k, cluster_variable="card", deff=None, deff_method=None,
            icc_raw=None, unavailable_reason=f"insufficient clusters: {k} < {min_clusters}",
        )
    rng = random.Random(seed)
    replicates: list[float] = []
    for _ in range(iters):
        sample = [clusters[rng.randrange(k)] for _ in range(k)]
        replicates.append(statistic(sample))
    replicates.sort()
    lo = _percentile(replicates, 100 * alpha / 2)
    hi = _percentile(replicates, 100 * (1 - alpha / 2))
    return Interval(
        point=point, lo=lo, hi=hi, method="cluster-bootstrap-percentile",
        n_clusters=k, cluster_variable="card", deff=None, deff_method=None,
        icc_raw=None, unavailable_reason=None,
    )


# -- Student-t inverse CDF, stdlib only (Lentz continued-fraction incomplete
#    beta, as in Numerical Recipes' betacf/betai) -- needed for cluster_t_interval.

def _betacf(a: float, b: float, x: float, max_iter: int = 200, eps: float = 1e-12) -> float:
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < 1e-30:
        d = 1e-30
    d = 1.0 / d
    h = d
    for m in range(1, max_iter + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def _betai(a: float, b: float, x: float) -> float:
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    bt = math.exp(
        math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
        + a * math.log(x) + b * math.log(1.0 - x)
    )
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def _student_t_cdf(t: float, df: int) -> float:
    x = df / (df + t * t)
    p = _betai(df / 2.0, 0.5, x)
    return (1.0 - 0.5 * p) if t >= 0 else (0.5 * p)


def _student_t_ppf(prob: float, df: int) -> float:
    lo, hi = 0.0, 1.0
    while _student_t_cdf(hi, df) < prob:
        hi *= 2
        if hi > 1e7:
            break
    for _ in range(200):
        mid = (lo + hi) / 2
        if _student_t_cdf(mid, df) < prob:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def cluster_t_interval(
    cluster_means: Sequence[float], *, alpha: float = 0.05, min_clusters: int = 8
) -> Interval:
    k = len(cluster_means)
    if k == 0:
        return Interval(
            point=None, lo=None, hi=None, method="cluster-t", n_clusters=0,
            cluster_variable="card", deff=None, deff_method=None, icc_raw=None,
            unavailable_reason="no clusters",
        )
    mean = sum(cluster_means) / k
    if k < min_clusters:
        return Interval(
            point=mean, lo=None, hi=None, method="cluster-t", n_clusters=k,
            cluster_variable="card", deff=None, deff_method=None, icc_raw=None,
            unavailable_reason=f"insufficient clusters: {k} < {min_clusters}",
        )
    if k < 2:
        return Interval(
            point=mean, lo=None, hi=None, method="cluster-t", n_clusters=k,
            cluster_variable="card", deff=None, deff_method=None, icc_raw=None,
            unavailable_reason="insufficient clusters: 1 < 2",
        )
    variance = sum((x - mean) ** 2 for x in cluster_means) / (k - 1)
    s = math.sqrt(variance)
    se = s / math.sqrt(k)
    tcrit = _student_t_ppf(1 - alpha / 2, k - 1)
    half = tcrit * se
    return Interval(
        point=mean, lo=mean - half, hi=mean + half, method="cluster-t", n_clusters=k,
        cluster_variable="card", deff=None, deff_method=None, icc_raw=None,
        unavailable_reason=None,
    )


def _eligible_for_effect(attempts: Sequence[Attempt], expected_role: ArmRole, side: str) -> list[Attempt]:
    """The population card_rate is computed over for one arm's side of
    Delta_full: correct role, fallback_flags verified against
    requested/realized (never merely trusted), non-fallback, scoring-valid.
    Shares the same eligibility rules matched_pairs enforces per attempt-pair,
    but is not itself pair-indexed -- see the difference_interval deviation
    note at the top of this module."""
    out: list[Attempt] = []
    for a in attempts:
        if a.role is not expected_role:
            raise ContractError(
                f"difference_interval: {side}-side attempt {a.attempt_id!r} has "
                f"role {a.role!r}, expected {expected_role!r}"
            )
        derived = derive_fallback_flags(a.requested, a.realized)
        if derived != a.fallback_flags:
            raise ContractError(
                f"difference_interval: {side}-side attempt {a.attempt_id!r} "
                f"recorded fallback_flags={a.fallback_flags!r} but requested vs "
                f"realized strata derive {derived!r} -- forged or stale fallback "
                "provenance"
            )
        if a.fallback_flags:
            continue
        if a.terminal_state not in SCORING_VALID_STATES:
            continue
        out.append(a)
    return out


def difference_interval(
    treatment: Iterable[Attempt],
    baseline: Iterable[Attempt],
    *,
    score: str = "outcome",
    seed: int,
    min_clusters: int = 8,
) -> Interval:
    """benchmark-spec §4.1: Delta_full = (1/|C|) * sum_c [p_T(c) - p_B(c)],
    each p_a(c) being that arm's OWN card_rate over its OWN eligible trials
    for card c -- never a per-trial paired difference. `seed` is accepted for
    signature stability but unused; see the module-level deviation note."""
    del seed
    treatment = list(treatment)
    baseline = list(baseline)

    # matched_pairs decides which cards belong to C: a card with no surviving
    # pair (every attempt on one side excluded by role/fallback/scoring
    # validity) is excluded from C entirely, never zero-filled.
    pairs, _ = matched_pairs(treatment, baseline)
    if not pairs:
        raise ContractError(
            "difference_interval: no matched cards in C (benchmark-spec §4.1) "
            "-- every card was excluded by role, fallback, or scoring-validity"
        )
    strata = {p.stratum for p in pairs}
    if len(strata) != 1:
        raise ContractError(
            f"difference_interval: matched cards span {len(strata)} distinct "
            "realized strata; call once per stratum via group_by_stratum "
            "instead (benchmark-spec §2: a silent fallback turns a plugin "
            "effect into a model effect)"
        )
    matched_cards = {p.card_id for p in pairs}

    t_eligible = _eligible_for_effect(treatment, ArmRole.TREATMENT, "treatment")
    b_eligible = _eligible_for_effect(baseline, ArmRole.BASELINE, "baseline")
    t_by_card: dict[str, list[Attempt]] = {}
    for a in t_eligible:
        if a.card_id in matched_cards:
            t_by_card.setdefault(a.card_id, []).append(a)
    b_by_card: dict[str, list[Attempt]] = {}
    for a in b_eligible:
        if a.card_id in matched_cards:
            b_by_card.setdefault(a.card_id, []).append(a)

    cluster_means: list[float] = []
    for card_id in sorted(matched_cards):
        p_t = card_rate(t_by_card.get(card_id, ()), score).value
        p_b = card_rate(b_by_card.get(card_id, ()), score).value
        if p_t is None or p_b is None:
            continue  # a zero-denominator arm on this card excludes it, never zero-fills it
        cluster_means.append(p_t - p_b)

    if not cluster_means:
        raise ContractError(
            "difference_interval: no card in C had a defined card_rate on both arms"
        )

    return cluster_t_interval(cluster_means, min_clusters=min_clusters)


def noninferiority(interval: Interval, margin: float | None) -> NoninferiorityResult:
    if margin is None:
        raise MarginMissing(
            "noninferiority: a margin must be declared in the run manifest "
            "before the run -- there is no code default"
        )
    if interval.lo is None:
        return NoninferiorityResult(
            established=None, margin=margin, lower_bound=None,
            reason=interval.unavailable_reason or "interval unavailable",
        )
    established = interval.lo > -margin
    return NoninferiorityResult(
        established=established, margin=margin, lower_bound=interval.lo,
        reason="established" if established else "not established",
    )
