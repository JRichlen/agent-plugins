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

No flag anywhere enables a model call. ``driver --spawn`` always raises
ApprovalRequired (contract §10.6) — it is not on the --gate or --offline path.
"""
from __future__ import annotations

import argparse
import json
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
from evals.agentic.framework.contract import (  # noqa: E402
    ALL_IDS,
    ApprovalGate,
    ApprovalRequired,
    CatalogUnresolvable,
    ContractError,
    Estimand,
    ExposureParityViolation,
    ForgedProvenance,
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
    import importlib.util

    from evals.agentic.framework import analysis

    fixtures_dir = repo_root / "evals" / "agentic" / "fixtures" / "measurement"
    spec = importlib.util.spec_from_file_location("agentic_gate_builders", fixtures_dir / "builders.py")
    builders = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builders)
    doc = io.load_json(fixtures_dir / "zero_denom" / "voice-neg-02.json")
    trials = builders.attempts_for_card(doc["card_id"], doc["all_fault_trials"])
    rate = analysis.card_rate(trials)
    rendered = rate.render()
    if rate.value is not None or "unavailable" not in rendered or rendered.strip().endswith("%"):
        return "agentic FAIL measurement: zero denominator rendered as a number"
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
    arm_path = repo_root / "evals" / "agentic" / "manifests" / "arms" / "graveyard.json"
    if not arm_path.is_file():
        return None
    doc = io.load_json(arm_path)
    full = pairing.Arm.from_dict(doc["full_package_arm"])
    base = pairing.Arm.from_dict(doc["baseline_arm"])
    try:
        pairing.assert_exposure_parity(full, base)
    except ExposureParityViolation:
        return "agentic FAIL registry: exposure parity"
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

    manifest = Manifest(
        run_id=f"run-{now_rfc3339().replace(':', '').replace('.', '').replace('-', '')}",
        created_at=now_rfc3339(),
        git_commit=_git(repo_root, "rev-parse", "HEAD") or "0" * 40,
        branch=_git(repo_root, "rev-parse", "--abbrev-ref", "HEAD") or "unknown",
        offline=True,
        toolchain=_detect_toolchain(),
        lanes=lanes,
        estimands=tuple(Estimand),
        noninferiority_margin=0.05,
        min_valid=3,
        min_clusters=8,
        planned_n={},
        holdout_seed=1,
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

def cmd_driver(repo_root: pathlib.Path, args: argparse.Namespace) -> int:
    if args.dry_run:
        print(adapters.dry_run(args.name))
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

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.subcommand == "driver":
        return cmd_driver(REPO_ROOT, args)
    if args.subcommand == "coverage":
        return cmd_coverage(REPO_ROOT, args.json)

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
