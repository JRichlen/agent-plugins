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

import os
import re
import subprocess
import sys
import unittest

from evals.agentic.framework import io, registry
from evals.agentic.framework.contract import ALL_IDS, ApprovalGate, EvidenceClass

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


_DOCUMENTED_TOKENS = ("--offline", "--gate", "--catalog", "--id", "--lane", "driver", "coverage")
_UNDOCUMENTED_FLAG = "--frobnicate-the-widget"  # T49's own negative control, see fixture .txt


class EndToEndRunnerCli(unittest.TestCase):
    """T49: documented subcommands/flags, and a real (non-mocked) execution."""

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


if __name__ == "__main__":
    unittest.main()
