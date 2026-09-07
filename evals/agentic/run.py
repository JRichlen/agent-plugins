#!/usr/bin/env python3
"""evals/agentic/run.py — the public CLI for the agentic test framework.

Integration-owned (contract §6 SHARED files, §9.2/§9.3, §10.6). This module
deliberately imports NOTHING from evals.agentic.framework at module scope
before it has put the correct repo root on ``sys.path`` — the same
``.claude-plugin/marketplace.json``-ancestor walk ``io.repo_root()`` performs
(contract §3.2), done here first because a plain script invoked as
``python3 evals/agentic/run.py`` does not otherwise have the repository root
importable as the ``evals`` package (only the script's own directory is on
``sys.path`` by default).

Subcommands / flags (contract §9.2), exactly:
  (no flag) / --offline   full offline suite + catalog + run manifest
  --gate                  root-portable subset (§9.3), terse, no manifest
  --id T07                run one catalog entry
  --lane <lane>           run one lane's catalog entries
  --catalog               the §7.4 fail-closed catalog walk
  coverage [--json]       delegates to registry.coverage_document
  driver --dry-run --name {claude,codex}
  driver --spawn --approval-token <tok> --name {claude,codex}
  plan [--seed N] [--repeats N] [--json]
                          REPAIR S-10/CV-12: the dispatch plan --
                          cells x arms x repeats, with each planned attempt's
                          holdout paraphrase selected deterministically from
                          the run seed. Dispatches nothing and spawns nothing;
                          it is what makes Manifest.planned_n a real,
                          externally-checkable declaration instead of `{}`.
  report --manifest <path> --attempts-dir <dir> [--out-dir <dir>]
         [--event-ledger <path>]
                          REPAIR S-12: loads a run manifest + a directory of
                          raw evals.agentic.schemas/attempt.schema.json
                          documents, builds an accounting.AttemptLedger from
                          them, and calls reporting.build_report /
                          render_text / render_json / render_markdown for
                          real -- the seam the measurement lane's
                          build_report/render_* had no production caller
                          through prior to this. Not in the frozen §9.2 flag
                          table (same footing as the pre-existing `coverage`
                          subcommand, itself an addition beyond that table);
                          it introduces no new subcommand token into any
                          --gate/--catalog/--offline path and no flag here
                          ever spawns a model either.

No flag anywhere enables a model call. ``driver --spawn`` always raises
ApprovalRequired (contract §10.6) — it is not on the --gate or --offline path.
"""
from __future__ import annotations

import argparse
import ast
import dataclasses
import importlib
import inspect
import json
import os
import pathlib
import re
import subprocess
import sys
import unittest

# ---------------------------------------------------------------------------
# Repo-root bootstrap. MUST happen before any `from evals.agentic...` import.
# ---------------------------------------------------------------------------

_HERE = pathlib.Path(__file__).resolve()


def _find_repo_root(start: pathlib.Path) -> pathlib.Path:
    for candidate in (start, *start.parents):
        if (candidate / ".claude-plugin" / "marketplace.json").is_file():
            return candidate
    raise SystemExit(
        f"evals/agentic/run.py: no ancestor of {start} contains "
        ".claude-plugin/marketplace.json -- cannot locate the repo root"
    )


REPO_ROOT = _find_repo_root(_HERE)
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evals.agentic.framework import io  # noqa: E402
from evals.agentic.framework import registry  # noqa: E402
from evals.agentic.framework import adapters  # noqa: E402
from evals.agentic.framework import pairing  # noqa: E402
from evals.agentic.framework import protocols  # noqa: E402
from evals.agentic.framework import accounting  # noqa: E402
from evals.agentic.framework import analysis  # noqa: E402
from evals.agentic.framework import reporting  # noqa: E402
from evals.agentic.framework import validate  # noqa: E402
from evals.agentic.framework.contract import (  # noqa: E402
    ALL_IDS,
    AccountingLeak,
    ApprovalGate,
    ApprovalRequired,
    Attempt,
    CatalogUnresolvable,
    ContractError,
    Estimand,
    ExposureParityViolation,
    ForgedProvenance,
    LedgerTampered,
    Manifest,
    SignatureClass,
    VacuousVerifier,
    digest,
    now_rfc3339,
)

PROVEN_RE = re.compile(r"\b52\b[^\n]{0,40}\bproven\b")

# --gate exclusion set (contract §9.3, with one deliberate, documented
# correction). Frozen contract text lists T11, T12, T15, T19-T23 as
# requires_real_marketplace and T51 as reentrant_unsafe (43 of 52 run under
# --gate). This runner ALSO excludes T50: its compaction sub-path genuinely
# drives the real plugins/redgate and plugins/voice SessionStart handlers
# (backlog T50(d)), which do not exist in the counterfeit corpus's synthetic
# root (one sample-guard plugin, no plugins/redgate or plugins/voice) --
# exactly the same structural reason T22 (the identical fixture) is already
# excluded. Running T50 under --gate in that root would either crash or
# silently skip the compaction assertion, both of which ground rule 4 (fail
# closed, never a silent skip) forbids. This mirrors the catalog entry's own
# `requires_real_marketplace` flag (see manifests/catalog/integration.json)
# and is reported as a deviation in the integration lane's own report, not
# hidden here.


def _load_index(repo_root: pathlib.Path) -> dict[str, list[str]]:
    index_path = repo_root / registry.CATALOG_DIR / "index.json"
    doc = io.load_json(index_path)
    ids_by_lane = doc.get("ids") if isinstance(doc, dict) else None
    if not isinstance(ids_by_lane, dict):
        raise SystemExit(f"run.py: {index_path} has no 'ids' mapping")
    return ids_by_lane


def _merge_catalog_reporting(repo_root: pathlib.Path):
    """Mirror registry.load_catalog's merge checks (contract §7.3) but return
    per-ID failures in the FROZEN §7.4 item 3a wording instead of raising one
    combined exception. Used by --catalog so a removed/misfiled ID (fixture
    20) is reported as ``agentic FAIL catalog: <ID> does not resolve
    (<reason>)`` on its own line, exactly as specified.

    Returns (entries: dict[str, registry.CatalogEntry], failures: dict[str, str])
    -- failures maps ID -> one of the four frozen reasons.
    """
    ids_by_lane = _load_index(repo_root)
    allocated_lane_of: dict[str, str] = {}
    for lane, ids in ids_by_lane.items():
        for entry_id in ids:
            allocated_lane_of[entry_id] = lane

    seen_in: dict[str, list[str]] = {}
    raw_by_id: dict[str, tuple[str, dict]] = {}
    for lane in sorted(ids_by_lane):
        fragment_path = repo_root / registry.CATALOG_DIR / f"{lane}.json"
        if not fragment_path.is_file():
            for entry_id in ids_by_lane[lane]:
                seen_in.setdefault(entry_id, []).append(lane)
            continue
        fragment = io.load_json(fragment_path)
        for raw_entry in fragment.get("entries", []) if isinstance(fragment, dict) else []:
            entry_id = raw_entry.get("id") if isinstance(raw_entry, dict) else None
            if not entry_id:
                continue
            seen_in.setdefault(entry_id, []).append(lane)
            raw_by_id[entry_id] = (lane, raw_entry)

    failures: dict[str, str] = {}
    for tid in ALL_IDS:
        lanes_seen = seen_in.get(tid, [])
        if len(lanes_seen) == 0:
            failures[tid] = "absent from fragment"
        elif len(lanes_seen) > 1:
            failures[tid] = "duplicate"
        else:
            frag_lane, raw_entry = raw_by_id[tid]
            expected_lane = allocated_lane_of.get(tid)
            if expected_lane is None or frag_lane != expected_lane or raw_entry.get("lane") != expected_lane:
                failures[tid] = f"not allocated to lane {frag_lane}"

    entries: dict[str, registry.CatalogEntry] = {}
    if not failures:
        try:
            catalog = registry.load_catalog(repo_root)
            entries = dict(catalog.entries)
        except CatalogUnresolvable as exc:
            # Merge succeeded by our own bookkeeping above but registry's
            # stricter constructor still refused (e.g. a malformed entry
            # object) -- report it rather than crash.
            for tid in ALL_IDS:
                failures.setdefault(tid, f"import failed: {exc}")
    return entries, failures


def _load_catalog_safely(repo_root: pathlib.Path):
    entries, failures = _merge_catalog_reporting(repo_root)
    return entries, failures


# ---------------------------------------------------------------------------
# Declared-before-the-run analysis floors (benchmark-spec §0/§7).
#
# REPAIR S-05: these are the SINGLE source of truth for this runner. Every
# manifest it writes carries them, and every analysis call it makes reads them
# back out rather than taking `analysis.card_rate`'s permissive
# `min_valid: int = 1` default. A report that prints `min_valid=3` in its
# header while its own rates were computed at 1 is worse than no floor at all,
# because the header is the sentence a reader trusts.
# ---------------------------------------------------------------------------

MIN_VALID = 3
MIN_CLUSTERS = 8
NONINFERIORITY_MARGIN = 0.05
HOLDOUT_SEED = 1
#: Planned repeats per (cell, arm). Tied to MIN_VALID deliberately: planning
#: fewer trials than the floor a card must clear to be reportable would
#: guarantee "starved" cells before a single attempt was dispatched.
REPEATS_PER_CELL_ARM = MIN_VALID


# ---------------------------------------------------------------------------
# REPAIR S-10 / CV-12 — the dispatch plan
#
# S-10: `Manifest.planned_n` was written as `{}` and never populated, so
# `accounting.assert_planned_reconciles` -- the ONE external check available
# to the report layer (conserve()/assert_reconciles() are tautological against
# whatever ledger they are handed) -- was a permanent no-op. It is populated
# here, at dispatch, from cells x arms x repeats, BEFORE anything runs.
#
# CV-12: holdout paraphrases became first-class `card.json` fields but nothing
# read them, so every attempt still ran the one wording sitting in the
# agent-visible task file. Selection happens here, per planned attempt,
# deterministically from the run seed -- same seed, same assignment, on any
# host, with no `random` module state anywhere -- and the chosen variant is
# recorded on the attempt itself.
# ---------------------------------------------------------------------------

ARMS_DIRNAME = ("evals", "agentic", "manifests", "arms")
#: The two arm documents every per-plugin manifest carries (registry lane's
#: manifests/arms/README.md). Sorted, so the plan is order-stable.
ARM_KEYS = ("baseline_arm", "full_package_arm")

#: The exact form a selected paraphrase takes in `Attempt.notes`.
#: `contract.Attempt` is core-owned and frozen -- it has no `paraphrase_id`
#: field and this lane cannot add one -- so `notes` (its documented free-text
#: field) carries it in a single parseable shape rather than in prose. See
#: known-gaps.md for what a first-class field would take.
PARAPHRASE_NOTE_RE = re.compile(
    r"paraphrase=(?P<index>\d+)/(?P<total>\d+) digest=(?P<digest>[0-9a-f]{16})"
)


@dataclasses.dataclass(frozen=True, slots=True)
class PlannedAttempt:
    cell_id: str
    card_id: str
    arm_id: str
    arm_role: str
    repeat: int
    paraphrase_index: int | None
    paraphrase_total: int
    paraphrase_digest: str | None

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


def paraphrase_note(planned: PlannedAttempt) -> str:
    """The note recorded on the attempt this plan row dispatches."""
    if planned.paraphrase_index is None:
        return "paraphrase=none (card declares no holdout paraphrases)"
    return (
        f"paraphrase={planned.paraphrase_index}/{planned.paraphrase_total} "
        f"digest={planned.paraphrase_digest}"
    )


def paraphrase_from_notes(notes: str) -> tuple[int, int, str] | None:
    """Recover (index, total, digest) from an attempt's notes, or None."""
    match = PARAPHRASE_NOTE_RE.search(notes or "")
    if match is None:
        return None
    return int(match.group("index")), int(match.group("total")), match.group("digest")


def _select_paraphrase(seed: int, card_id: str, arm_id: str, repeat: int, total: int) -> int:
    """Deterministic, host-independent, seed-derived choice.

    `contract.digest` is sha256 over canonical JSON -- not `random`, whose
    global state a concurrent caller can perturb, and not `hash()`, which is
    salted per process. Same (seed, card, arm, repeat) always selects the same
    variant; a different seed reassigns the whole run.
    """
    stream = digest({"seed": seed, "card": card_id, "arm": arm_id, "repeat": repeat})
    return int(stream, 16) % total


def dispatch_plan(
    repo_root: pathlib.Path,
    *,
    seed: int = HOLDOUT_SEED,
    repeats: int = REPEATS_PER_CELL_ARM,
) -> tuple[PlannedAttempt, ...]:
    """Every attempt this run intends to dispatch: cells x arms x repeats.

    A cell is a card. Arms come from that plugin's committed arm manifest
    (`manifests/arms/<plugin>.json`), so the plan is derived from the same
    documents `--gate`'s exposure-parity probe checks, never from a count
    written down by hand. A card whose plugin has no arm manifest is a hard
    failure: silently planning zero attempts for it is precisely the shortfall
    `assert_planned_reconciles` exists to refuse.
    """
    if repeats < 1:
        raise ContractError(f"dispatch_plan: repeats must be >= 1, got {repeats!r}")
    cards = validate.load_cards(repo_root)
    arms_dir = repo_root.joinpath(*ARMS_DIRNAME)
    plan: list[PlannedAttempt] = []
    for card in sorted(cards, key=lambda c: c.card_id):
        arm_path = arms_dir / f"{card.plugin}.json"
        if not arm_path.is_file():
            raise ContractError(
                f"dispatch_plan: {card.card_id} names plugin {card.plugin!r}, which has no "
                f"arm manifest at {arm_path.relative_to(repo_root)} -- refusing to plan "
                "zero attempts for a real cell"
            )
        arm_doc = io.load_json(arm_path)
        paraphrases = validate.card_paraphrases(card, repo_root)
        total = len(paraphrases)
        for arm_key in ARM_KEYS:
            arm = pairing.Arm.from_dict(arm_doc[arm_key])
            for repeat in range(repeats):
                if total:
                    index = _select_paraphrase(seed, card.card_id, arm.arm_id, repeat, total)
                    para_digest = digest(paraphrases[index])[:16]
                else:
                    index, para_digest = None, None
                plan.append(PlannedAttempt(
                    cell_id=card.card_id,
                    card_id=card.card_id,
                    arm_id=arm.arm_id,
                    arm_role=arm.role.value,
                    repeat=repeat,
                    paraphrase_index=index,
                    paraphrase_total=total,
                    paraphrase_digest=para_digest,
                ))
    return tuple(plan)


def planned_n_of(plan: "tuple[PlannedAttempt, ...]") -> dict[str, int]:
    """cell id -> planned trials, the shape `Manifest.planned_n` declares."""
    counts: dict[str, int] = {}
    for row in plan:
        counts[row.cell_id] = counts.get(row.cell_id, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# REPAIR F1 — structural binding: entry.negative_control <-> the sibling
# ---------------------------------------------------------------------------
#
# §7.4's "an executable negative control" was enforced as two INDEPENDENT
# checks: `(repo_root / entry.negative_control).exists()` and
# `hasattr(cls, name + "__negative")`. Both can be true while naming
# completely unrelated things -- F1's repro swapped an entry's
# `negative_control` for an unrelated POSITIVE fixture and nothing noticed,
# because every lane's `__negative` method hardcodes its own fixture path with
# no reference to the catalog field at all. The catalog's central claim ("this
# ID's negative control is THAT artifact") was therefore unfalsifiable.
#
# This binds them. Four ways an entry can be bound, strongest first; each is a
# real, distinct way a Python test refers to a file, and every one of them is
# falsified by pointing the catalog at a different artifact:
#
#   declared    -- the sibling method (or its class) carries a
#                  `negative_control` attribute equal to the catalog field.
#                  Exact, unambiguous, and the only form that cannot drift.
#                  Integration and adapter lane siblings declare it.
#   constructed -- a statically resolvable path expression in the sibling (or
#                  its module) evaluates to the negative control, or to a path
#                  INSIDE it when the control is a directory. Module-level and
#                  local `X = ROOT / "a" / "b"` bindings are followed.
#   named       -- a string literal in the sibling (or its module) contains
#                  the control path down to at least its last two segments,
#                  right-boundary anchored so `oracle/guarded-delete` does not
#                  match `oracle/guarded-delete-no-side-effects`. This is the
#                  existing convention where a sibling's own docstring quotes
#                  `entry.negative_control`.
#   segmented   -- the sibling's literals name the control's leaf segment AND
#                  a non-structural ancestor segment (structural = a directory
#                  segment shared by a quarter or more of the catalog, i.e.
#                  `evals`/`agentic`/`fixtures`, which carry no information).
#
# Honest limit, recorded in known-gaps.md: all four are SOURCE-REFERENCE
# bindings. They prove the sibling names its control; they do not prove it
# reads it at run time. The strongest available form -- registry.run_entry
# passing `entry.negative_control` into the method -- needs framework/
# registry.py plus a signature change in every lane's test files, none of
# which this lane owns.

_BINDING_STRUCTURAL_SHARE = 4  # a segment in >= 1/4 of controls carries no information


def _segments(path: str) -> list[str]:
    return [s for s in str(path).replace("\\", "/").split("/") if s]


def _structural_segments(entries) -> frozenset[str]:
    counts: dict[str, int] = {}
    total = 0
    for entry in entries:
        total += 1
        for seg in set(_segments(entry.negative_control)[:-1]):
            counts[seg] = counts.get(seg, 0) + 1
    return frozenset(
        seg for seg, n in counts.items() if n * _BINDING_STRUCTURAL_SHARE >= total
    )


def _sibling_node(tree: "ast.Module", class_name: str, method_name: str):
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == method_name:
                    return child
    return None


def _resolve_path_expr(node, module, locals_: dict[str, str]) -> str | None:
    """Fold a `Path / "a" / "b"` (or os.path.join) expression to a string.

    Only reads values that are already strings or PathLike; never calls
    anything, so importing a test module is the only code this runs.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        if node.id in locals_:
            return locals_[node.id]
        value = getattr(module, node.id, None)
        return str(value) if isinstance(value, (str, os.PathLike)) else None
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        if node.value.id in locals_:
            return None
        base = getattr(module, node.value.id, None)
        value = getattr(base, node.attr, None) if base is not None else None
        return str(value) if isinstance(value, (str, os.PathLike)) else None
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        left = _resolve_path_expr(node.left, module, locals_)
        right = _resolve_path_expr(node.right, module, locals_)
        if left is None or right is None:
            return None
        return str(pathlib.PurePosixPath(left) / right)
    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "join":
            parts = [_resolve_path_expr(a, module, locals_) for a in node.args]
            if parts and all(parts):
                return str(pathlib.PurePosixPath(*parts))  # type: ignore[arg-type]
    return None


def _constructed_paths(node, module) -> set[str]:
    locals_: dict[str, str] = {}
    for stmt in ast.walk(node):
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
            value = _resolve_path_expr(stmt.value, module, locals_)
            if value:
                locals_[stmt.targets[0].id] = value
    out: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, (ast.BinOp, ast.Call)):
            value = _resolve_path_expr(child, module, locals_)
            if value:
                out.add(value)
    return out


def _string_literals(node) -> list[str]:
    return [
        n.value for n in ast.walk(node)
        if isinstance(n, ast.Constant) and isinstance(n.value, str)
    ]


def _constructed_bound(node, module, repo_root: pathlib.Path, control: str) -> bool:
    target = pathlib.PurePosixPath(control)
    for raw in _constructed_paths(node, module):
        candidate = pathlib.PurePosixPath(raw)
        try:
            relative = candidate.relative_to(pathlib.PurePosixPath(repo_root))
        except ValueError:
            if not raw.startswith("evals/"):
                continue
            relative = candidate
        if relative == target or target in relative.parents:
            return True
    return False


def _named_bound(literals: list[str], control: str) -> bool:
    segments = _segments(control)
    for k in range(len(segments), 1, -1):
        tail = "/".join(segments[-k:])
        pattern = re.compile(re.escape(tail) + r"(?![A-Za-z0-9_.\-])")
        if any(pattern.search(text) for text in literals):
            return True
    return False


def _segmented_bound(literals: list[str], control: str, structural: frozenset[str]) -> bool:
    components: set[str] = set()
    for text in literals:
        components.add(text)
        components.update(_segments(text))
    segments = _segments(control)
    if segments[-1] not in components:
        return False
    return any(seg in components for seg in segments[:-1] if seg not in structural)


def negative_control_binding(
    repo_root: pathlib.Path,
    entry,
    cls: type,
    method_name: str,
    structural: frozenset[str],
) -> str | None:
    """Return HOW ``entry.negative_control`` is bound to the sibling, or None.

    None means the sibling makes no reference to the artifact the catalog
    says is its negative control -- ``agentic FAIL catalog: <ID> negative
    control not bound``.
    """
    sibling_name = method_name + "__negative"
    sibling = getattr(cls, sibling_name, None)
    if sibling is None:
        return None

    declared = getattr(sibling, "negative_control", None)
    if declared is None:
        declared = getattr(cls, "negative_control", None)
    if declared is not None:
        # A lane that has opted into declaring is held to it EXACTLY: a
        # declaration that disagrees with the catalog is a contradiction, and
        # falling through to the weaker source-scan tiers would let the
        # catalog be re-pointed at some other artifact the same module
        # happens to mention. Declared is authoritative in both directions.
        matches = (
            declared == entry.negative_control
            if isinstance(declared, str)
            else entry.negative_control in declared
            if isinstance(declared, (tuple, list))
            else False
        )
        return "declared" if matches else None

    try:
        module = importlib.import_module(entry.module)
        tree = ast.parse(inspect.getsource(module))
    except (ImportError, OSError, SyntaxError, TypeError):
        return None

    node = _sibling_node(tree, entry.test_class, sibling_name)
    control = entry.negative_control
    for scope, label in ((node, "sibling"), (tree, "module")):
        if scope is None:
            continue
        if _constructed_bound(scope, module, repo_root, control):
            return f"constructed ({label})"
        literals = _string_literals(scope)
        if _named_bound(literals, control):
            return f"named ({label})"
        if _segmented_bound(literals, control, structural):
            return f"segmented ({label})"
    return None


# ---------------------------------------------------------------------------
# --catalog (contract §7.4)
# ---------------------------------------------------------------------------

def cmd_catalog(repo_root: pathlib.Path) -> int:
    entries, load_failures = _load_catalog_safely(repo_root)
    lines: list[str] = []
    exit_code = 0

    for tid in ALL_IDS:
        if tid in load_failures:
            lines.append(f"agentic FAIL catalog: {tid} does not resolve ({load_failures[tid]})")
            exit_code = 1

    executed = 0
    blocked = 0
    native_required = 0
    paid_required = 0
    structural = _structural_segments([entries[t] for t in ALL_IDS if t not in load_failures])

    for tid in ALL_IDS:
        if tid in load_failures:
            continue
        entry = entries[tid]

        if entry.approval_gate is not ApprovalGate.NONE:
            blocked += 1
            if entry.approval_gate is ApprovalGate.NATIVE_REQUIRED:
                native_required += 1
            else:
                paid_required += 1
            lines.append(f"{tid} BLOCKED — approval required ({entry.approval_gate.value})")
            continue

        try:
            cls, method_name = registry.resolve_test(entry)
        except CatalogUnresolvable as exc:
            lines.append(f"agentic FAIL catalog: {tid} does not resolve (import failed: {exc})")
            exit_code = 1
            continue

        neg_path = repo_root / entry.negative_control
        has_negative_sibling = hasattr(cls, method_name + "__negative")
        if not neg_path.exists() or not has_negative_sibling:
            lines.append(f"agentic FAIL catalog: {tid} has no executable negative control")
            exit_code = 1
            continue

        # REPAIR F1: the path and the sibling must be the SAME control, not
        # two independently-true facts (see negative_control_binding above).
        if negative_control_binding(repo_root, entry, cls, method_name, structural) is None:
            lines.append(f"agentic FAIL catalog: {tid} negative control not bound")
            exit_code = 1
            continue

        run = registry.run_entry(entry)
        if run.assertions < 1:
            lines.append(f"agentic FAIL catalog: {tid} executed 0 assertions")
            exit_code = 1
            continue
        if run.outcome != "pass":
            detail = (run.detail or "").strip().splitlines()
            tail = detail[-1] if detail else run.outcome
            lines.append(f"agentic FAIL catalog: {tid} failed ({tail})")
            exit_code = 1
            continue

        # REPAIR F1: "an executable negative control" means the __negative
        # sibling actually runs with real assertions and passes -- a bare
        # hasattr()/path-exists() pair above is a name check, not a proof
        # (F1's repro: an entry's negative_control swapped for an unrelated
        # POSITIVE fixture path went undetected because nothing here ever
        # executed the sibling method).
        neg_run = registry.run_entry(dataclasses.replace(entry, test_name=method_name + "__negative"))
        if neg_run.assertions < 1:
            lines.append(f"agentic FAIL catalog: {tid} negative control executed 0 assertions")
            exit_code = 1
            continue
        if neg_run.outcome != "pass":
            detail = (neg_run.detail or "").strip().splitlines()
            tail = detail[-1] if detail else neg_run.outcome
            lines.append(f"agentic FAIL catalog: {tid} negative control failed ({tail})")
            exit_code = 1
            continue

        executed += 1

    summary = (
        f"agentic catalog: 52 IDs, {executed} executed, {blocked} BLOCKED — "
        f"approval required (native-required={native_required}, paid-required={paid_required})"
    )
    lines.append(summary)
    output = "\n".join(lines)
    if PROVEN_RE.search(output):
        # This must never happen; if it does, it is itself the bug (ground
        # rule / handoff: never claim "52 ... proven").
        print("agentic FAIL catalog: summary line matched the banned proven-regex", file=sys.stderr)
        return 1
    print(output)
    return exit_code


# ---------------------------------------------------------------------------
# --gate structural probes (see the integration lane's report for why these
# exist alongside the catalog-entry run below: the frozen FAIL substrings in
# contract §8.8 must be reachable even for lanes (protocol's hook discovery)
# whose catalog-mapped test requires the real marketplace and is therefore
# excluded from --gate itself).
# ---------------------------------------------------------------------------

def _probe_vacuous_verifier(repo_root: pathlib.Path) -> str | None:
    try:
        from evals.agentic.tests import test_controls as tc
        from evals.agentic.framework import controls
    except Exception as exc:  # noqa: BLE001
        return f"agentic FAIL core: vacuous verifier probe could not load ({exc})"
    try:
        controls.assert_not_vacuous(tc.GUARDED_DELETE_CARD, tc.FIXTURES / "oracle" / "guarded-delete")
    except VacuousVerifier:
        return "agentic FAIL core: vacuous verifier"
    return None


def _probe_zero_denominator(repo_root: pathlib.Path) -> str | None:
    """REPAIR S-05: `min_valid` comes from the run's declared floor, never
    from `analysis.card_rate`'s permissive keyword default.

    `card_rate(trials)` with no `min_valid` silently takes 1, so a card could
    render 100% off a single sample under a manifest whose own header said
    `min_valid=3`. This runner has exactly one source for that number
    (`MIN_VALID`, written into every manifest it emits) and every call it
    makes passes it explicitly -- `tests/test_catalog.py` parses this file's
    AST and reds if any `analysis.card_rate` call here omits the keyword, so
    the discipline cannot be lost to a later edit.
    """
    import importlib.util

    fixtures_dir = repo_root / "evals" / "agentic" / "fixtures" / "measurement"
    spec = importlib.util.spec_from_file_location("agentic_gate_builders", fixtures_dir / "builders.py")
    builders = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builders)
    doc = io.load_json(fixtures_dir / "zero_denom" / "voice-neg-02.json")
    trials = builders.attempts_for_card(doc["card_id"], doc["all_fault_trials"])
    rate = analysis.card_rate(trials, min_valid=MIN_VALID)
    rendered = rate.render()
    if rate.value is not None or "unavailable" not in rendered or rendered.strip().endswith("%"):
        return "agentic FAIL measurement: zero denominator rendered as a number"

    # The floor itself must be load-bearing, not merely passed. The same
    # fixture ships `starved_trials` (2 evaluated verdicts) and the exact
    # sentence benchmark-spec §7 requires for it; at the permissive default
    # this renders 50%, which is the whole defect S-05 names.
    starved = builders.attempts_for_card(doc["card_id"], doc["starved_trials"])
    floored = analysis.card_rate(starved, min_valid=MIN_VALID)
    expected_reason = doc["expected"]["starved_reason"]
    if doc["expected"]["starved_min_valid"] != MIN_VALID:
        return (
            "agentic FAIL measurement: run.py's declared MIN_VALID "
            f"({MIN_VALID}) disagrees with the fixture's "
            f"({doc['expected']['starved_min_valid']})"
        )
    if floored.value is not None or expected_reason not in floored.render():
        return (
            "agentic FAIL measurement: min_valid floor is not load-bearing "
            f"({len(doc['starved_trials'])} valid trial(s) rendered "
            f"{floored.render()!r} at min_valid={MIN_VALID})"
        )
    return None


def _probe_forged_native(repo_root: pathlib.Path) -> str | None:
    from evals.agentic.framework.contract import Attempt, assert_native_backed

    class _EmptyLedger:
        def has_event(self, event_id: str) -> bool:
            return False

        def session_ids(self):
            return frozenset()

        def host_observed_session_ids(self):
            return frozenset()

        def is_verified(self) -> bool:
            return True

        def signature_class(self, event_id: str):
            return None

    attempts_dir = repo_root / "evals" / "agentic" / "fixtures" / "native" / "attempts"
    if not attempts_dir.is_dir():
        return None
    ledger = _EmptyLedger()
    for path in sorted(attempts_dir.glob("*.json")):
        try:
            doc = io.load_json(path)
            attempt = Attempt.from_dict(doc)
        except ContractError:
            # Not a raw Attempt record -- e.g. the adapter lane's own
            # documented negative-control fixture, which wraps the attempt
            # under a "PROVENANCE"/"attempt" envelope specifically so a
            # scanner like this one does not mistake it for live tampering.
            continue
        if attempt.evidence_class.value != "native-proven":
            continue
        try:
            assert_native_backed(attempt, ledger)
        except ForgedProvenance:
            return "agentic FAIL adapter: forged_provenance"
    return None


def _probe_hook_discovery(repo_root: pathlib.Path) -> str | None:
    tree = repo_root / "evals" / "agentic" / "fixtures" / "protocols"
    specs = protocols.discover_hooks(tree)
    if len(specs) != 3:
        return "agentic FAIL protocol: hook discovery missed"
    return None


def _probe_exposure_parity(repo_root: pathlib.Path) -> str | None:
    """REPAIR CV-10: every committed baseline arm, not just graveyard's.

    This probe used to open `manifests/arms/graveyard.json` and nothing else,
    so 24 of the 25 committed baseline arms were ungated: widening any other
    plugin's `baseline_arm.allowed_tools` (counterfeit fixture 25's exact
    defect) passed `--gate` silently. It now loops the whole directory in
    sorted order and NAMES the first plugin that fails, so the frozen
    substring still appears and the message says which manifest to look at.

    A missing/unreadable arm manifest is a failure, not a skip: a directory
    that has stopped producing arm documents is exactly how this probe would
    go quiet.
    """
    arms_dir = repo_root / "evals" / "agentic" / "manifests" / "arms"
    if not arms_dir.is_dir():
        return None
    arm_paths = sorted(p for p in arms_dir.glob("*.json"))
    if not arm_paths:
        return "agentic FAIL registry: exposure parity (no arm manifests under manifests/arms/)"
    for arm_path in arm_paths:
        plugin = arm_path.stem
        try:
            doc = io.load_json(arm_path)
            full = pairing.Arm.from_dict(doc["full_package_arm"])
            base = pairing.Arm.from_dict(doc["baseline_arm"])
        except (ContractError, KeyError, TypeError) as exc:
            return f"agentic FAIL registry: exposure parity ({plugin}: unreadable arm manifest: {exc})"
        try:
            pairing.assert_exposure_parity(full, base)
        except ExposureParityViolation as exc:
            return f"agentic FAIL registry: exposure parity ({plugin}: {exc})"
    return None


_STRUCTURAL_PROBES = (
    _probe_vacuous_verifier,
    _probe_zero_denominator,
    _probe_forged_native,
    _probe_hook_discovery,
    _probe_exposure_parity,
)


def cmd_gate(repo_root: pathlib.Path) -> int:
    """Root-portable subset (contract §9.3), terse, no manifest write.

    Perf note: T52's own catalog-mapped test (SuiteCatalogIntegrity) already
    performs a genuine registry.run_entry sweep over every non-excluded
    catalog ID as ITS OWN assertion (backlog T52: "runs each mapped
    selector"). Running that same sweep a second time here, entry by entry,
    would double the wall-clock cost of every real-subprocess check in the
    suite (T42's promptfoo validation and T48's docker netproof alone are
    ~30s each) for zero additional coverage. So --gate runs the five
    structural probes (which cover the frozen per-lane FAIL substrings T52's
    own test does not, e.g. hook discovery on the synthetic tree) plus T52
    itself, and trusts T52's internal sweep to have proven the rest. `--id`
    and `--lane` remain the way to run any OTHER single entry directly.
    """
    lines: list[str] = []
    fail = False

    for probe in _STRUCTURAL_PROBES:
        try:
            result = probe(repo_root)
        except Exception as exc:  # noqa: BLE001 -- a probe crashing is itself a gate failure
            result = f"agentic FAIL gate: structural probe {probe.__name__} crashed: {exc}"
        if result is not None:
            lines.append(result)
            fail = True

    entries, load_failures = _load_catalog_safely(repo_root)
    for tid, reason in sorted(load_failures.items()):
        lines.append(f"agentic FAIL catalog: {tid} does not resolve ({reason})")
        fail = True

    ran = 0
    if "T52" in entries:
        run = registry.run_entry(entries["T52"])
        ran += 1
        if run.outcome != "pass":
            detail = (run.detail or "").strip().splitlines()
            tail = detail[-1] if detail else run.outcome
            lines.append(f"agentic FAIL integration: T52 failed ({tail})")
            fail = True
    elif "T52" not in load_failures:
        lines.append("agentic FAIL catalog: T52 does not resolve (missing from merged catalog)")
        fail = True

    if fail:
        for line in lines:
            print(line)
        print(f"agentic gate: {ran} catalog entries checked, FAILURES ABOVE")
        return 1
    print(f"agentic gate: {ran} catalog entries (T52, which sweeps the rest) "
          f"+ {len(_STRUCTURAL_PROBES)} structural probes, all clean")
    return 0


# ---------------------------------------------------------------------------
# Default / --offline: full suite + catalog + manifest
# ---------------------------------------------------------------------------

def _detect_toolchain() -> dict[str, str]:
    toolchain: dict[str, str] = {"python": sys.version.split()[0]}
    try:
        out = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=10)
        if out.returncode == 0:
            toolchain["node"] = out.stdout.strip().lstrip("v")
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        pin = io.load_json(repo_root_pin := (REPO_ROOT / "evals" / "redteam" / "pin.json"))
        home = pin.get("promptfoo", {}).get("home")
        if home:
            pkg = io.load_json(pathlib.Path(home) / "package.json")
            version = pkg.get("version")
            if version:
                toolchain["promptfoo"] = version
    except (OSError, ContractError, KeyError, TypeError):
        pass
    return toolchain


def _git(repo_root: pathlib.Path, *args: str) -> str:
    out = subprocess.run(["git", *args], cwd=str(repo_root), capture_output=True, text=True, timeout=15)
    return out.stdout.strip()


def cmd_offline(repo_root: pathlib.Path) -> int:
    loader = unittest.TestLoader()
    suite = loader.discover(
        start_dir=str(repo_root / "evals" / "agentic" / "tests"), top_level_dir=str(repo_root)
    )
    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(suite)
    suite_ok = result.wasSuccessful()

    catalog_code = cmd_catalog(repo_root)

    entries, load_failures = _load_catalog_safely(repo_root)
    ids_by_lane = _load_index(repo_root)
    lanes = tuple(sorted(ids_by_lane))

    skipped = []
    for tid in ALL_IDS:
        if tid in load_failures:
            continue
        entry = entries[tid]
        if entry.approval_gate is not ApprovalGate.NONE:
            skipped.append({"id": tid, "reason": f"approval required ({entry.approval_gate.value})"})

    cat_digest = digest({"index": ids_by_lane, "entries": []})
    try:
        cat_digest = registry.load_catalog(repo_root).digest
    except CatalogUnresolvable:
        pass

    # REPAIR S-10: `planned_n` is populated from the real dispatch plan
    # (cells x arms x repeats) instead of being written as `{}`. It was the
    # single reason `accounting.assert_planned_reconciles` -- the only check
    # in the framework that compares the ledger against something declared
    # OUTSIDE it -- could never fire.
    #
    # An `--offline` run executes the test suite; it dispatches none of these
    # attempts. That shortfall is declared here in `skipped`, in the shape
    # `assert_planned_reconciles` reads, rather than hidden by leaving the
    # plan empty: "we planned 450 and ran 0, and here is why" is a checkable
    # statement, "{}" is not.
    plan = dispatch_plan(repo_root, seed=HOLDOUT_SEED, repeats=REPEATS_PER_CELL_ARM)
    planned = planned_n_of(plan)
    skipped.append({
        "id": "dispatch",
        "reason": (
            f"offline run: {len(plan)} planned attempts across {len(planned)} cells were "
            "not dispatched (--offline runs the test suite, not the corpus)"
        ),
    })

    manifest = Manifest(
        run_id=f"run-{now_rfc3339().replace(':', '').replace('.', '').replace('-', '')}",
        created_at=now_rfc3339(),
        git_commit=_git(repo_root, "rev-parse", "HEAD") or "0" * 40,
        branch=_git(repo_root, "rev-parse", "--abbrev-ref", "HEAD") or "unknown",
        offline=True,
        toolchain=_detect_toolchain(),
        lanes=lanes,
        estimands=tuple(Estimand),
        noninferiority_margin=NONINFERIORITY_MARGIN,
        min_valid=MIN_VALID,
        min_clusters=MIN_CLUSTERS,
        planned_n=planned,
        holdout_seed=HOLDOUT_SEED,
        catalog_digest=cat_digest,
        skipped=tuple(skipped),
        approvals=(),
    )
    manifest_doc = manifest.to_dict()
    io.load_schema("run-manifest").validate(manifest_doc)

    runs_dir = repo_root / "evals" / "agentic" / "manifests" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = runs_dir / f"{manifest.run_id}.json"
    io.dump_json(manifest_path, manifest_doc)
    io.dump_json(
        runs_dir / f"{manifest.run_id}-plan.json",
        {
            "run_id": manifest.run_id,
            "seed": HOLDOUT_SEED,
            "repeats_per_cell_arm": REPEATS_PER_CELL_ARM,
            "planned_attempts": [row.to_dict() for row in plan],
        },
    )

    ok = suite_ok and catalog_code == 0
    if ok:
        print(f"agentic: PASS (manifest: {manifest_path.relative_to(repo_root)})")
        return 0
    print(f"agentic FAIL suite: offline suite or catalog reported failures (manifest still written: "
          f"{manifest_path.relative_to(repo_root)})")
    return 1


# ---------------------------------------------------------------------------
# --id / --lane
# ---------------------------------------------------------------------------

def cmd_id(repo_root: pathlib.Path, entry_id: str) -> int:
    entries, load_failures = _load_catalog_safely(repo_root)
    if entry_id in load_failures:
        print(f"agentic FAIL catalog: {entry_id} does not resolve ({load_failures[entry_id]})")
        return 1
    if entry_id not in entries:
        print(f"agentic FAIL catalog: {entry_id} does not resolve (not in contract.ALL_IDS)")
        return 2
    entry = entries[entry_id]
    if entry.approval_gate is not ApprovalGate.NONE:
        print(f"{entry_id} BLOCKED — approval required ({entry.approval_gate.value})")
        return 0
    run = registry.run_entry(entry)
    print(f"{entry_id} [{entry.lane}] {entry.test_class}.{entry.test_name}: "
          f"{run.outcome} ({run.assertions} assertions)")
    return 0 if run.outcome == "pass" else 1


def cmd_lane(repo_root: pathlib.Path, lane: str) -> int:
    entries, load_failures = _load_catalog_safely(repo_root)
    ids_by_lane = _load_index(repo_root)
    if lane not in ids_by_lane:
        print(f"agentic FAIL lane: {lane!r} is not a known lane; known lanes: {sorted(ids_by_lane)}")
        return 2
    fail = False
    for tid in ids_by_lane[lane]:
        if tid in load_failures:
            print(f"agentic FAIL catalog: {tid} does not resolve ({load_failures[tid]})")
            fail = True
            continue
        entry = entries[tid]
        if entry.approval_gate is not ApprovalGate.NONE:
            print(f"{tid} BLOCKED — approval required ({entry.approval_gate.value})")
            continue
        run = registry.run_entry(entry)
        print(f"{tid} [{lane}] {entry.test_class}.{entry.test_name}: {run.outcome} ({run.assertions} assertions)")
        if run.outcome != "pass":
            fail = True
    return 1 if fail else 0


# ---------------------------------------------------------------------------
# coverage subcommand
# ---------------------------------------------------------------------------

def cmd_coverage(repo_root: pathlib.Path, as_json: bool) -> int:
    return registry.print_coverage(repo_root, as_json=as_json)


# ---------------------------------------------------------------------------
# driver subcommand
# ---------------------------------------------------------------------------

def cmd_report(repo_root: pathlib.Path, args: argparse.Namespace) -> int:
    """REPAIR S-12: a real (non-mocked) caller of accounting.AttemptLedger and
    reporting.build_report/render_text/render_json/render_markdown.

    Takes a run manifest (schemas/run-manifest.schema.json, as written by
    cmd_offline) and a directory of raw attempt records (each a
    schemas/attempt.schema.json document -- NOT the PROVENANCE-wrapped
    negative-control fixtures under fixtures/native/attempts/, which are
    deliberately not raw Attempt records so a scanner does not mistake them
    for live tampering; see _probe_forged_native above). Every file fails
    closed: a missing/empty directory, a schema-invalid document, or a
    ledger that fails to conserve is reported and refused, never silently
    skipped.
    """
    manifest_path = pathlib.Path(args.manifest)
    if not manifest_path.is_file():
        print(f"agentic FAIL report: manifest not found: {manifest_path}", file=sys.stderr)
        return 1
    manifest_doc = io.load_json(manifest_path)
    try:
        io.load_schema("run-manifest").validate(manifest_doc)
    except Exception as exc:  # noqa: BLE001 -- any schema violation is a hard refusal
        print(f"agentic FAIL report: manifest does not validate: {exc}", file=sys.stderr)
        return 1
    manifest = Manifest.from_dict(manifest_doc)

    attempts_dir = pathlib.Path(args.attempts_dir)
    if not attempts_dir.is_dir():
        print(f"agentic FAIL report: attempts dir not found: {attempts_dir}", file=sys.stderr)
        return 1
    attempt_paths = sorted(attempts_dir.glob("*.json"))
    if not attempt_paths:
        print(f"agentic FAIL report: no attempt records under {attempts_dir}", file=sys.stderr)
        return 1

    ledger = accounting.AttemptLedger(run_id=manifest.run_id)
    attempt_schema = io.load_schema("attempt")
    for path in attempt_paths:
        doc = io.load_json(path)
        try:
            attempt_schema.validate(doc)
        except Exception as exc:  # noqa: BLE001 -- schema violation is a hard refusal
            print(f"agentic FAIL report: {path.name} does not validate: {exc}", file=sys.stderr)
            return 1
        try:
            ledger.add(Attempt.from_dict(doc))
        except (ContractError, AccountingLeak) as exc:
            print(f"agentic FAIL report: {path.name}: {exc}", file=sys.stderr)
            return 1

    # REPAIR S-10: reconcile what the EVENT ledger says was spawned against
    # what the ATTEMPT ledger recorded. `AttemptLedger.conserve()` and
    # `Denominators.assert_reconciles()` both re-derive their comparison from
    # the very list they are checking, so neither can see a row dropped before
    # the ledger ever held it. The event ledger is the only external witness:
    # its SPAWN entries are written by the host when an attempt starts, and
    # they are hash-chained.
    event_ledger = None
    if getattr(args, "event_ledger", None):
        event_ledger_path = pathlib.Path(args.event_ledger)
        if not event_ledger_path.is_file():
            print(f"agentic FAIL report: event ledger not found: {event_ledger_path}", file=sys.stderr)
            return 1
        event_ledger = adapters.LedgerReader(event_ledger_path, key=None)
        try:
            event_ledger.assert_chain()
        except LedgerTampered as exc:
            print(f"agentic FAIL report: {exc}", file=sys.stderr)
            return 1
        accounting_view = event_ledger.spawn_exit_accounting()
        recorded = {a.attempt_id for a in ledger.attempts()}
        missing = accounting_view.missing_from(recorded)
        if missing:
            print(
                "agentic FAIL report: the event ledger records "
                f"{len(missing)} spawned attempt(s) the attempt ledger never recorded: "
                f"{', '.join(missing)}",
                file=sys.stderr,
            )
            return 1
        if accounting_view.unattributed:
            print(
                "agentic FAIL report: the event ledger holds "
                f"{accounting_view.unattributed} SPAWN/EXIT entr(ies) with no attempt_id -- "
                "an unattributable spawn is missing evidence, not absent evidence",
                file=sys.stderr,
            )
            return 1

    try:
        report = reporting.build_report(manifest, ledger, event_ledger)
    except (ContractError, AccountingLeak) as exc:
        print(f"agentic FAIL report: {exc}", file=sys.stderr)
        return 1

    out_dir = pathlib.Path(args.out_dir) if args.out_dir else manifest_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    text = reporting.render_text(report, event_ledger)
    markdown = reporting.render_markdown(report, event_ledger)
    as_json = reporting.render_json(report, event_ledger)
    (out_dir / f"{manifest.run_id}-report.txt").write_text(text + "\n", encoding="utf-8")
    (out_dir / f"{manifest.run_id}-report.md").write_text(markdown + "\n", encoding="utf-8")
    io.dump_json(out_dir / f"{manifest.run_id}-report.json", as_json)
    print(text)
    return 0


def cmd_plan(repo_root: pathlib.Path, args: argparse.Namespace) -> int:
    """REPAIR S-10/CV-12: print the dispatch plan. Dispatches nothing.

    This is the path that decides `Manifest.planned_n` and, for every planned
    attempt on a holdout card, WHICH paraphrase that attempt runs -- chosen
    from the run seed, so the assignment is reproducible from the manifest
    alone and does not depend on process-local randomness.
    """
    try:
        plan = dispatch_plan(repo_root, seed=args.seed, repeats=args.repeats)
    except ContractError as exc:
        print(f"agentic FAIL registry: dispatch plan: {exc}", file=sys.stderr)
        return 1
    counts = planned_n_of(plan)
    with_paraphrase = sum(1 for row in plan if row.paraphrase_index is not None)
    if args.json:
        print(json.dumps({
            "seed": args.seed,
            "repeats_per_cell_arm": args.repeats,
            "planned_n": counts,
            "planned_attempts": [row.to_dict() for row in plan],
        }, indent=2, sort_keys=True))
        return 0
    print(
        f"agentic plan: {len(plan)} planned attempts = {len(counts)} cells "
        f"x {len(ARM_KEYS)} arms x {args.repeats} repeats (seed={args.seed}); "
        f"{with_paraphrase} carry a seed-selected holdout paraphrase"
    )
    for row in plan[:10]:
        print(f"  {row.cell_id} {row.arm_role} repeat={row.repeat} {paraphrase_note(row)}")
    if len(plan) > 10:
        print(f"  ... {len(plan) - 10} more (use --json for the full plan)")
    return 0


def cmd_driver(repo_root: pathlib.Path, args: argparse.Namespace) -> int:
    if args.dry_run:
        try:
            print(adapters.dry_run(args.name))
        except ContractError as exc:
            # REPAIR N-11: a driver whose flags do not conform to the
            # INSTALLED binary's own help is refused here rather than having
            # a plausible, unvalidated argv printed for a reader to copy.
            print(f"agentic FAIL adapter: driver --dry-run refused: {exc}", file=sys.stderr)
            return 1
        return 0
    if args.spawn:
        config = adapters.load_driver_config(args.name)
        driver = adapters.CliDriver(config)
        try:
            driver.spawn(approval_token=args.approval_token)
        except ApprovalRequired as exc:
            print(f"driver spawn refused: {exc}")
            return 1
        return 0  # pragma: no cover -- spawn() never returns today (§10.6)
    print("driver: pass --dry-run or --spawn", file=sys.stderr)
    return 2


# ---------------------------------------------------------------------------
# argparse wiring
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="evals/agentic/run.py",
        description="Agentic test framework CLI (contract §9.2). No flag here ever spawns a model.",
    )
    parser.add_argument("--offline", action="store_true", help="full offline suite + catalog + manifest (default)")
    parser.add_argument("--gate", action="store_true", help="root-portable subset, terse, no manifest write")
    parser.add_argument("--catalog", action="store_true", help="the §7.4 fail-closed catalog walk")
    parser.add_argument("--id", metavar="TID", help="run one catalog entry, e.g. --id T07")
    parser.add_argument("--lane", metavar="LANE", help="run one lane's catalog entries")

    sub = parser.add_subparsers(dest="subcommand")

    p_driver = sub.add_parser("driver", help="native adapter driver (contract §10)")
    p_driver.add_argument("--dry-run", action="store_true")
    p_driver.add_argument("--spawn", action="store_true")
    p_driver.add_argument("--name", required=True, choices=["claude", "codex"])
    p_driver.add_argument("--approval-token", default=None)

    p_coverage = sub.add_parser("coverage", help="registry coverage document (contract §8.4)")
    p_coverage.add_argument("--json", action="store_true")

    p_report = sub.add_parser(
        "report", help="build + render a Report from a manifest + attempt records (REPAIR S-12)"
    )
    p_report.add_argument("--manifest", required=True, metavar="PATH")
    p_report.add_argument("--attempts-dir", required=True, metavar="DIR")
    p_report.add_argument("--out-dir", default=None, metavar="DIR")
    p_report.add_argument(
        "--event-ledger", default=None, metavar="PATH",
        help="REPAIR S-10: a host event ledger (JSONL). Its SPAWN entries are "
             "reconciled against the attempt records; a spawned attempt that was "
             "never recorded fails the report.",
    )

    p_plan = sub.add_parser(
        "plan",
        help="the dispatch plan: cells x arms x repeats, with the per-attempt "
             "holdout paraphrase selected from the run seed (REPAIR S-10/CV-12)",
    )
    p_plan.add_argument("--seed", type=int, default=HOLDOUT_SEED, metavar="N")
    p_plan.add_argument("--repeats", type=int, default=REPEATS_PER_CELL_ARM, metavar="N")
    p_plan.add_argument("--json", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.subcommand == "driver":
        return cmd_driver(REPO_ROOT, args)
    if args.subcommand == "coverage":
        return cmd_coverage(REPO_ROOT, args.json)
    if args.subcommand == "report":
        return cmd_report(REPO_ROOT, args)
    if args.subcommand == "plan":
        return cmd_plan(REPO_ROOT, args)

    flags_set = sum(bool(x) for x in (args.gate, args.catalog, args.id, args.lane))
    if flags_set > 1:
        print("run.py: pass at most one of --gate / --catalog / --id / --lane", file=sys.stderr)
        return 2

    if args.gate:
        return cmd_gate(REPO_ROOT)
    if args.catalog:
        return cmd_catalog(REPO_ROOT)
    if args.id:
        return cmd_id(REPO_ROOT, args.id)
    if args.lane:
        return cmd_lane(REPO_ROOT, args.lane)
    # (no flag) / --offline are identical (contract §9.2)
    return cmd_offline(REPO_ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
