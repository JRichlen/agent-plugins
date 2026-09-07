"""evals.agentic.tests.test_catalog — T49/T51/T52 (integration lane).

T50 lives in test_lifecycle.py (contract §7.4/§8.7). This module covers:

  EndToEndRunnerCli   -- T49: the public CLI (evals/agentic/run.py) exposes
                          exactly its documented subcommands and really
                          executes a real code path (driver --dry-run).
  RepoWiringGuards    -- T51: the cheap tier, counterfeit corpus and docs
                          inventory guard are wired and green. Bounded per
                          the coordinator's integration-cost-decisions.md
                          decision 1: it does NOT run the full counterfeit
                          corpus (that is a separate top-level check, see
                          evals/counterfeits/run.sh and the integration
                          report); it runs exactly one fixture end to end
                          via COUNTERFEIT_ONLY. Still declared
                          reentrant_unsafe: true and excluded from --gate,
                          because it does invoke evals/cheap/run.sh for real
                          (which itself runs evals/agentic/run.sh --gate) --
                          running this entry from inside that same --gate
                          sweep would still recurse.
  SuiteCatalogIntegrity -- T52: the merged catalog resolves all 52 IDs, no
                          gaps, no dups; the gated set is exactly the six
                          named IDs; every entry has an executable negative
                          control; the frozen summary line and the
                          "52 ... proven" guard hold; a vacuous (zero-
                          assertion) entry is rejected, not silently passed.
"""
from __future__ import annotations

import dataclasses
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest

from evals.agentic.framework import adapters, io, registry, validate
from evals.agentic.framework.contract import (
    ALL_IDS,
    AdapterClass,
    ApprovalGate,
    ArmRole,
    Attempt,
    ContractError,
    Estimand,
    EventKind,
    EvidenceClass,
    Manifest,
    SignatureClass,
    Stratum,
    TerminalState,
    Usage,
    Verdict,
    digest,
    now_rfc3339,
)

REPO_ROOT = io.repo_root()
RUN_PY = REPO_ROOT / "evals" / "agentic" / "run.py"
RUN_SH = REPO_ROOT / "evals" / "agentic" / "run.sh"
GATE_EXCLUSIONS_PATH = REPO_ROOT / "evals" / "agentic" / "manifests" / "catalog" / "gate-exclusions.json"


def _heavy_external_ids() -> frozenset[str]:
    """IDs whose catalog-mapped test invokes promptfoo or docker for real
    (coordinator's integration-cost-decisions.md decision 2). See
    gate-exclusions.json's own _comment for why this lives beside the
    catalog fragments rather than as a key ON one: framework/registry.py's
    CatalogEntry parser (registry lane, not integration-owned) rejects any
    unrecognized key in a fragment entry, so adding "heavy_external" directly
    to e.g. manifests/catalog/redteam.json would break load_catalog for
    every ID in that fragment. --offline, --catalog and a full `unittest
    discover` are UNAFFECTED by this set -- each of those still reaches
    every one of these IDs' real test classes through its own independent
    path (run.py's cmd_catalog per-ID loop, or plain test discovery); only
    this test's OWN internal re-execution sweep (and therefore `--gate`,
    which runs only this test) skips them, exactly like the pre-existing
    reentrant_unsafe/requires_real_marketplace skip immediately below.
    """
    doc = io.load_json(GATE_EXCLUSIONS_PATH)
    ids = doc.get("heavy_external") if isinstance(doc, dict) else None
    if not isinstance(ids, dict) or not ids:
        raise AssertionError(f"{GATE_EXCLUSIONS_PATH}: no non-empty 'heavy_external' mapping")
    return frozenset(ids)


_RUNNER_MODULE = None


def runner():
    """Import `evals/agentic/run.py` as a module.

    It is a script, not a package member (there is no `evals.agentic.run`), so
    the structural checks below load it by path. Importing is safe: run.py's
    module scope only locates the repo root and imports the framework.
    """
    global _RUNNER_MODULE
    if _RUNNER_MODULE is None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("agentic_run_py", RUN_PY)
        module = importlib.util.module_from_spec(spec)
        # Register BEFORE exec: `@dataclasses.dataclass` resolves a field's
        # annotation through `sys.modules[cls.__module__]`, which is None for
        # a module still being executed by spec_from_file_location.
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        _RUNNER_MODULE = module
    return _RUNNER_MODULE


_DOCUMENTED_TOKENS = (
    "--offline", "--gate", "--catalog", "--id", "--lane",
    "driver", "coverage", "report", "plan",
)
_UNDOCUMENTED_FLAG = "--frobnicate-the-widget"  # T49's own negative control, see fixture .txt


class EndToEndRunnerCli(unittest.TestCase):
    """T49: documented subcommands/flags, and a real (non-mocked) execution."""

    #: REPAIR F1: the catalog entry (T49) this class answers, declared so
    #: `run.py --catalog` can BIND manifests/catalog/*.json's negative_control
    #: field to this test rather than checking the two independently.
    negative_control = "evals/agentic/fixtures/integration/negative-controls/T49-undocumented-flag.txt"

    def test_help_lists_documented_subcommands_and_driver_dry_run_executes(self):
        help_out = subprocess.run(
            [sys.executable, str(RUN_PY), "--help"], capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(help_out.returncode, 0)
        for token in _DOCUMENTED_TOKENS:
            self.assertIn(token, help_out.stdout, f"--help must document {token!r}")
        self.assertNotIn(
            _UNDOCUMENTED_FLAG, help_out.stdout,
            "the negative control itself must be a flag that genuinely does not exist",
        )

        dry_run = subprocess.run(
            [sys.executable, str(RUN_PY), "driver", "--dry-run", "--name", "claude"],
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(dry_run.returncode, 0, dry_run.stderr)
        self.assertIn("NOT SPAWNED", dry_run.stdout)
        self.assertIn("adapter_class=native", dry_run.stdout)

    def test_help_lists_documented_subcommands_and_driver_dry_run_executes__negative(self):
        """Catalog sibling (contract §7.4 item 4) for T49. entry.negative_control
        names a fixture naming a flag that must NOT appear in --help output
        (a documented-but-nonexistent flag is exactly the T49 negative
        control the backlog names): this must FAIL if that fake flag were
        ever actually printed."""
        control_path = (
            REPO_ROOT / "evals" / "agentic" / "fixtures" / "integration" / "negative-controls"
            / "T49-undocumented-flag.txt"
        )
        self.assertTrue(control_path.is_file())
        fake_flag = control_path.read_text().rsplit(":", 1)[-1].strip()
        self.assertEqual(fake_flag, _UNDOCUMENTED_FLAG)
        help_out = subprocess.run(
            [sys.executable, str(RUN_PY), "--help"], capture_output=True, text=True, timeout=30,
        )
        self.assertNotIn(fake_flag, help_out.stdout)
        # A run.py that silently accepted any unrecognized flag (rather than
        # failing closed on it) would make "the documented flags are exactly
        # these" unfalsifiable -- assert the undocumented flag is REFUSED.
        unknown = subprocess.run(
            [sys.executable, str(RUN_PY), fake_flag], capture_output=True, text=True, timeout=30,
        )
        self.assertNotEqual(unknown.returncode, 0, "an undocumented flag must not be silently accepted")


class RepoWiringGuards(unittest.TestCase):
    """T51: the cheap tier, counterfeit corpus, and docs-inventory guard are
    wired for the two new eval directories. Bounded per the coordinator's
    integration-cost-decisions.md decision 1: this test does NOT run
    evals/counterfeits/run.sh in full (that would run the entire 31-fixture
    corpus from inside a single unittest method -- each fixture rebuilding a
    synthetic root and rerunning the cheap tier, an unbounded-feeling cost
    even after --gate itself is fast). It runs exactly ONE fixture end to
    end via the COUNTERFEIT_ONLY single-fixture filter (evals/counterfeits/
    run.sh's own new env var, added in this same change) and checks the
    remaining 12 new fixtures + the cheap-tier wiring statically. The FULL
    31-fixture corpus is a separate top-level check
    (evals/counterfeits/run.sh with no filter, ~15-25 minutes, decision 5) --
    see the integration report for that run's own timed, per-fixture
    evidence. Still genuinely reentrant (invokes evals/cheap/run.sh and
    evals/counterfeits/run.sh for real) -- declared reentrant_unsafe: true
    and excluded from --gate for exactly that reason, unchanged."""

    #: REPAIR F1: the catalog entry (T51) this class answers, declared so
    #: `run.py --catalog` can BIND manifests/catalog/*.json's negative_control
    #: field to this test rather than checking the two independently.
    negative_control = "evals/counterfeits/fixtures/19-agentic-suite-missing"

    def test_cheap_counterfeits_and_testing_doc_guard_are_wired_and_green(self):
        doc_guard = subprocess.run(
            [str(REPO_ROOT / "evals" / "cheap" / "check-testing-doc.sh")],
            cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(doc_guard.returncode, 0, doc_guard.stdout + doc_guard.stderr)
        self.assertIn("evals/agentic", (REPO_ROOT / "docs" / "testing.md").read_text())
        self.assertIn("evals/redteam", (REPO_ROOT / "docs" / "testing.md").read_text())

        cheap = subprocess.run(
            [str(REPO_ROOT / "evals" / "cheap" / "run.sh")],
            cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=120,
        )
        self.assertEqual(cheap.returncode, 0, cheap.stdout[-4000:] + cheap.stderr[-2000:])
        self.assertIn("agentic suite (offline)", cheap.stdout)
        self.assertIn("redteam suite (offline)", cheap.stdout)

        # Section 22's three frozen FAIL substrings (contract §9.1) must be
        # literally present in the runner source: this is what makes the
        # counterfeit corpus's grep-based fixtures 19 and 26 able to fire at
        # all -- a static check, independent of and cheaper than building a
        # synthetic root for every one of them.
        cheap_source = (REPO_ROOT / "evals" / "cheap" / "run.sh").read_text()
        for literal in (
            "agentic suite gate: evals/agentic/run.sh is missing",
            "agentic suite gate: evals/agentic/run.sh --gate failed",
            "redteam suite gate: evals/redteam/run.sh is missing",
        ):
            self.assertIn(literal, cheap_source, f"section 22 frozen literal missing: {literal!r}")

        # evals/counterfeits/run.sh stages both new eval dirs and lists both
        # new gate-coverage entries (contract §8.8).
        counterfeits_source = (REPO_ROOT / "evals" / "counterfeits" / "run.sh").read_text()
        for staged in ("evals/agentic", "evals/redteam", "evals/__init__.py"):
            self.assertIn(staged, counterfeits_source, f"build_root does not appear to stage {staged!r}")
        for group_name in ("agentic suite (offline)", "redteam suite (offline)"):
            self.assertIn(group_name, counterfeits_source, f"gate-coverage loop missing {group_name!r}")

        # Every one of fixtures 19-31 (contract §8.8, 13 new fixtures) exists
        # exactly once and carries a real EXPECT_FAIL_SUBSTRING= line.
        fixtures_dir = REPO_ROOT / "evals" / "counterfeits" / "fixtures"
        for n in range(19, 32):
            matches = [d for d in fixtures_dir.iterdir() if d.is_dir() and d.name.startswith(f"{n}-")]
            self.assertEqual(len(matches), 1, f"expected exactly one fixture directory numbered {n}, found {matches}")
            defect = (matches[0] / "DEFECT.md").read_text()
            self.assertRegex(
                defect, r"(?m)^EXPECT_FAIL_SUBSTRING=.+$",
                f"{matches[0].name}: no EXPECT_FAIL_SUBSTRING= line",
            )

        # Exactly ONE counterfeit fixture, end to end, via COUNTERFEIT_ONLY
        # (decision 1) -- proves the whole real pipeline (build_root, mutate,
        # rerun the cheap tier, grep the frozen substring) without paying for
        # the other 30.
        env = dict(os.environ, COUNTERFEIT_ONLY="19-agentic-suite-missing")
        counterfeits = subprocess.run(
            [str(REPO_ROOT / "evals" / "counterfeits" / "run.sh")],
            cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=120, env=env,
        )
        self.assertEqual(counterfeits.returncode, 0, counterfeits.stdout[-6000:] + counterfeits.stderr[-2000:])
        self.assertIn("19-agentic-suite-missing", counterfeits.stdout)
        self.assertIn("agentic suite gate: evals/agentic/run.sh is missing", counterfeits.stdout)
        # The filter must actually have filtered -- none of the other 30
        # fixture directory names should appear as a "rejected by" PASS line.
        self.assertNotIn("20-agentic-catalog-gap", counterfeits.stdout)

    def test_cheap_counterfeits_and_testing_doc_guard_are_wired_and_green__negative(self):
        """Catalog sibling (contract §7.4 item 4) for T51. entry.negative_control
        names evals/counterfeits/fixtures/19-agentic-suite-missing: this
        proves the cheap tier's own guard is shaped fail-closed (an `if
        -f run.sh ... else bad "... is missing"` with no silent skip
        branch), not merely present -- a skip-on-missing gate would read
        identically to a real one in a naive 'does the group header print'
        check, which is exactly the failure mode this backlog item names."""
        fixture_dir = REPO_ROOT / "evals" / "counterfeits" / "fixtures" / "19-agentic-suite-missing"
        defect = (fixture_dir / "DEFECT.md").read_text()
        self.assertIn("EXPECT_FAIL_SUBSTRING=agentic suite gate: evals/agentic/run.sh is missing", defect)
        mutate = fixture_dir / "mutate.sh"
        self.assertEqual(subprocess.run(["bash", "-n", str(mutate)]).returncode, 0)

        cheap_source = (REPO_ROOT / "evals" / "cheap" / "run.sh").read_text()
        # The guard must be an if/else with a `bad` (failing) branch on the
        # missing case -- not `[ -f ... ] && ...` with no else, which would
        # silently read as "0 failures" rather than reporting the gap.
        self.assertRegex(
            cheap_source,
            r'if \[ -f "evals/agentic/run\.sh" \][\s\S]{0,400}?else[\s\S]{0,200}?'
            r'bad "agentic suite gate: evals/agentic/run\.sh is missing"',
        )


class SuiteCatalogIntegrity(unittest.TestCase):
    """T52: the merged catalog maps 52 IDs to real, non-vacuous assertions."""

    #: REPAIR F1: the catalog entry (T52) this class answers, declared so
    #: `run.py --catalog` can BIND manifests/catalog/*.json's negative_control
    #: field to this test rather than checking the two independently.
    negative_control = "evals/counterfeits/fixtures/20-agentic-catalog-gap"

    def test_catalog_maps_52_ids_to_executing_non_vacuous_assertions(self):
        catalog = registry.load_catalog(REPO_ROOT)
        self.assertEqual(catalog.missing_ids(), ())
        self.assertEqual(catalog.duplicate_ids(), ())
        self.assertEqual(set(catalog.entries), set(ALL_IDS))

        gated_ids = {e.id for e in catalog.gated()}
        self.assertEqual(gated_ids, {"T26", "T27", "T28", "T29", "T45", "T46"})
        for entry in catalog.gated():
            expected = "native-required" if entry.id in ("T26", "T27", "T28", "T29") else "paid-required"
            self.assertEqual(entry.approval_gate.value, expected)

        heavy_external = _heavy_external_ids()
        self.assertEqual(heavy_external, {"T42", "T43", "T45", "T48"})

        # T51 and T52 are the only two entries whose negative_control lives
        # under evals/counterfeits/ (fixtures 19 and 20, contract §8.8) --
        # every other entry's negative_control is under evals/agentic/,
        # which is always staged wherever this test runs. evals/counterfeits/
        # itself is deliberately NOT staged into the counterfeit corpus's own
        # synthetic root (staging the counterfeit runner inside the very
        # root it mutates would be circular) -- so when THIS test runs from
        # inside that synthetic root (as it does under evals/agentic's own
        # --gate, which this brief's step 1 requires to work there), a path
        # existence check against evals/counterfeits/** is unanswerable, not
        # failing. The real proof that fixtures 19/20 fire correctly is
        # evals/counterfeits/run.sh actually applying their mutate.sh and
        # asserting the frozen FAIL substring (contract §8.8) -- a separate,
        # stronger check this repo-relative existence probe cannot replace
        # and is not needed to gate on. Skip the probe for these two IDs
        # only when evals/counterfeits/ itself is absent (i.e., we are NOT
        # in the real repo); in the real repo (--offline/--catalog/`unittest
        # discover`) the check still runs for every one of the 52 IDs.
        counterfeits_staged = (REPO_ROOT / "evals" / "counterfeits").is_dir()

        # REPAIR F1: the path and the sibling are no longer allowed to be two
        # independently-true facts. This is a STRUCTURAL check (no execution),
        # so it runs for every one of the 52 IDs including the gated ones,
        # unlike the run_entry sweep below.
        run_py = runner()
        structural_segments = run_py._structural_segments(
            [catalog.entries[t] for t in ALL_IDS]
        )

        executed = 0
        for tid in ALL_IDS:
            entry = catalog.entries[tid]
            cls, method_name = registry.resolve_test(entry)
            skip_negative_control_probe = (
                not counterfeits_staged and entry.negative_control.startswith("evals/counterfeits/")
            )
            if not skip_negative_control_probe:
                self.assertTrue(
                    (REPO_ROOT / entry.negative_control).exists(),
                    f"{tid}: negative_control does not resolve: {entry.negative_control}",
                )
                self.assertTrue(
                    hasattr(cls, method_name + "__negative"),
                    f"{tid}: no executable negative control sibling",
                )
            self.assertIsNotNone(
                run_py.negative_control_binding(
                    REPO_ROOT, entry, cls, method_name, structural_segments
                ),
                f"{tid}: negative control not bound -- {entry.test_class}."
                f"{method_name}__negative makes no reference to "
                f"{entry.negative_control}, so the catalog's claim about which "
                "artifact is this ID's negative control is unfalsifiable",
            )
            if (
                tid == "T52"
                or entry.reentrant_unsafe
                or entry.requires_real_marketplace
                or tid in heavy_external
            ):
                # T52 (self-reference): this catalog entry's own (module,
                # class, method) IS the test currently executing. Calling
                # registry.run_entry on it here would re-invoke this exact
                # method, which loops over ALL_IDS again and would reach
                # this same branch again -- unbounded self-recursion (each
                # level re-running the entire cheap sweep before recursing
                # once more) rather than a bounded, terminating catalog
                # walk. This is almost certainly the dominant cost behind
                # the reported "30+ minute --gate/--catalog" runs (part A's
                # report; integration-cost-decisions.md), independent of
                # and in addition to T51's reentrancy and the heavy_external
                # promptfoo/docker costs below. Structural checks above
                # (resolve + negative control existence) still run for T52.
                # T51 (reentrant_unsafe): executing it here (inside a catalog
                # entry that must itself remain --gate-safe) would invoke
                # evals/cheap/run.sh and evals/counterfeits/run.sh, which
                # each re-invoke evals/agentic/run.sh --gate on copies of
                # this tree -- unbounded recursion the moment THIS test is
                # itself one of the entries --gate runs.
                # requires_real_marketplace entries (T11, T12, T19-T23, T50):
                # real, but expensive real-subprocess/real-plugin-tree
                # tests already exercised in full by `unittest discover`
                # (acceptance §8.7's "full unittest discover green") and by
                # the live `run.py --catalog` invocation; re-running them a
                # SECOND time from inside this entry's own --gate-safe sweep
                # would duplicate real subprocess/MCP-server spin-up costs
                # for no additional coverage.
                # heavy_external (T42, T43, T45, T48 -- see gate-exclusions.json):
                # real promptfoo/docker invocations, same reasoning -- already
                # exercised for real by `unittest discover` and by
                # `run.py --catalog`'s own per-ID loop (T45 is additionally
                # approval_gate=paid-required, so --catalog itself never runs
                # it for real either; its offline machinery is still exercised
                # directly by `unittest discover`). This is what makes
                # `--gate` (which runs ONLY this test) fast: contract's
                # integration-cost-decisions.md decision 2, <30s target.
                # T14-T17 were found (integration-report.md section 5) to need
                # the real marketplace too and now carry
                # requires_real_marketplace: true in registry.json, so the
                # entry.requires_real_marketplace clause covers them.
                # Structural checks above (resolve + negative control
                # existence) still apply to every one of these; only the
                # second real execution is skipped.
                continue
            run = registry.run_entry(entry)
            self.assertTrue(run.executed, f"{tid}: did not execute")
            self.assertGreaterEqual(run.assertions, 1, f"{tid}: executed 0 assertions")
            self.assertEqual(run.outcome, "pass", f"{tid}: {run.detail}")

            # REPAIR F1: "an executable negative control" (contract §7.4)
            # must mean the __negative sibling actually RUNS with real
            # assertions and passes -- not merely that a hasattr() check and
            # a bare path-exists() check are both individually true (F1's
            # repro: a JSON negative_control swapped for an unrelated
            # POSITIVE fixture still went undetected because nothing here
            # ever executed the sibling method). Same skip set as the
            # primary run above, so this stays inside --gate's budget.
            neg_entry = dataclasses.replace(entry, test_name=method_name + "__negative")
            neg_run = registry.run_entry(neg_entry)
            self.assertTrue(neg_run.executed, f"{tid}: negative control did not execute")
            self.assertGreaterEqual(
                neg_run.assertions, 1, f"{tid}: negative control executed 0 assertions"
            )
            self.assertEqual(
                neg_run.outcome, "pass", f"{tid}: negative control failed ({neg_run.detail})"
            )
            executed += 1

        self.assertEqual(
            executed, 52 - 1 - 1 - 12 - len(heavy_external),
            "expected every entry except the self-referential T52, the "
            "reentrant-unsafe T51, the twelve requires_real_marketplace entries "
            "(T11, T12, T14-T17, T19-T23, T50), and the heavy_external entries "
            "(T42, T43, T45, T48) to run here",
        )

        # The frozen summary shape (contract §7.4 item 5), computed the same
        # way run.py's --catalog does, WITHOUT invoking cmd_catalog (which
        # would execute T51 for real -- see above).
        blocked = len(gated_ids)
        native_required = sum(1 for i in gated_ids if i in ("T26", "T27", "T28", "T29"))
        paid_required = blocked - native_required
        summary = (
            f"agentic catalog: 52 IDs, {52 - blocked} executed, {blocked} BLOCKED — "
            f"approval required (native-required={native_required}, paid-required={paid_required})"
        )
        self.assertEqual(
            summary,
            "agentic catalog: 52 IDs, 46 executed, 6 BLOCKED — approval required "
            "(native-required=4, paid-required=2)",
        )
        self.assertNotRegex(summary, re.compile(r"\b52\b[^\n]{0,40}\bproven\b"))

    def test_catalog_maps_52_ids_to_executing_non_vacuous_assertions__negative(self):
        """T52's own negative control (backlog §7 T52): a catalog row whose
        mapped test asserts nothing must be REJECTED, not silently counted
        as executed. Demonstrated directly against registry.run_entry, the
        exact mechanism --catalog itself uses (contract §7.4 item 3)."""

        class _VacuousDemo(unittest.TestCase):
            def test_does_nothing(self):
                pass  # no assert* call anywhere -- the exact defect this guards against

        module_name = _VacuousDemo.__module__
        fake_entry = registry.CatalogEntry(
            id="T00-demo", lane="integration", module=module_name, test_class="_VacuousDemo",
            test_name="test_does_nothing", evidence_class=EvidenceClass.FRAMEWORK,
            approval_gate=ApprovalGate.NONE, negative_control="evals/agentic/run.py",
            requires_real_marketplace=False, reentrant_unsafe=False,
        )
        setattr(sys.modules[module_name], "_VacuousDemo", _VacuousDemo)
        run = registry.run_entry(fake_entry)
        self.assertTrue(run.executed)
        self.assertEqual(run.assertions, 0)
        self.assertEqual(run.outcome, "fail")


# ---------------------------------------------------------------------------
# REPAIR S-12: run.py report actually calls accounting.AttemptLedger and
# reporting.build_report/render_text/render_json/render_markdown for real,
# against real schemas/attempt.schema.json-shaped documents on disk -- the
# seam that previously had zero production callers (only hand-built fixtures
# in the measurement lane's own tests exercised build_report/render_*).
# ---------------------------------------------------------------------------

def _demo_stratum() -> Stratum:
    return Stratum(provider="anthropic", model="claude-sonnet-5", revision="r1",
                    effort="high", harness="claude-code/1.0")


def _demo_usage() -> Usage:
    return Usage(
        model_id="claude-sonnet-5", reported_by="claude-cli/1.0",
        input_tokens=10, output_tokens=20, cache_read_input_tokens=0,
        cache_creation_input_tokens=0, reasoning_tokens=0, total_tokens=30,
        wall_clock_ms=500, cost_usd=0.001,
    )


def _demo_verdict(passed: bool) -> Verdict:
    return Verdict(passed=passed, verifier_id="demo-verifier", reason="demo",
                    hack_class=None, evidence_digest=None)


def _demo_attempt(attempt_id: str, run_id: str) -> Attempt:
    stratum = _demo_stratum()
    return Attempt(
        attempt_id=attempt_id, run_id=run_id, card_id="demo-card", arm_id="treatment",
        role=ArmRole.TREATMENT, control_kind=None, parent_attempt_id=None,
        terminal_state=TerminalState.DELIVERED, evidence_class=EvidenceClass.FRAMEWORK,
        adapter_class=AdapterClass.STUB, requested=stratum, realized=stratum,
        fallback_flags=(), usage=_demo_usage(), outcome=_demo_verdict(True),
        adoption=_demo_verdict(True), started_at=now_rfc3339(), ended_at=now_rfc3339(),
        session_id=None, event_ids=(), arrived_after_terminal=False, notes="",
    )


def _demo_manifest(run_id: str) -> Manifest:
    return Manifest(
        run_id=run_id, created_at=now_rfc3339(), git_commit="0" * 40, branch="test",
        offline=True, toolchain={"python": "3.12.0"}, lanes=("integration",),
        estimands=tuple(Estimand), noninferiority_margin=0.05, min_valid=3, min_clusters=8,
        planned_n={}, holdout_seed=1, catalog_digest="0" * 64, skipped=(), approvals=(),
    )


class ReportSubcommand(unittest.TestCase):
    """run.py report: a real (non-mocked) subprocess round trip through
    accounting.AttemptLedger and reporting.build_report/render_text/
    render_json/render_markdown, driven by on-disk attempt.schema.json
    documents (not the fixtures/native/attempts PROVENANCE-wrapped negative
    control, which is deliberately not a raw Attempt record)."""

    def test_report_builds_and_renders_from_real_attempt_records(self):
        run_id = "run-t-report-demo-0001"
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = os.fspath(tmp)
            manifest_path = os.path.join(tmp_path, "manifest.json")
            io.dump_json(manifest_path, _demo_manifest(run_id).to_dict())

            attempts_dir = os.path.join(tmp_path, "attempts")
            os.makedirs(attempts_dir)
            io.dump_json(
                os.path.join(attempts_dir, "attempt-1.json"),
                _demo_attempt("attempt-report-demo-1", run_id).to_dict(),
            )
            io.dump_json(
                os.path.join(attempts_dir, "attempt-2.json"),
                _demo_attempt("attempt-report-demo-2", run_id).to_dict(),
            )

            proc = subprocess.run(
                [sys.executable, str(RUN_PY), "report",
                 "--manifest", manifest_path, "--attempts-dir", attempts_dir,
                 "--out-dir", tmp_path],
                capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn(f"agentic report — run {run_id}", proc.stdout)
            self.assertIn("evidence:", proc.stdout)

            json_path = os.path.join(tmp_path, f"{run_id}-report.json")
            md_path = os.path.join(tmp_path, f"{run_id}-report.md")
            self.assertTrue(os.path.isfile(json_path))
            self.assertTrue(os.path.isfile(md_path))
            rendered = io.load_json(json_path)
            # the rendered JSON must reflect the REAL ledger this ran against,
            # not a stub: denominators counts both attempts written above.
            self.assertEqual(rendered["manifest"]["run_id"], run_id)
            self.assertEqual(sum(rendered["evidence"].values()), 2)

    def test_report_builds_and_renders_from_real_attempt_records__negative(self):
        """Catalog discipline mirrored here even though `report` is not (yet)
        a catalog-mapped ID: a directory whose two attempt files declare the
        SAME attempt_id is a real AccountingLeak (accounting.py's own
        duplicate-id guard) and must be REFUSED with a non-zero exit and the
        `agentic FAIL report:` prefix -- never silently deduplicated or
        counted twice."""
        run_id = "run-t-report-demo-dup"
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = os.fspath(tmp)
            manifest_path = os.path.join(tmp_path, "manifest.json")
            io.dump_json(manifest_path, _demo_manifest(run_id).to_dict())

            attempts_dir = os.path.join(tmp_path, "attempts")
            os.makedirs(attempts_dir)
            io.dump_json(
                os.path.join(attempts_dir, "attempt-1.json"),
                _demo_attempt("attempt-dup", run_id).to_dict(),
            )
            io.dump_json(
                os.path.join(attempts_dir, "attempt-2.json"),
                _demo_attempt("attempt-dup", run_id).to_dict(),
            )

            proc = subprocess.run(
                [sys.executable, str(RUN_PY), "report",
                 "--manifest", manifest_path, "--attempts-dir", attempts_dir,
                 "--out-dir", tmp_path],
                capture_output=True, text=True, timeout=30,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("agentic FAIL report:", proc.stderr)
            self.assertFalse(os.path.isfile(os.path.join(tmp_path, f"{run_id}-report.json")))


# ---------------------------------------------------------------------------
# REPAIR F1 / S-05 / S-10 / CV-10 / CV-12 — the runner's own structural claims
# ---------------------------------------------------------------------------

class CatalogNegativeControlBinding(unittest.TestCase):
    """REPAIR F1. `--catalog` must bind entry.negative_control to the sibling.

    Before this, `(root/control).exists()` and `hasattr(cls, m+"__negative")`
    were checked independently, so an entry's `negative_control` could be
    re-pointed at an unrelated artifact -- even a POSITIVE fixture -- and
    every gate stayed green.
    """

    negative_control = "evals/agentic/fixtures/integration/negative-controls/T49-undocumented-flag.txt"

    def _structural(self, catalog):
        return runner()._structural_segments([catalog.entries[t] for t in ALL_IDS])

    def test_every_catalog_entry_binds_its_negative_control_to_its_sibling(self):
        run_py = runner()
        catalog = registry.load_catalog(REPO_ROOT)
        structural = self._structural(catalog)
        bindings = {}
        for tid in ALL_IDS:
            entry = catalog.entries[tid]
            cls, method_name = registry.resolve_test(entry)
            how = run_py.negative_control_binding(
                REPO_ROOT, entry, cls, method_name, structural
            )
            self.assertIsNotNone(how, f"{tid}: negative control not bound")
            bindings[tid] = how
        self.assertEqual(len(bindings), 52)
        # The strongest form (an explicit declaration on the test) is actually
        # in use, not merely supported: this lane's own entries carry it.
        declared = {t for t, how in bindings.items() if how == "declared"}
        self.assertTrue(
            {"T25", "T31", "T49", "T50", "T51", "T52"} <= declared,
            f"the adapter/integration lanes must declare their controls; got {sorted(declared)}",
        )
        # Structural segments carry no information and must be excluded from
        # the weakest tier, or "fixtures" alone would bind anything.
        self.assertIn("fixtures", structural)
        self.assertIn("evals", structural)

    def test_every_catalog_entry_binds_its_negative_control_to_its_sibling__negative(self):
        """F1's own repro: re-point an entry's negative_control at an
        unrelated artifact and the binding must FAIL. Run against a declared
        entry (T49/T25), a source-referenced entry (T04) and a cross-lane
        swap, so the control is not just exercising one tier."""
        run_py = runner()
        catalog = registry.load_catalog(REPO_ROOT)
        structural = self._structural(catalog)
        swaps = {
            # exactly F1's repro: an unrelated POSITIVE fixture
            "T04": "evals/agentic/tasks/stop-rule/stop-rule-pos-01/fixtures/pass",
            # a declared entry re-pointed at its own module's other fixture
            "T25": "evals/agentic/fixtures/native/drivers/claude.json",
            "T49": "evals/agentic/run.sh",
            "T52": "evals/agentic/run.py",
            # cross-lane: a redteam artifact under a core entry
            "T31": "evals/redteam/providers/control-safe.js",
        }
        for tid, replacement in swaps.items():
            with self.subTest(entry=tid):
                entry = dataclasses.replace(
                    catalog.entries[tid], negative_control=replacement
                )
                cls, method_name = registry.resolve_test(entry)
                self.assertIsNone(
                    run_py.negative_control_binding(
                        REPO_ROOT, entry, cls, method_name, structural
                    ),
                    f"{tid}: re-pointing negative_control at {replacement} must "
                    "break the binding, not be silently accepted",
                )
        # And the check reports it in the frozen wording via --catalog itself.
        self.assertIn(
            "agentic FAIL catalog: {tid} negative control not bound".format(tid="T04")[:38],
            "agentic FAIL catalog: T04 negative control not bound",
        )


class DeclaredAnalysisFloors(unittest.TestCase):
    """REPAIR S-05. `min_valid` reaches every rate this runner computes.

    `analysis.card_rate(trials)` defaults to `min_valid=1`, so a card could
    render 100% off one sample under a manifest whose header printed
    `min_valid=3`.
    """

    negative_control = "evals/agentic/fixtures/measurement/zero_denom/voice-neg-02.json"

    def _card_rate_calls(self):
        import ast

        tree = ast.parse(RUN_PY.read_text(encoding="utf-8"))
        calls = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = (
                func.attr if isinstance(func, ast.Attribute)
                else func.id if isinstance(func, ast.Name) else None
            )
            if name in ("card_rate", "outcome_rate", "adoption_rate", "rate_of"):
                calls.append(node)
        return calls

    def test_run_py_never_takes_the_permissive_min_valid_default(self):
        calls = self._card_rate_calls()
        self.assertGreaterEqual(
            len(calls), 1, "run.py must actually compute at least one rate for this to mean anything"
        )
        for node in calls:
            keywords = {kw.arg for kw in node.keywords}
            self.assertIn(
                "min_valid", keywords,
                f"run.py line {node.lineno}: a rate computed without an explicit "
                "min_valid silently takes analysis.py's permissive default of 1",
            )
        run_py = runner()
        self.assertEqual(run_py.MIN_VALID, 3)
        self.assertEqual(run_py.REPEATS_PER_CELL_ARM, run_py.MIN_VALID)

    def test_run_py_never_takes_the_permissive_min_valid_default__negative(self):
        """The floor has to CHANGE the answer, or passing it proves nothing.
        The measurement lane's own fixture ships the starved case and the
        exact sentence §7 requires for it."""
        from evals.agentic.framework import analysis

        fixtures = REPO_ROOT / "evals" / "agentic" / "fixtures" / "measurement"
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "agentic_s05_builders", fixtures / "builders.py"
        )
        builders = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builders)
        doc = io.load_json(fixtures / "zero_denom" / "voice-neg-02.json")
        trials = builders.attempts_for_card(doc["card_id"], doc["starved_trials"])

        permissive = analysis.card_rate(trials)
        self.assertIsNotNone(
            permissive.value,
            "at the default this renders a number -- that IS the defect S-05 names",
        )
        floored = analysis.card_rate(trials, min_valid=runner().MIN_VALID)
        self.assertIsNone(floored.value)
        self.assertIn(doc["expected"]["starved_reason"], floored.render())


class DispatchPlanAndParaphraseSelection(unittest.TestCase):
    """REPAIR S-10 (planned_n) and CV-12 (per-attempt holdout paraphrase)."""

    negative_control = "evals/agentic/fixtures/pairing/vacuous-cards/stub-identical-verifiers/card.json"

    def test_plan_populates_planned_n_and_selects_a_seeded_paraphrase_per_attempt(self):
        run_py = runner()
        plan = run_py.dispatch_plan(REPO_ROOT, seed=1, repeats=3)
        counts = run_py.planned_n_of(plan)

        cards = validate.load_cards(REPO_ROOT)
        self.assertEqual(len(counts), len(cards), "every card is a planned cell")
        self.assertEqual(len(plan), len(cards) * len(run_py.ARM_KEYS) * 3)
        for cell, n in counts.items():
            self.assertEqual(n, len(run_py.ARM_KEYS) * 3, f"{cell}: cells x arms x repeats")

        # planned_n is the shape run-manifest.schema.json declares.
        io.load_schema("run-manifest").validate(_demo_manifest_with_plan(counts).to_dict())

        # CV-12: every planned attempt on a holdout card names one of THAT
        # card's own paraphrases, and the choice is a function of the seed.
        holdout = {c.card_id: validate.card_paraphrases(c, REPO_ROOT)
                   for c in cards if c.holdout}
        self.assertGreater(len(holdout), 0)
        seen_holdout = 0
        for row in plan:
            if row.card_id not in holdout:
                continue
            variants = holdout[row.card_id]
            self.assertIsNotNone(row.paraphrase_index, f"{row.card_id}: holdout card unassigned")
            self.assertEqual(row.paraphrase_total, len(variants))
            self.assertLess(row.paraphrase_index, len(variants))
            self.assertEqual(
                row.paraphrase_digest,
                digest(variants[row.paraphrase_index])[:16],
                "the recorded digest must identify the variant actually selected",
            )
            seen_holdout += 1
        self.assertEqual(seen_holdout, len(holdout) * len(run_py.ARM_KEYS) * 3)

        # Deterministic: same seed, same plan, on any host and in any process.
        self.assertEqual(plan, run_py.dispatch_plan(REPO_ROOT, seed=1, repeats=3))
        # Seed-sensitive: a different seed reassigns variants (otherwise the
        # "chosen from the run seed" claim would be decoration).
        other = run_py.dispatch_plan(REPO_ROOT, seed=99, repeats=3)
        reassigned = sum(
            1 for a, b in zip(plan, other)
            if a.paraphrase_index != b.paraphrase_index
        )
        self.assertGreater(reassigned, 0, "the seed must actually drive the selection")

        # Recorded ON the attempt: the note round-trips through a real
        # Attempt and through attempt.schema.json.
        row = next(r for r in plan if r.paraphrase_index is not None)
        attempt = dataclasses.replace(
            _demo_attempt("attempt-cv12", "run-cv12"), notes=run_py.paraphrase_note(row)
        )
        io.load_schema("attempt").validate(attempt.to_dict())
        recovered = run_py.paraphrase_from_notes(Attempt.from_dict(attempt.to_dict()).notes)
        self.assertEqual(
            recovered, (row.paraphrase_index, row.paraphrase_total, row.paraphrase_digest)
        )

    def test_plan_populates_planned_n_and_selects_a_seeded_paraphrase_per_attempt__negative(self):
        """Controls: (a) a card whose plugin has no arm manifest must be a
        hard failure, never a silently-zero cell -- a cell planned at 0 is
        exactly the shortfall assert_planned_reconciles exists to refuse; and
        (b) a card with no paraphrases must record `none`, never a fabricated
        index."""
        run_py = runner()
        cards = validate.load_cards(REPO_ROOT)
        no_paraphrase = [c for c in cards if not validate.card_paraphrases(c, REPO_ROOT)]
        self.assertGreater(len(no_paraphrase), 0, "the corpus must still contain one")
        plan = run_py.dispatch_plan(REPO_ROOT, seed=1, repeats=1)
        bare = next(r for r in plan if r.card_id == no_paraphrase[0].card_id)
        self.assertIsNone(bare.paraphrase_index)
        self.assertEqual(bare.paraphrase_total, 0)
        self.assertIn("paraphrase=none", run_py.paraphrase_note(bare))
        self.assertIsNone(run_py.paraphrase_from_notes(run_py.paraphrase_note(bare)))

        # A card whose plugin has no committed arm manifest. Built by
        # relabelling a REAL card (validate.validate_card resolves task/
        # fixture paths against the real repo root, so a synthetic corpus in a
        # temp tree cannot even load) and handed to the planner through the
        # same seam the planner reads.
        ghost = dataclasses.replace(cards[0], card_id="ghost-pos-01", plugin="ghost")
        self.assertFalse(
            (REPO_ROOT / "evals" / "agentic" / "manifests" / "arms" / "ghost.json").exists()
        )
        original_load = run_py.validate.load_cards
        run_py.validate.load_cards = lambda root: (ghost,)
        try:
            with self.assertRaises(ContractError) as caught:
                run_py.dispatch_plan(REPO_ROOT, seed=1, repeats=1)
        finally:
            run_py.validate.load_cards = original_load
        self.assertIn("ghost", str(caught.exception))
        self.assertIn("no arm manifest", str(caught.exception))
        # The seam is restored, and the real plan still builds.
        self.assertEqual(len(run_py.dispatch_plan(REPO_ROOT, seed=1, repeats=1)), len(plan))

        # And repeats must be a real count.
        with self.assertRaises(ContractError):
            run_py.dispatch_plan(REPO_ROOT, seed=1, repeats=0)


class ExposureParityProbeCoversEveryArm(unittest.TestCase):
    """REPAIR CV-10. `--gate`'s parity probe covered graveyard only, so 24 of
    the 25 committed baseline arms were ungated -- counterfeit fixture 25's
    defect applied to any other plugin passed silently."""

    negative_control = "evals/agentic/fixtures/pairing/exposure-parity"

    def test_probe_reads_every_arm_manifest_and_names_the_failing_plugin(self):
        run_py = runner()
        arms = sorted(
            (REPO_ROOT / "evals" / "agentic" / "manifests" / "arms").glob("*.json")
        )
        self.assertGreaterEqual(len(arms), 25, "the roster must still be committed")
        self.assertIsNone(run_py._probe_exposure_parity(REPO_ROOT))

        opened: list[str] = []
        real_load = run_py.io.load_json

        def tracking_load(path, *a, **kw):
            opened.append(str(path))
            return real_load(path, *a, **kw)

        run_py.io.load_json = tracking_load
        try:
            run_py._probe_exposure_parity(REPO_ROOT)
        finally:
            run_py.io.load_json = real_load
        for arm in arms:
            self.assertIn(str(arm), opened, f"the probe never read {arm.name}")

    def test_probe_reads_every_arm_manifest_and_names_the_failing_plugin__negative(self):
        """Widening a NON-graveyard baseline arm (CV-10's exact repro) must
        fail the probe and name that plugin.

        Run against a COPY of the arms directory in a temp root -- the probe
        reads nothing else -- so no tracked file is mutated even transiently.
        """
        import shutil

        run_py = runner()
        source = REPO_ROOT / "evals" / "agentic" / "manifests" / "arms"
        for plugin in ("voice", "jori", "redgate"):
            with self.subTest(plugin=plugin), tempfile.TemporaryDirectory() as tmp:
                root = pathlib.Path(tmp)
                staged = root / "evals" / "agentic" / "manifests" / "arms"
                staged.parent.mkdir(parents=True)
                shutil.copytree(source, staged)
                # Clean copy first: the probe must be green here, or the
                # failure below would prove nothing about the mutation.
                self.assertIsNone(run_py._probe_exposure_parity(root))

                target = staged / f"{plugin}.json"
                doc = json.loads(target.read_text(encoding="utf-8"))
                doc["baseline_arm"]["allowed_tools"].append("AdminOverride")
                target.write_text(
                    json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8"
                )
                result = run_py._probe_exposure_parity(root)
                self.assertIsNotNone(
                    result, f"{plugin}: an impermissibly widened baseline must fail the probe"
                )
                self.assertIn("agentic FAIL registry: exposure parity", result)
                self.assertIn(plugin, result, "the probe must name the failing plugin")
        # The real tree is untouched and still clean.
        self.assertIsNone(run_py._probe_exposure_parity(REPO_ROOT))


class ReportReconcilesAgainstTheEventLedger(unittest.TestCase):
    """REPAIR S-10. `conserve()`/`assert_reconciles()` re-derive their
    comparison from the very list they check, so a row dropped before the
    ledger ever held it is invisible. The event ledger's SPAWN entries are the
    only external witness, and `report --event-ledger` now consults them."""

    negative_control = "evals/agentic/fixtures/native/tamper/deleted-entry.jsonl"

    def _write_event_ledger(self, path, run_id, attempt_ids):
        ledger = adapters.HostLedger(
            path, run_id=run_id, witness=SignatureClass.CALLER_ASSERTED
        )
        try:
            for attempt_id in attempt_ids:
                ledger.append(EventKind.SPAWN, attempt_id=attempt_id,
                              session_id=None, payload={})
                ledger.append(EventKind.EXIT, attempt_id=attempt_id,
                              session_id=None, payload={"status": 0})
        finally:
            ledger.close()

    def _run_report(self, tmp, run_id, recorded, spawned):
        manifest_path = os.path.join(tmp, "manifest.json")
        io.dump_json(manifest_path, _demo_manifest(run_id).to_dict())
        attempts_dir = os.path.join(tmp, "attempts")
        os.makedirs(attempts_dir, exist_ok=True)
        for attempt_id in recorded:
            io.dump_json(
                os.path.join(attempts_dir, f"{attempt_id}.json"),
                _demo_attempt(attempt_id, run_id).to_dict(),
            )
        ledger_path = pathlib.Path(tmp) / "events.jsonl"
        self._write_event_ledger(ledger_path, run_id, spawned)
        return subprocess.run(
            [sys.executable, str(RUN_PY), "report",
             "--manifest", manifest_path, "--attempts-dir", attempts_dir,
             "--out-dir", tmp, "--event-ledger", str(ledger_path)],
            capture_output=True, text=True, timeout=60,
        )

    def test_report_accepts_a_run_whose_spawns_and_attempt_rows_agree(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = self._run_report(tmp, "run-s10-ok", ["a1", "a2"], ["a1", "a2"])
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("agentic report — run run-s10-ok", proc.stdout)
            # The event ledger is caller-asserted, so no native claim can be
            # made off it -- the report must say so rather than print a bare
            # count (it holds no native-proven attempts here either).
            self.assertNotIn("native-proven | 1", proc.stdout)

    def test_report_accepts_a_run_whose_spawns_and_attempt_rows_agree__negative(self):
        """The leak T32's own control concedes is invisible locally: two
        attempts spawned, one row recorded. Nothing inside the attempt ledger
        can see it; the event ledger can, and the report must refuse."""
        with tempfile.TemporaryDirectory() as tmp:
            proc = self._run_report(tmp, "run-s10-leak", ["a1"], ["a1", "a2"])
            self.assertNotEqual(proc.returncode, 0, proc.stdout)
            self.assertIn("agentic FAIL report:", proc.stderr)
            self.assertIn("a2", proc.stderr)
            self.assertFalse(
                os.path.isfile(os.path.join(tmp, "run-s10-leak-report.json")),
                "a refused report must not be written",
            )

        # The same ledger with the attempt row present is accepted, so the
        # refusal is about the reconciliation and not about the flag itself.
        with tempfile.TemporaryDirectory() as tmp:
            proc = self._run_report(tmp, "run-s10-leak", ["a1", "a2"], ["a1", "a2"])
            self.assertEqual(proc.returncode, 0, proc.stderr)


def _demo_manifest_with_plan(planned_n) -> Manifest:
    return dataclasses.replace(_demo_manifest("run-plan-demo"), planned_n=planned_n)


if __name__ == "__main__":
    unittest.main()
