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
from .accounting import AttemptLedger, Denominators, Total, USAGE_FIELDS, denominators
from .analysis import Interval, NoninferiorityResult, Rate, pool_tokens, rate_of
from .contract import (
    Attempt,
    ContractError,
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

    def evaluated(self) -> int:
        return (
            self.outcome_pass_adoption_pass
            + self.outcome_pass_adoption_fail
            + self.outcome_fail_adoption_pass
            + self.outcome_fail_adoption_fail
        )

    def outcome_rate(self) -> Rate:
        n = self.evaluated()
        num = self.outcome_pass_adoption_pass + self.outcome_pass_adoption_fail
        return rate_of(num, n)

    def adoption_rate(self) -> Rate:
        n = self.evaluated()
        num = self.outcome_pass_adoption_pass + self.outcome_fail_adoption_pass
        return rate_of(num, n)

    def ritual_without_outcome(self) -> Rate:
        # n01 / (n11 + n01) -- of the runs that performed the ritual, how many
        # did not accomplish the user's task. The central vacuity cell.
        denom = self.outcome_pass_adoption_pass + self.outcome_fail_adoption_pass
        return rate_of(self.outcome_fail_adoption_pass, denom)

    def outcome_without_ritual(self) -> Rate:
        # n10 / (n11 + n10) -- of the successful runs, how many skipped the
        # ritual. Where a correct direct baseline is supposed to show up.
        denom = self.outcome_pass_adoption_pass + self.outcome_pass_adoption_fail
        return rate_of(self.outcome_pass_adoption_fail, denom)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def outcome_adoption_matrix(
    attempts: Iterable[Attempt], *, card_plugin: Callable[[str], str] | None = None
) -> Mapping[str, Cell2x2]:
    from .contract import SCORING_VALID_STATES  # local: avoid widening module import surface

    plugin_of = card_plugin or _plugin_of_card
    buckets: dict[str, dict[str, int]] = {}
    for a in attempts:
        if a.terminal_state not in SCORING_VALID_STATES:
            continue
        plugin = plugin_of(a.card_id)
        b = buckets.setdefault(
            plugin,
            {"n11": 0, "n10": 0, "n01": 0, "n00": 0, "outcome_unevaluated": 0, "adoption_unevaluated": 0},
        )
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
    """
    ledger.conserve()
    attempts = ledger.attempts()
    denoms = denominators(attempts)
    denoms.assert_reconciles()

    per_plugin = outcome_adoption_matrix(attempts)
    evidence = evidence_summary(attempts)

    per_stratum_tokens: dict[str, dict[str, Total]] = {}
    for field in USAGE_FIELDS:
        try:
            per_field = pool_tokens(attempts, field, by="stratum")
        except ContractError:
            per_field = {}
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
        warnings=(),
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


def render_text(report: Report) -> str:
    m = report.manifest
    lines: list[str] = []
    lines.append(f"agentic report — run {m.run_id}")
    lines.append(
        f"git={m.git_commit} branch={m.branch} catalog_digest={m.catalog_digest} "
        f"offline={m.offline}"
    )
    lines.append(
        f"min_valid={m.min_valid} min_clusters={m.min_clusters} "
        f"noninferiority_margin={m.noninferiority_margin} holdout_seed={m.holdout_seed}"
    )
    lines.append(report.denominators.render())
    lines.append("")

    lines.append("evidence:")
    for ec in EvidenceClass:
        lines.append(f"  {ec.value}: {report.evidence[ec]}")
    lines.append("")

    lines.append("per-plugin outcome / adoption (2x2, scoring-valid attempts only):")
    for plugin in sorted(report.per_plugin):
        cell = report.per_plugin[plugin]
        lines.append(
            f"  {plugin}: outcome={cell.outcome_rate().render()} "
            f"adoption={cell.adoption_rate().render()} "
            f"ritual_without_outcome={cell.ritual_without_outcome().render()} "
            f"outcome_without_ritual={cell.outcome_without_ritual().render()} "
            f"(unevaluated: outcome={cell.outcome_unevaluated} adoption={cell.adoption_unevaluated})"
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


def render_json(report: Report) -> dict[str, Any]:
    return {
        "manifest": report.manifest.to_dict(),
        "denominators": report.denominators.to_dict(),
        "denominators_rendered": report.denominators.render(),
        "per_plugin": {k: v.to_dict() for k, v in report.per_plugin.items()},
        "per_stratum_tokens": {
            sk: {f: t.to_dict() for f, t in fields.items()}
            for sk, fields in report.per_stratum_tokens.items()
        },
        "effects": {k: v.to_dict() for k, v in report.effects.items()},
        "effects_rendered": {k: v.render() for k, v in report.effects.items()},
        "noninferiority": {k: dataclasses.asdict(v) for k, v in report.noninferiority.items()},
        "evidence": {k.value: v for k, v in report.evidence.items()},
        "agreement": report.agreement.to_dict() if report.agreement is not None else None,
        "blocked": [dict(b) for b in report.blocked],
        "warnings": list(report.warnings),
    }


def render_markdown(report: Report) -> str:
    m = report.manifest
    lines: list[str] = []
    lines.append(f"# agentic report — run `{m.run_id}`")
    lines.append("")
    lines.append(
        f"- git `{m.git_commit}` branch `{m.branch}` catalog_digest `{m.catalog_digest}` "
        f"offline={m.offline}"
    )
    lines.append(f"- {report.denominators.render()}")
    lines.append("")
    lines.append("## Evidence")
    lines.append("")
    lines.append("| class | count |")
    lines.append("|---|---:|")
    for ec in EvidenceClass:
        lines.append(f"| {ec.value} | {report.evidence[ec]} |")
    lines.append("")
    lines.append("## Outcome vs adoption (per plugin)")
    lines.append("")
    lines.append("| plugin | outcome | adoption | ritual_without_outcome | outcome_without_ritual |")
    lines.append("|---|---|---|---|---|")
    for plugin in sorted(report.per_plugin):
        cell = report.per_plugin[plugin]
        lines.append(
            f"| {plugin} | {cell.outcome_rate().render()} | {cell.adoption_rate().render()} | "
            f"{cell.ritual_without_outcome().render()} | {cell.outcome_without_ritual().render()} |"
        )
    if report.effects:
        lines.append("")
        lines.append("## Effects")
        lines.append("")
        lines.append("| estimand | interval |")
        lines.append("|---|---|")
        for name in sorted(report.effects):
            lines.append(f"| {name} | {report.effects[name].render()} |")
    if report.blocked:
        lines.append("")
        lines.append("## Blocked")
        lines.append("")
        for b in report.blocked:
            lines.append(f"- {b['id']} BLOCKED — approval required ({b['gate']})")
    return "\n".join(lines)
