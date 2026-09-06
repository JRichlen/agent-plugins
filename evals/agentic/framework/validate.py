"""evals.agentic.framework.validate -- card/corpus validation (registry lane,
contract §3.10): schema + on-disk resolution, two-sided-verifier vacuity,
holdout/leakage, coverage/strata reporting. Also exposes a CLI:

    python3 -m evals.agentic.framework.validate --corpus [--json]

for card authors to run locally (see evals/agentic/tasks/README.md).
"""
from __future__ import annotations

import argparse
import dataclasses
import importlib
import inspect
import json
import pathlib
import re
import sys
from collections.abc import Iterator, Mapping, Sequence
from typing import Any

from . import io
from .contract import (
    Card,
    CardKind,
    ContractError,
    CoverageGap,
    LeakageDetected,
    Manifest,
    VacuousVerifier,
    now_rfc3339,
)
from .controls import MUTATIONS
from .registry import PluginRef, derive_roster

__all__ = [
    "validate_card",
    "validate_arm_manifest",
    "validate_run_manifest",
    "load_cards",
    "Coverage",
    "coverage_report",
    "assert_triplet_completeness",
    "Overlap",
    "scan_leakage",
    "assert_no_leakage",
    "holdout_ids",
    "assert_holdout_unread",
]

# benchmark-spec §6.0: the per-plugin measurement floor, distinct from the
# coverage floor (>=1 card per kind). A plugin below this many total cards
# can never report an interval -- every per-plugin estimand there correctly
# reads "unavailable (insufficient clusters: n < 8)".
_MIN_CLUSTERS_FLOOR = 8

_TASKS_DIRNAME = "tasks"
_CARD_FILENAME = "card.json"


# ---------------------------------------------------------------------------
# Verifier-spec resolution shared by validate_card's vacuity check and
# scan_leakage's hidden-text extraction. Registry's real corpus cards use the
# "path/to/script.<ext>" form (an executable that takes a workspace path and
# prints a JSON verdict, per tasks/README.md) -- controls.py's own
# `_resolve_verifier` only understands "module:function" (its own two toy
# scenarios), so this module owns "path/to/script" resolution independently.
# ---------------------------------------------------------------------------

def _is_module_function_spec(spec: str) -> bool:
    return ":" in spec


def _verifier_source_bytes(spec: str, repo_root: pathlib.Path) -> bytes:
    if _is_module_function_spec(spec):
        module_name, _, func_name = spec.partition(":")
        try:
            module = importlib.import_module(module_name)
        except Exception as exc:  # noqa: BLE001
            raise ContractError(f"cannot import verifier module {module_name!r}: {exc}") from exc
        fn = getattr(module, func_name, None)
        if fn is None or not callable(fn):
            raise ContractError(f"verifier {spec!r} does not resolve to a callable")
        return inspect.getsource(fn).encode("utf-8")
    path = repo_root / spec
    if not path.is_file():
        raise ContractError(f"verifier path does not resolve: {spec}")
    return path.read_bytes()


def _resolve_verifier_exists(spec: str, repo_root: pathlib.Path) -> None:
    """Raises ContractError unless spec resolves to something real on disk."""
    _verifier_source_bytes(spec, repo_root)


# ---------------------------------------------------------------------------
# validate_card (T12, T15's vacuity half)
# ---------------------------------------------------------------------------

def validate_card(doc: Mapping[str, Any]) -> Card:
    io.load_schema("card").validate(doc)
    card = Card.from_dict(doc)
    repo_root = io.repo_root()

    task_path = repo_root / card.task_path
    if not task_path.exists():
        raise ContractError(f"validate_card: {card.card_id}: task_path does not resolve: {card.task_path}")

    pass_fixture = repo_root / card.pass_fixture
    if not pass_fixture.is_dir():
        raise ContractError(
            f"validate_card: {card.card_id}: pass_fixture does not resolve to a directory: {card.pass_fixture}"
        )
    fail_fixture = repo_root / card.fail_fixture
    if not fail_fixture.is_dir():
        raise ContractError(
            f"validate_card: {card.card_id}: fail_fixture does not resolve to a directory: {card.fail_fixture}"
        )

    _resolve_verifier_exists(card.outcome_verifier, repo_root)
    _resolve_verifier_exists(card.adoption_verifier, repo_root)

    if card.outcome_verifier == card.adoption_verifier:
        raise VacuousVerifier(
            f"{card.card_id}: outcome_verifier and adoption_verifier are the same entry point "
            f"({card.outcome_verifier!r}) -- the 2x2 collapses to its diagonal"
        )
    if _verifier_source_bytes(card.outcome_verifier, repo_root) == _verifier_source_bytes(
        card.adoption_verifier, repo_root
    ):
        raise VacuousVerifier(
            f"{card.card_id}: outcome_verifier and adoption_verifier resolve to identical source"
        )

    if card.kind is CardKind.NEAR_MISS:
        if not card.expected_boundary_verdict:
            raise ContractError(
                f"validate_card: {card.card_id}: near-miss card requires a non-empty "
                "expected_boundary_verdict"
            )
    elif card.expected_boundary_verdict:
        raise ContractError(
            f"validate_card: {card.card_id}: expected_boundary_verdict must be '' for kind "
            f"{card.kind.value!r}"
        )

    if not card.mutations:
        raise ContractError(f"validate_card: {card.card_id}: mutations must be non-empty (T10)")
    unknown = [m for m in card.mutations if m not in MUTATIONS]
    if unknown:
        raise ContractError(
            f"validate_card: {card.card_id}: mutation(s) not in controls.MUTATIONS: {unknown!r}"
        )

    return card


def validate_arm_manifest(doc: Mapping[str, Any]) -> Any:
    """Contract §3.10 types this ``-> "Arm"``. ``pairing.py`` (the module that
    defines ``Arm``) is explicitly out of this delivery's scope -- see the
    task brief's part-1/part-2 split for T16/T17 -- so this function cannot
    be fully implemented or tested here without importing a module that does
    not exist yet. Reported deviation, not a silent stub: the ``pairing``
    import is deferred to call time (so importing ``validate`` today never
    fails), and this performs the structural checks that do not depend on
    ``Arm``'s eventual constructor shape. Part 2 should give ``pairing.Arm``
    a ``from_dict`` classmethod following the §2.3 convention (Arm is not one
    of the frozen §2.3 dataclasses, so the contract does not spell this out
    explicitly) and this function will then construct a real ``Arm``.
    """
    if not isinstance(doc, Mapping):
        raise ContractError("validate_arm_manifest: expected a JSON object")
    for required in ("arm_id", "estimand", "role"):
        if required not in doc:
            raise ContractError(f"validate_arm_manifest: missing required key {required!r}")
    try:
        from . import pairing  # deferred: pairing.py lands in part 2
    except ImportError as exc:
        raise ContractError(
            "validate_arm_manifest: evals.agentic.framework.pairing is not implemented yet "
            "(part 2 of the registry lane)"
        ) from exc
    from_dict = getattr(pairing.Arm, "from_dict", None)
    if from_dict is None:
        raise ContractError(
            "validate_arm_manifest: pairing.Arm has no from_dict(); part 2 must add one "
            "(§2.3 convention) for validate_arm_manifest to construct a real Arm"
        )
    return from_dict(doc)


def validate_run_manifest(doc: Mapping[str, Any]) -> Manifest:
    io.load_schema("run-manifest").validate(doc)
    return Manifest.from_dict(doc)


def load_cards(repo_root: pathlib.Path) -> tuple[Card, ...]:
    repo_root = pathlib.Path(repo_root)
    tasks_dir = repo_root / "evals" / "agentic" / _TASKS_DIRNAME
    if not tasks_dir.is_dir():
        return ()
    cards: list[Card] = []
    for card_json in sorted(tasks_dir.rglob(_CARD_FILENAME)):
        doc = io.load_json(card_json)
        cards.append(validate_card(doc))
    ids = [c.card_id for c in cards]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        raise ContractError(f"load_cards: duplicate card_id(s) across tasks/**: {dupes!r}")
    return tuple(cards)


# ---------------------------------------------------------------------------
# Coverage (T12)
# ---------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True, slots=True)
class Coverage:
    per_plugin: Mapping[str, Mapping[CardKind, int]]
    missing: tuple[tuple[str, CardKind], ...]
    total_cards: int

    def is_complete(self) -> bool:
        return len(self.missing) == 0


def coverage_report(cards: Sequence[Card], roster: Sequence[PluginRef]) -> Coverage:
    per_plugin: dict[str, dict[CardKind, int]] = {p.name: {k: 0 for k in CardKind} for p in roster}
    roster_names = set(per_plugin)
    for card in cards:
        if card.plugin not in per_plugin:
            raise ContractError(
                f"coverage_report: card {card.card_id} names plugin {card.plugin!r}, "
                f"which is not in the derived roster {sorted(roster_names)!r}"
            )
        per_plugin[card.plugin][card.kind] += 1
    missing = tuple(
        (name, kind)
        for name in sorted(per_plugin)
        for kind in CardKind
        if per_plugin[name][kind] < 1
    )
    return Coverage(per_plugin=per_plugin, missing=missing, total_cards=len(cards))


def assert_triplet_completeness(coverage: Coverage) -> None:
    if coverage.missing:
        rendered = ", ".join(f"{name}/{kind.value}" for name, kind in coverage.missing)
        raise CoverageGap(f"coverage gap ({len(coverage.missing)} plugin/kind cell(s) missing): {rendered}")


# ---------------------------------------------------------------------------
# Leakage / holdout (T18)
# ---------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True, slots=True)
class Overlap:
    card_id: str
    surface_path: str
    ngram: str
    length: int


_WORD_RE = re.compile(r"[A-Za-z0-9_]+")


def _tokenize(text: str) -> tuple[str, ...]:
    return tuple(m.group(0).lower() for m in _WORD_RE.finditer(text))


def _ngrams(tokens: Sequence[str], n: int) -> Iterator[tuple[str, ...]]:
    if n <= 0 or len(tokens) < n:
        return
    for i in range(len(tokens) - n + 1):
        yield tuple(tokens[i : i + n])


def _card_hidden_text(card: Card, repo_root: pathlib.Path) -> str:
    """The text a leaked instruction would let a model reproduce for free:
    both verifiers' own source, plus the card's task-fixture prose. Verifier
    internals are explicitly named by T18(b) ("verifier internals" must not
    appear in any arm-visible surface); the task fixture is what T18(b) calls
    "expected-artifact strings"."""
    parts: list[str] = []
    for spec in (card.outcome_verifier, card.adoption_verifier):
        try:
            parts.append(_verifier_source_bytes(spec, repo_root).decode("utf-8", errors="ignore"))
        except ContractError:
            continue
    task_path = repo_root / card.task_path
    if task_path.is_dir():
        for f in sorted(task_path.rglob("*")):
            if f.is_file():
                try:
                    parts.append(f.read_text(encoding="utf-8", errors="ignore"))
                except OSError:
                    continue
    elif task_path.is_file():
        parts.append(task_path.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(parts)


def scan_leakage(
    cards: Sequence[Card], surfaces: Sequence[pathlib.Path], *, min_tokens: int = 8
) -> tuple[Overlap, ...]:
    repo_root = io.repo_root()
    overlaps: list[Overlap] = []
    for card in cards:
        hidden_tokens = _tokenize(_card_hidden_text(card, repo_root))
        hidden_ngrams = set(_ngrams(hidden_tokens, min_tokens))
        if not hidden_ngrams:
            continue
        for surface in surfaces:
            surface_path = pathlib.Path(surface)
            if not surface_path.is_file():
                continue
            try:
                surface_text = surface_path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            surface_tokens = _tokenize(surface_text)
            seen_here: set[tuple[str, ...]] = set()
            for gram in _ngrams(surface_tokens, min_tokens):
                if gram in hidden_ngrams and gram not in seen_here:
                    seen_here.add(gram)
                    overlaps.append(
                        Overlap(
                            card_id=card.card_id,
                            surface_path=str(surface_path),
                            ngram=" ".join(gram),
                            length=min_tokens,
                        )
                    )
    return tuple(overlaps)


def assert_no_leakage(overlaps: Sequence[Overlap]) -> None:
    if overlaps:
        rendered = "; ".join(f"{o.card_id} <-> {o.surface_path}: {o.ngram!r}" for o in overlaps)
        raise LeakageDetected(f"{len(overlaps)} leaked n-gram(s): {rendered}")


def holdout_ids(cards: Sequence[Card]) -> frozenset[str]:
    return frozenset(c.card_id for c in cards if c.holdout)


def assert_holdout_unread(manifest: Manifest, cards: Sequence[Card]) -> None:
    hidden = holdout_ids(cards)
    visible = set(manifest.planned_n.keys())
    leaked = hidden & visible
    if leaked:
        raise LeakageDetected(
            f"holdout card id(s) present in run manifest planned_n: {sorted(leaked)!r}"
        )


# ---------------------------------------------------------------------------
# CLI: python3 -m evals.agentic.framework.validate --corpus [--json]
# ---------------------------------------------------------------------------

def _build_coverage_document(repo_root: pathlib.Path) -> dict[str, Any]:
    roster = derive_roster(repo_root)
    cards = load_cards(repo_root)
    coverage = coverage_report(cards, roster)
    measured_plugins = sum(
        1
        for name, counts in coverage.per_plugin.items()
        if sum(counts.values()) >= _MIN_CLUSTERS_FLOOR
    )
    return {
        "generated_at": now_rfc3339(),
        "roster_size": len(roster),
        "total_cards": coverage.total_cards,
        "per_plugin": {
            name: {kind.value: n for kind, n in counts.items()}
            for name, counts in coverage.per_plugin.items()
        },
        "missing": [{"plugin": name, "kind": kind.value} for name, kind in coverage.missing],
        "complete": coverage.is_complete(),
        "measured_plugins": measured_plugins,
    }


def _cli(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python3 -m evals.agentic.framework.validate")
    parser.add_argument("--corpus", action="store_true", help="run corpus/coverage validation")
    parser.add_argument("--json", action="store_true", help="emit the coverage-schema JSON document")
    args = parser.parse_args(argv)

    if not args.corpus:
        parser.error("--corpus is required")
        return 2  # pragma: no cover -- parser.error() already exits

    repo_root = io.repo_root()
    try:
        doc = _build_coverage_document(repo_root)
    except ContractError as exc:
        print(f"registry FAIL corpus: {exc}", file=sys.stderr)
        return 1

    io.load_schema("coverage").validate(doc)

    if args.json:
        print(json.dumps(doc, indent=2, sort_keys=True))
    else:
        print(
            f"registry coverage: roster_size={doc['roster_size']} "
            f"total_cards={doc['total_cards']} complete={doc['complete']} "
            f"measured_plugins={doc['measured_plugins']} (min_clusters={_MIN_CLUSTERS_FLOOR})"
        )
        missing_plugins = sorted({m["plugin"] for m in doc["missing"]})
        if missing_plugins:
            print(f"plugins still missing >=1 card kind ({len(missing_plugins)}): " + ", ".join(missing_plugins))
        else:
            print("every roster plugin has all three card kinds")

    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
