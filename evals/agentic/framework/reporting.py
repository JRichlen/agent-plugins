"""evals.agentic.framework.reporting -- the 2x2 outcome/adoption matrix, grader
agreement (reused from evals/paid/calibration/agreement.py, never
reimplemented), and the native-evidence refusal gate (measurement lane,
contract §3.7, §5.4).

Deviation reported explicitly (per the task brief's instruction, not silent):
`outcome_adoption_matrix` groups attempts by plugin, but `contract.Attempt`
carries only `card_id`, not `plugin` -- `Card.plugin` lives on a registry-owned
dataclass this lane does not construct. This module derives the plugin name
from the corpus's own card-id convention used throughout the benchmark spec's
worked examples ("redgate-pos-01", "voice-neg-02", i.e.
`<plugin>-{pos,neg,near}-<NN>`) via `_plugin_of_card`. When registry's real
`Card` objects are available, a caller can pass a `card_plugin` lookup instead
of relying on this convention; `outcome_adoption_matrix` accepts one as an
optional keyword for that reason.
"""
from __future__ import annotations

import dataclasses
import re
import subprocess
import sys
from collections.abc import Callable, Iterable, Mapping
from typing import Any

from . import io
from .accounting import AttemptLedger, Denominators, Total, USAGE_FIELDS, assert_planned_reconciles, denominators
from .analysis import Interval, NoninferiorityResult, Rate, pool_tokens, rate_of
from .contract import (
    Attempt,
    ContractError,
    CrossModelPoolingRefused,
    EvidenceClass,
    LedgerView,
    Manifest,
    NativeProofRequired,
)

__all__ = [
    "Cell2x2",
    "AgreementResult",
    "Report",
    "outcome_adoption_matrix",
    "evidence_summary",
    "grader_agreement",
    "sample_hash",
    "build_report",
    "assert_native_claims",
    "render_text",
    "render_json",
    "render_markdown",
]

_CARD_ID_RE = re.compile(r"^(?P<plugin>.+)-(?:pos|neg|near)-\d+$")


def _plugin_of_card(card_id: str) -> str:
    m = _CARD_ID_RE.match(card_id)
    return m.group("plugin") if m else card_id


@dataclasses.dataclass(frozen=True, slots=True)
class Cell2x2:
    outcome_pass_adoption_pass: int
    outcome_pass_adoption_fail: int
    outcome_fail_adoption_pass: int
    outcome_fail_adoption_fail: int
    outcome_unevaluated: int
    adoption_unevaluated: int
    # REPAIR S-06: a plugin whose attempts are ALL scoring-invalid (FAULT/
    # CANCELLED) used to get no bucket at all -- silently absent from the
    # report rather than rendered "unavailable" with a reason (benchmark-spec
    # §7's own worked example, voice-neg-02, 5/5 FAULT). Defaulted so every
    # existing positional/keyword construction in this module and in tests
    # keeps working unchanged.
    scoring_valid_total: int = 0
    scoring_invalid_fault: int = 0
    scoring_invalid_cancel: int = 0

    def evaluated(self) -> int:
        return (
            self.outcome_pass_adoption_pass
            + self.outcome_pass_adoption_fail
            + self.outcome_fail_adoption_pass
            + self.outcome_fail_adoption_fail
        )

    def _reason(self) -> str:
        """Only meaningful when evaluated() == 0 -- see rate_of's
        denominator<=0 branch. Distinguishes 'no scoring-valid samples at
        all' (FAULT/CANCELLED) from 'samples existed but the verifier never
        ran on any of them' (S-06): the two are different failures and read
        very differently in a report."""
        total = self.scoring_valid_total + self.scoring_invalid_fault + self.scoring_invalid_cancel
        if self.scoring_valid_total == 0:
            if total == 0:
                return "no trials"
            if self.scoring_invalid_fault == total:
                return f"no valid samples: {self.scoring_invalid_fault}/{total} FAULT"
            if self.scoring_invalid_cancel == total:
                return f"no valid samples: {self.scoring_invalid_cancel}/{total} CANCELLED"
            return f"no valid samples: {total}/{total} invalid"
        return (
            f"no evaluated verdicts: {self.scoring_valid_total} scoring-valid "
            "sample(s), the verifier never ran"
        )

    def outcome_rate(self, *, min_valid: int = 1) -> Rate:
        n = self.evaluated()
        num = self.outcome_pass_adoption_pass + self.outcome_pass_adoption_fail
        return rate_of(num, n, min_valid=min_valid, unavailable_reason=self._reason() if n == 0 else None)

    def adoption_rate(self, *, min_valid: int = 1) -> Rate:
        n = self.evaluated()
        num = self.outcome_pass_adoption_pass + self.outcome_fail_adoption_pass
        return rate_of(num, n, min_valid=min_valid, unavailable_reason=self._reason() if n == 0 else None)

    def ritual_without_outcome(self) -> Rate:
        # n01 / (n11 + n01) -- of the runs that performed the ritual, how many
        # did not accomplish the user's task. The central vacuity cell.
        denom = self.outcome_pass_adoption_pass + self.outcome_fail_adoption_pass
        return rate_of(
            self.outcome_fail_adoption_pass, denom,
            unavailable_reason=self._reason() if denom == 0 and self.evaluated() == 0 else None,
        )

    def outcome_without_ritual(self) -> Rate:
        # n10 / (n11 + n10) -- of the successful runs, how many skipped the
        # ritual. Where a correct direct baseline is supposed to show up.
        denom = self.outcome_pass_adoption_pass + self.outcome_pass_adoption_fail
        return rate_of(
            self.outcome_pass_adoption_fail, denom,
            unavailable_reason=self._reason() if denom == 0 and self.evaluated() == 0 else None,
        )

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def outcome_adoption_matrix(
    attempts: Iterable[Attempt], *, card_plugin: Callable[[str], str] | None = None
) -> Mapping[str, Cell2x2]:
    from .contract import SCORING_VALID_STATES, TerminalState  # local: avoid widening module import surface

    plugin_of = card_plugin or _plugin_of_card
    buckets: dict[str, dict[str, int]] = {}

    def bucket(plugin: str) -> dict[str, int]:
        return buckets.setdefault(
            plugin,
            {
                "n11": 0, "n10": 0, "n01": 0, "n00": 0,
                "outcome_unevaluated": 0, "adoption_unevaluated": 0,
                "scoring_valid_total": 0, "scoring_invalid_fault": 0, "scoring_invalid_cancel": 0,
            },
        )

    for a in attempts:
        # Create the bucket for every plugin SEEN, before the scoring-valid
        # filter (S-06) -- a plugin whose every attempt faulted or was
        # cancelled must still appear in the report, rendered "unavailable"
        # with a reason, not be silently absent.
        b = bucket(plugin_of(a.card_id))
        if a.terminal_state not in SCORING_VALID_STATES:
            if a.terminal_state is TerminalState.FAULT:
                b["scoring_invalid_fault"] += 1
            elif a.terminal_state is TerminalState.CANCELLED:
                b["scoring_invalid_cancel"] += 1
            continue
        b["scoring_valid_total"] += 1
        o = a.outcome.passed
        r = a.adoption.passed
        if o is None:
            b["outcome_unevaluated"] += 1
        if r is None:
            b["adoption_unevaluated"] += 1
        if o is None or r is None:
            continue
        if o and r:
            b["n11"] += 1
        elif o and not r:
            b["n10"] += 1
        elif not o and r:
            b["n01"] += 1
        else:
            b["n00"] += 1
    return {
        plugin: Cell2x2(
            outcome_pass_adoption_pass=b["n11"],
            outcome_pass_adoption_fail=b["n10"],
            outcome_fail_adoption_pass=b["n01"],
            outcome_fail_adoption_fail=b["n00"],
            outcome_unevaluated=b["outcome_unevaluated"],
            adoption_unevaluated=b["adoption_unevaluated"],
            scoring_valid_total=b["scoring_valid_total"],
            scoring_invalid_fault=b["scoring_invalid_fault"],
            scoring_invalid_cancel=b["scoring_invalid_cancel"],
        )
        for plugin, b in buckets.items()
    }


def evidence_summary(attempts: Iterable[Attempt]) -> Mapping[EvidenceClass, int]:
    out: dict[EvidenceClass, int] = {e: 0 for e in EvidenceClass}
    for a in attempts:
        out[a.evidence_class] += 1
    return out


@dataclasses.dataclass(frozen=True, slots=True)
class AgreementResult:
    n: int
    agree: int
    percent: float
    kappa: float | None
    confusion: Mapping[str, Mapping[str, int]]
    disagreements: tuple[Mapping[str, str], ...]
    unlabelled: Mapping[str, int]
    unavailable_reason: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "n": self.n,
            "agree": self.agree,
            "percent": self.percent,
            "kappa": self.kappa,
            "confusion": self.confusion,
            "disagreements": list(self.disagreements),
            "unlabelled": dict(self.unlabelled),
            "unavailable_reason": self.unavailable_reason,
        }


def sample_hash(card_id: str, arm_id: str, attempt_id: str, output_digest: str) -> str:
    from .contract import digest

    return digest({"card": card_id, "arm": arm_id, "attempt": attempt_id, "output_digest": output_digest})


def grader_agreement(
    a_path: str, b_path: str, *, name_a: str, name_b: str, out_json: str
) -> AgreementResult:
    """Shells out to evals/paid/calibration/agreement.py. No kappa/confusion
    logic is reimplemented here -- see benchmark-spec §10 and T41."""
    repo = io.repo_root()
    script = repo / "evals" / "paid" / "calibration" / "agreement.py"
    proc = subprocess.run(
        [
            sys.executable, str(script), a_path, b_path,
            "--name-a", name_a, "--name-b", name_b, "--json", out_json,
        ],
        cwd=str(repo), capture_output=True, text=True,
    )
    if proc.returncode == 0:
        doc = io.load_json(out_json)
        return AgreementResult(
            n=doc["n"], agree=doc["agree"], percent=doc["percent"], kappa=doc["kappa"],
            confusion=doc["confusion"], disagreements=tuple(doc["disagreements"]),
            unlabelled=doc["unlabelled"], unavailable_reason=None,
        )

    stderr = proc.stderr or ""
    lines = stderr.splitlines()
    first_line = lines[0] if lines else ""
    if proc.returncode == 2:
        if first_line.startswith("agreement: only"):
            reason = "fewer than two hashes in common"
        elif "labels outside pass/fail" in stderr:
            m = re.search(r"labels outside pass/fail: (\[.*\])", stderr)
            reason = f"grader emitted labels outside pass/fail: {m.group(1) if m else stderr.strip()}"
        else:
            reason = f"agreement.py exit 2: {first_line}"
    else:
        reason = f"agreement.py exit {proc.returncode}: {first_line}"
    return AgreementResult(
        n=0, agree=0, percent=0.0, kappa=None, confusion={}, disagreements=(),
        unlabelled={}, unavailable_reason=reason,
    )


@dataclasses.dataclass(frozen=True, slots=True)
class Report:
    manifest: Manifest
    denominators: Denominators
    per_plugin: Mapping[str, Cell2x2]
    per_stratum_tokens: Mapping[str, Mapping[str, Total]]
    effects: Mapping[str, Interval]
    noninferiority: Mapping[str, NoninferiorityResult]
    evidence: Mapping[EvidenceClass, int]
    agreement: AgreementResult | None
    blocked: tuple[Mapping[str, str], ...]
    warnings: tuple[str, ...]


def build_report(
    manifest: Manifest,
    ledger: AttemptLedger,
    event_ledger: LedgerView | None,
) -> Report:
    """Builds the conservation-checked, denominator-reconciled report shell.

    `effects` and `noninferiority` are left empty here: computing them
    requires per-card matched-pair construction (arms, cards), which is
    registry-lane territory this module does not own the inputs for. A caller
    holding `analysis.matched_pairs`/`analysis.difference_interval` results
    populates those two maps via `dataclasses.replace(report, effects=..., ...)`
    before rendering. This is a lane-boundary decision, not an omission --
    reported explicitly per the task brief's instruction.

    REPAIR S-10: `event_ledger` is threaded through unchanged to the render
    layer (`render_text`/`render_json`/`render_markdown` now take it too, so
    `assert_native_claims` is actually consulted before a native-proven count
    is printed as trustworthy -- see N-01). `Manifest.planned_n`, when
    declared, is checked against the ledger's own accounting denominator via
    `assert_planned_reconciles` -- a real external check, unlike
    `conserve()`/`assert_reconciles()`, which are tautological against
    whatever ledger they are handed. `planned_n` is `{}` in every run today
    (a cross-lane gap in `run.py`, outside this lane's ownership), so this is
    a no-op until a caller populates it.
    """
    ledger.conserve()
    attempts = ledger.attempts()
    denoms = denominators(attempts)
    denoms.assert_reconciles()
    assert_planned_reconciles(denoms, manifest.planned_n, manifest.skipped)

    per_plugin = outcome_adoption_matrix(attempts)
    evidence = evidence_summary(attempts)

    warnings: list[str] = []
    seen_warnings: set[str] = set()
    per_stratum_tokens: dict[str, dict[str, Total]] = {}
    for field in USAGE_FIELDS:
        try:
            per_field = pool_tokens(attempts, field, by="stratum")
        except CrossModelPoolingRefused as exc:
            # REPAIR S-09: this used to be swallowed as `per_field = {}` with
            # no trace -- a genuine cross-model token contamination rendered
            # as an empty, unremarkable "token totals per stratum:" section.
            # Surface it instead of erasing it. The same contamination is
            # normally detected on every USAGE_FIELDS pass; dedupe rather
            # than repeat the identical sentence once per field.
            msg = str(exc)
            if msg not in seen_warnings:
                seen_warnings.add(msg)
                warnings.append(msg)
            continue
        for stratum_key, total in per_field.items():
            per_stratum_tokens.setdefault(stratum_key, {})[field] = total

    return Report(
        manifest=manifest,
        denominators=denoms,
        per_plugin=per_plugin,
        per_stratum_tokens=per_stratum_tokens,
        effects={},
        noninferiority={},
        evidence=evidence,
        agreement=None,
        blocked=(),
        warnings=tuple(warnings),
    )


def assert_native_claims(report: Report, event_ledger: LedgerView | None) -> None:
    """Raises NativeProofRequired unless evidence[NATIVE_PROVEN] > 0 AND the
    ledger chain verifies. Callers (render_*) must gate any "native"/"proven in
    a real harness" sentence behind a call to this first."""
    native_count = report.evidence[EvidenceClass.NATIVE_PROVEN]
    if native_count == 0:
        raise NativeProofRequired(
            "assert_native_claims: evidence[NATIVE_PROVEN] == 0 -- no attempt "
            "in this report is backed by a verified host-observed ledger"
        )
    if event_ledger is None or not event_ledger.is_verified():
        raise NativeProofRequired(
            "assert_native_claims: the event ledger is absent or its hash "
            "chain is not verified"
        )
    # REPAIR FOLLOWUP-2 (adapter lane, belt and braces). The clause above is
    # load-bearing on its own today: adapters.LedgerReader.verification_reason
    # refuses a ledger with zero host-observed entries, so is_verified() is
    # already False for one. But `event_ledger` is typed as the LedgerView
    # PROTOCOL, and any object with the five (now six) methods satisfies it --
    # including a duck-typed reader whose is_verified() returns True for a
    # ledger the host witnessed nothing in. That is the exact shape review
    # finding N-02 walked in through. Ask the ledger directly how many
    # host-observed entries it holds and refuse zero, so the native sentence
    # never rests on one implementation's internal policy.
    #
    # Probed with getattr rather than called outright: contract.LedgerView
    # (core-owned, frozen) declares five methods plus an OPTIONAL sixth
    # (`records()`), and this lane cannot add `verify_chain` to that Protocol.
    # Probing is the same pattern contract.assert_native_backed already uses
    # for records(), and it keeps every existing LedgerView test double --
    # which predate this check -- working unchanged.
    verify_chain = getattr(event_ledger, "verify_chain", None)
    if callable(verify_chain):
        chain = verify_chain()
        host_observed = getattr(chain, "host_observed", None)
        if isinstance(host_observed, int) and host_observed <= 0:
            raise NativeProofRequired(
                "assert_native_claims: the event ledger's chain reports "
                f"host_observed={host_observed} -- the host witnessed nothing in "
                "it, so there is no native behaviour here to report"
            )


def _native_proven_status(report: Report, event_ledger: LedgerView | None) -> tuple[bool, str | None]:
    """REPAIR N-01: render_text/render_json/render_markdown used to print
    `evidence[NATIVE_PROVEN]` as a bare, trustworthy-looking count with no
    call to `assert_native_claims` anywhere -- the lane's own negative-control
    fixture (a forged evidence_class="native-proven" attempt with a session_id
    no SESSION_ACK ever carried) rendered "native-proven | 1" in every format.
    Every renderer now calls this first and annotates the count instead of
    printing it bare. Returns (verified, reason); reason is None iff verified
    or the count is 0 (nothing to verify)."""
    if report.evidence[EvidenceClass.NATIVE_PROVEN] == 0:
        return True, None
    try:
        assert_native_claims(report, event_ledger)
    except NativeProofRequired as exc:
        return False, str(exc)
    return True, None


def _header_lines(m: Manifest, denominators_rendered: str) -> list[str]:
    """REPAIR S-04: the header (toolchain, delta, min_valid, min_clusters,
    seed) that benchmark-spec §11.1 requires "first, always" -- shared by
    render_text and render_markdown so the two cannot drift (render_markdown
    used to omit every line here but the git/branch/catalog/offline one)."""
    return [
        f"git={m.git_commit} branch={m.branch} catalog_digest={m.catalog_digest} offline={m.offline}",
        f"toolchain={dict(m.toolchain)}",
        f"min_valid={m.min_valid} min_clusters={m.min_clusters} "
        f"noninferiority_margin={m.noninferiority_margin} holdout_seed={m.holdout_seed}",
        denominators_rendered,
    ]


def _evidence_rows(report: Report, event_ledger: LedgerView | None) -> list[tuple[str, str]]:
    """REPAIR N-01: (label, value) pairs for the evidence table, shared by all
    three renderers. NATIVE_PROVEN is never printed as a bare count -- it is
    gated behind `_native_proven_status` (which calls `assert_native_claims`)
    first."""
    verified, reason = _native_proven_status(report, event_ledger)
    rows: list[tuple[str, str]] = []
    for ec in EvidenceClass:
        count = report.evidence[ec]
        if ec is EvidenceClass.NATIVE_PROVEN and count > 0 and not verified:
            rows.append((ec.value, f"{count} (UNVERIFIABLE IN THIS RENDER: {reason})"))
        else:
            rows.append((ec.value, str(count)))
    return rows


def _cell_row_strings(cell: Cell2x2, *, min_valid: int) -> dict[str, str]:
    """REPAIR S-04/S-05: one 2x2-row formatter shared by render_text and
    render_markdown, so a count or reason string present in one can never be
    silently absent from the other. `min_valid` is threaded from
    `Manifest.min_valid` (benchmark-spec §7's starved-card floor) rather than
    the permissive code default."""
    return {
        "outcome": cell.outcome_rate(min_valid=min_valid).render(),
        "adoption": cell.adoption_rate(min_valid=min_valid).render(),
        "ritual_without_outcome": cell.ritual_without_outcome().render(),
        "outcome_without_ritual": cell.outcome_without_ritual().render(),
        "unevaluated": f"outcome={cell.outcome_unevaluated} adoption={cell.adoption_unevaluated}",
    }


def render_text(report: Report, event_ledger: LedgerView | None = None) -> str:
    m = report.manifest
    lines: list[str] = []
    lines.append(f"agentic report — run {m.run_id}")
    lines.extend(_header_lines(m, report.denominators.render()))
    lines.append("")

    lines.append("evidence:")
    for label, value in _evidence_rows(report, event_ledger):
        lines.append(f"  {label}: {value}")
    lines.append("")

    lines.append("per-plugin outcome / adoption (2x2, scoring-valid attempts only):")
    for plugin in sorted(report.per_plugin):
        cell = report.per_plugin[plugin]
        row = _cell_row_strings(cell, min_valid=m.min_valid)
        lines.append(
            f"  {plugin}: outcome={row['outcome']} "
            f"adoption={row['adoption']} "
            f"ritual_without_outcome={row['ritual_without_outcome']} "
            f"outcome_without_ritual={row['outcome_without_ritual']} "
            f"(unevaluated: {row['unevaluated']})"
        )
    lines.append("")

    lines.append("token totals per stratum:")
    for stratum_key in sorted(report.per_stratum_tokens):
        fields = report.per_stratum_tokens[stratum_key]
        for field in sorted(fields):
            lines.append(f"  {stratum_key} {field}: {fields[field].render()}")
    lines.append("")

    lines.append("effects:")
    for name in sorted(report.effects):
        lines.append(f"  {name}: {report.effects[name].render()}")
    lines.append("noninferiority:")
    for name in sorted(report.noninferiority):
        res = report.noninferiority[name]
        lines.append(
            f"  {name}: established={res.established} margin={res.margin} "
            f"lower_bound={res.lower_bound} ({res.reason})"
        )

    if report.agreement is not None:
        a = report.agreement
        if a.unavailable_reason is not None:
            lines.append(f"grader agreement: unavailable ({a.unavailable_reason})")
        else:
            kappa_str = (
                "undefined (both graders used one label)" if a.kappa is None else f"{a.kappa:.3f}"
            )
            lines.append(
                f"grader agreement: n={a.n} agree={a.agree} percent={a.percent:.1f}% kappa={kappa_str}"
            )
            if a.unlabelled and any(a.unlabelled.values()):
                lines.append(f"  unlabelled: {dict(a.unlabelled)}")

    if report.blocked:
        lines.append("")
        lines.append("blocked:")
        for b in report.blocked:
            lines.append(f"  {b['id']} BLOCKED — approval required ({b['gate']})")

    for w in report.warnings:
        lines.append(f"WARNING: {w}")

    return "\n".join(lines)


def render_json(report: Report, event_ledger: LedgerView | None = None) -> dict[str, Any]:
    m = report.manifest
    verified, native_reason = _native_proven_status(report, event_ledger)
    return {
        "manifest": report.manifest.to_dict(),
        "denominators": report.denominators.to_dict(),
        "denominators_rendered": report.denominators.render(),
        "per_plugin": {
            k: {
                **v.to_dict(),
                "outcome_rate": v.outcome_rate(min_valid=m.min_valid).render(),
                "adoption_rate": v.adoption_rate(min_valid=m.min_valid).render(),
                "ritual_without_outcome": v.ritual_without_outcome().render(),
                "outcome_without_ritual": v.outcome_without_ritual().render(),
            }
            for k, v in report.per_plugin.items()
        },
        "per_stratum_tokens": {
            sk: {f: t.to_dict() for f, t in fields.items()}
            for sk, fields in report.per_stratum_tokens.items()
        },
        "effects": {k: v.to_dict() for k, v in report.effects.items()},
        "effects_rendered": {k: v.render() for k, v in report.effects.items()},
        "noninferiority": {k: dataclasses.asdict(v) for k, v in report.noninferiority.items()},
        "evidence": {k.value: v for k, v in report.evidence.items()},
        "evidence_native_proven_verified": verified,
        "evidence_native_proven_unverifiable_reason": native_reason,
        "agreement": report.agreement.to_dict() if report.agreement is not None else None,
        "blocked": [dict(b) for b in report.blocked],
        "warnings": list(report.warnings),
    }


def render_markdown(report: Report, event_ledger: LedgerView | None = None) -> str:
    """REPAIR S-04: parity with render_text/render_json -- the header (git,
    toolchain, min_valid/min_clusters/margin/seed), the unevaluated counts on
    each 2x2 row, the token-totals-per-stratum section, the noninferiority
    section, the grader-agreement section, and every warning used to be
    present in text/json and silently absent here."""
    m = report.manifest
    lines: list[str] = []
    lines.append(f"# agentic report — run `{m.run_id}`")
    lines.append("")
    for line in _header_lines(m, report.denominators.render()):
        lines.append(f"- {line}")
    lines.append("")
    lines.append("## Evidence")
    lines.append("")
    lines.append("| class | count |")
    lines.append("|---|---:|")
    for label, value in _evidence_rows(report, event_ledger):
        lines.append(f"| {label} | {value} |")
    lines.append("")
    lines.append("## Outcome vs adoption (per plugin, scoring-valid attempts only)")
    lines.append("")
    lines.append("| plugin | outcome | adoption | ritual_without_outcome | outcome_without_ritual | unevaluated |")
    lines.append("|---|---|---|---|---|---|")
    for plugin in sorted(report.per_plugin):
        cell = report.per_plugin[plugin]
        row = _cell_row_strings(cell, min_valid=m.min_valid)
        lines.append(
            f"| {plugin} | {row['outcome']} | {row['adoption']} | "
            f"{row['ritual_without_outcome']} | {row['outcome_without_ritual']} | {row['unevaluated']} |"
        )
    lines.append("")
    lines.append("## Token totals per stratum")
    lines.append("")
    if report.per_stratum_tokens:
        lines.append("| stratum | field | total |")
        lines.append("|---|---|---:|")
        for stratum_key in sorted(report.per_stratum_tokens):
            fields = report.per_stratum_tokens[stratum_key]
            for field in sorted(fields):
                lines.append(f"| {stratum_key} | {field} | {fields[field].render()} |")
    else:
        lines.append("_none_")
    if report.effects:
        lines.append("")
        lines.append("## Effects")
        lines.append("")
        lines.append("| estimand | interval |")
        lines.append("|---|---|")
        for name in sorted(report.effects):
            lines.append(f"| {name} | {report.effects[name].render()} |")
    if report.noninferiority:
        lines.append("")
        lines.append("## Noninferiority")
        lines.append("")
        lines.append("| estimand | established | margin | lower_bound | reason |")
        lines.append("|---|---|---:|---:|---|")
        for name in sorted(report.noninferiority):
            res = report.noninferiority[name]
            lines.append(f"| {name} | {res.established} | {res.margin} | {res.lower_bound} | {res.reason} |")
    if report.agreement is not None:
        lines.append("")
        lines.append("## Grader agreement")
        lines.append("")
        a = report.agreement
        if a.unavailable_reason is not None:
            lines.append(f"unavailable ({a.unavailable_reason})")
        else:
            kappa_str = (
                "undefined (both graders used one label)" if a.kappa is None else f"{a.kappa:.3f}"
            )
            lines.append(f"n={a.n} agree={a.agree} percent={a.percent:.1f}% kappa={kappa_str}")
            if a.unlabelled and any(a.unlabelled.values()):
                lines.append(f"unlabelled: {dict(a.unlabelled)}")
    if report.blocked:
        lines.append("")
        lines.append("## Blocked")
        lines.append("")
        for b in report.blocked:
            lines.append(f"- {b['id']} BLOCKED — approval required ({b['gate']})")
    if report.warnings:
        lines.append("")
        lines.append("## Warnings")
        lines.append("")
        for w in report.warnings:
            lines.append(f"- WARNING: {w}")
    return "\n".join(lines)
