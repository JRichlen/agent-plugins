"""Measurement-lane tests for evals.agentic.framework.reporting.

Covers T40 (user outcome separated from ritual adoption, never combined into
one headline) and T41 (grader agreement reuses agreement.py verbatim -- no
local kappa). Also exercises the §5.4 refusal rule (assert_native_claims) and
build_report's conservation + denominator-reconciliation wiring, since those
are this module's job per contract §3.7.
"""
from __future__ import annotations

import importlib.util
import pathlib
import re
import tempfile
import unittest

from evals.agentic.framework import io
from evals.agentic.framework.accounting import AttemptLedger
from evals.agentic.framework.contract import (
    EvidenceClass,
    NativeProofRequired,
    TerminalState,
)
from evals.agentic.framework.reporting import (
    build_report,
    evidence_summary,
    grader_agreement,
    outcome_adoption_matrix,
    render_json,
    render_markdown,
    render_text,
    sample_hash,
)

FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "measurement"
REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]


def _load_builders():
    spec = importlib.util.spec_from_file_location(
        "measurement_fixture_builders", FIXTURES / "builders.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builders = _load_builders()


def _make_manifest(**overrides):
    from evals.agentic.framework.contract import Manifest

    fields = dict(
        run_id="run-report-test", created_at="2026-09-06T00:00:00.000Z",
        git_commit="6d5342c", branch="feat/agentic-test-framework", offline=True,
        toolchain={"python": "3.12.3"}, lanes=("measurement",),
        estimands=(), noninferiority_margin=0.05, min_valid=3, min_clusters=8,
        planned_n={}, holdout_seed=1, catalog_digest="deadbeef" * 8,
        skipped=(), approvals=(),
    )
    fields.update(overrides)
    return Manifest(**fields)


# ---------------------------------------------------------------------------
# T40 -- user outcome separated from ritual adoption
# ---------------------------------------------------------------------------

class OutcomeVsAdoption(unittest.TestCase):
    def _attempts_from_fixture(self):
        spec = io.load_json(FIXTURES / "outcome_adoption" / "redgate-40.json")
        plugin = spec["plugin"]
        attempts = []
        for _ in range(spec["n11"]):
            attempts.append(builders.make_attempt(card_id=f"{plugin}-pos-01", outcome=True, adoption=True))
        for _ in range(spec["n10"]):
            attempts.append(builders.make_attempt(card_id=f"{plugin}-pos-02", outcome=True, adoption=False))
        for _ in range(spec["n01"]):
            attempts.append(builders.make_attempt(card_id=f"{plugin}-pos-03", outcome=False, adoption=True))
        for _ in range(spec["n00"]):
            attempts.append(builders.make_attempt(card_id=f"{plugin}-pos-04", outcome=False, adoption=False))
        return attempts, spec

    def test_2x2_matches_worked_example(self):
        attempts, spec = self._attempts_from_fixture()
        matrix = outcome_adoption_matrix(attempts)
        cell = matrix[spec["plugin"]]
        self.assertEqual(cell.outcome_pass_adoption_pass, spec["n11"])
        self.assertEqual(cell.outcome_pass_adoption_fail, spec["n10"])
        self.assertEqual(cell.outcome_fail_adoption_pass, spec["n01"])
        self.assertEqual(cell.outcome_fail_adoption_fail, spec["n00"])
        self.assertEqual(cell.evaluated(), 40)

        exp = spec["expected"]
        self.assertAlmostEqual(cell.outcome_rate().value, exp["outcome_rate"], places=3)
        self.assertAlmostEqual(cell.adoption_rate().value, exp["adoption_rate"], places=3)
        self.assertAlmostEqual(cell.ritual_without_outcome().value, exp["ritual_without_outcome"], places=5)
        self.assertAlmostEqual(cell.outcome_without_ritual().value, exp["outcome_without_ritual"], places=5)

    def test_unevaluated_verdicts_are_excluded_from_n_not_coerced_to_fail(self):
        attempts = [
            builders.make_attempt(card_id="p-pos-01", outcome=True, adoption=True),
            builders.make_attempt(card_id="p-pos-01", outcome=None, adoption=True),  # outcome verifier never ran
            builders.make_attempt(card_id="p-pos-01", outcome=True, adoption=None),  # adoption verifier never ran
        ]
        matrix = outcome_adoption_matrix(attempts)
        cell = matrix["p"]
        self.assertEqual(cell.evaluated(), 1)  # only the fully-evaluated attempt counts
        self.assertEqual(cell.outcome_unevaluated, 1)
        self.assertEqual(cell.adoption_unevaluated, 1)

    def test_fault_and_cancel_attempts_excluded_from_matrix(self):
        attempts = [
            builders.make_attempt(card_id="p-pos-01", terminal_state=TerminalState.FAULT, outcome=None, adoption=None),
            builders.make_attempt(card_id="p-pos-01", terminal_state=TerminalState.CANCELLED, outcome=None, adoption=None),
            builders.make_attempt(card_id="p-pos-01", outcome=True, adoption=True),
        ]
        matrix = outcome_adoption_matrix(attempts)
        self.assertEqual(matrix["p"].evaluated(), 1)

    def test_timeout_after_delivery_can_pass_adoption_regardless_of_outcome(self):
        a = builders.make_attempt(
            card_id="p-pos-01", terminal_state=TerminalState.TIMEOUT_AFTER_DELIVERY,
            outcome=False, adoption=True,
        )
        matrix = outcome_adoption_matrix([a])
        cell = matrix["p"]
        self.assertEqual(cell.outcome_fail_adoption_pass, 1)  # proper stopping can pass adoption, fail outcome

    # -- negative control: a composite score in which ritual earns credit
    #    regardless of outcome -----------------------------------------------

    def test_composite_score_would_make_every_plugin_work_by_construction(self):
        """T40 negative control: a composite in which performing the ritual
        earns credit regardless of outcome makes every plugin 'work' because
        every ritual is something a model can perform. Demonstrated by
        constructing exactly that composite on the fixture and showing it
        reports success even where outcome_rate says the opposite."""
        attempts, spec = self._attempts_from_fixture()
        matrix = outcome_adoption_matrix(attempts)
        cell = matrix[spec["plugin"]]
        # composite: pass if adoption passed, regardless of outcome
        composite_pass = cell.outcome_pass_adoption_pass + cell.outcome_fail_adoption_pass
        composite_rate = composite_pass / cell.evaluated()
        self.assertAlmostEqual(composite_rate, cell.adoption_rate().value)
        # the composite hides exactly the vacuity cell outcome-separated
        # reporting exposes:
        self.assertGreater(cell.ritual_without_outcome().value, 0.0)
        self.assertNotAlmostEqual(composite_rate, cell.outcome_rate().value)

    def test_2x2_matches_worked_example__negative(self):
        """Catalog sibling (contract §7.4 item 4) for T40. entry.negative_control
        names fixtures/measurement/outcome_adoption/redgate-40.json: this must
        FAIL the composite 'ritual earns credit regardless of outcome' score
        (it must disagree with the correct outcome rate) for the T40 catalog
        entry to be considered non-vacuous."""
        return self.test_composite_score_would_make_every_plugin_work_by_construction()


# ---------------------------------------------------------------------------
# T41 -- grader agreement reuses agreement.py
# ---------------------------------------------------------------------------

class GraderAgreementReuse(unittest.TestCase):
    def test_round_trips_worked_example_via_the_real_script(self):
        a_path = FIXTURES / "agreement" / "grader-a.json"
        b_path = FIXTURES / "agreement" / "grader-b.json"
        with tempfile.TemporaryDirectory() as tmp:
            out_json = str(pathlib.Path(tmp) / "out.json")
            result = grader_agreement(
                str(a_path), str(b_path), name_a="human", name_b="grader", out_json=out_json,
            )
        self.assertIsNone(result.unavailable_reason)
        self.assertEqual(result.n, 40)
        self.assertEqual(result.agree, 34)
        self.assertAlmostEqual(result.percent, 85.0, places=1)
        self.assertAlmostEqual(result.kappa, 0.681, places=3)
        self.assertEqual(result.confusion["pass"]["pass"], 22)
        self.assertEqual(result.confusion["fail"]["fail"], 12)

    def test_exit_2_too_few_hashes_reports_unavailable_not_zero(self):
        a_path = FIXTURES / "agreement" / "grader-few-a.json"
        b_path = FIXTURES / "agreement" / "grader-few-b.json"
        with tempfile.TemporaryDirectory() as tmp:
            out_json = str(pathlib.Path(tmp) / "out.json")
            result = grader_agreement(
                str(a_path), str(b_path), name_a="a", name_b="b", out_json=out_json,
            )
        self.assertEqual(result.unavailable_reason, "fewer than two hashes in common")
        self.assertEqual(result.n, 0)  # unavailable, never a fabricated 0% agreement

    def test_exit_2_bad_labels_is_a_grader_defect_not_a_sample_size_problem(self):
        a_path = FIXTURES / "agreement" / "grader-bad-labels.json"
        b_path = FIXTURES / "agreement" / "grader-a.json"
        with tempfile.TemporaryDirectory() as tmp:
            out_json = str(pathlib.Path(tmp) / "out.json")
            result = grader_agreement(
                str(a_path), str(b_path), name_a="bad", name_b="good", out_json=out_json,
            )
        self.assertIsNotNone(result.unavailable_reason)
        self.assertIn("labels outside pass/fail", result.unavailable_reason)
        self.assertNotIn("fewer than two hashes", result.unavailable_reason)

    def test_round_trips_worked_example_via_the_real_script__negative(self):
        """Catalog sibling (contract §7.4 item 4) for T41. entry.negative_control
        names fixtures/measurement/agreement/grader-a.json: paired against a
        corrupted labels file, the real script must FAIL closed with a
        grader-defect reason, never silently miscounting, for the T41
        catalog entry to be considered non-vacuous."""
        return self.test_exit_2_bad_labels_is_a_grader_defect_not_a_sample_size_problem()

    def test_sample_hash_matches_agreement_py_join_key_shape(self):
        h = sample_hash("card-1", "arm-1", "attempt-1", "digest-1")
        self.assertRegex(h, r"^[0-9a-f]{64}$")
        # deterministic
        self.assertEqual(h, sample_hash("card-1", "arm-1", "attempt-1", "digest-1"))
        self.assertNotEqual(h, sample_hash("card-2", "arm-1", "attempt-1", "digest-1"))

    def test_no_local_kappa_implementation_anywhere_in_agentic(self):
        """T41 negative control: a local cohen_kappa() helper drifts from the
        real one. A source scan of evals/agentic/** must find no second kappa
        implementation -- only the shell-out in reporting.grader_agreement."""
        agentic_root = REPO_ROOT / "evals" / "agentic"
        offenders = []
        for path in agentic_root.rglob("*.py"):
            if "__pycache__" in path.parts or "tests" in path.parts:
                continue  # a test method's own name (e.g. this one) may say "kappa"
            text = path.read_text(encoding="utf-8")
            if re.search(r"def\s+[A-Za-z_]*_kappa[A-Za-z_]*\s*\(|def\s+kappa\s*\(", text):
                offenders.append(str(path))
        self.assertEqual(offenders, [], f"local kappa implementation(s) found: {offenders}")


# ---------------------------------------------------------------------------
# build_report / evidence_summary / assert_native_claims (§5.4 refusal rule)
# ---------------------------------------------------------------------------

class BuildReportAndNativeRefusal(unittest.TestCase):
    def test_evidence_summary_counts_every_class(self):
        attempts = [
            builders.make_attempt(evidence_class=EvidenceClass.FRAMEWORK),
            builders.make_attempt(evidence_class=EvidenceClass.FRAMEWORK),
            builders.make_attempt(evidence_class=EvidenceClass.SIMULATED),
        ]
        summary = evidence_summary(attempts)
        self.assertEqual(summary[EvidenceClass.FRAMEWORK], 2)
        self.assertEqual(summary[EvidenceClass.SIMULATED], 1)
        self.assertEqual(summary[EvidenceClass.NATIVE_PROVEN], 0)
        self.assertEqual(sum(summary.values()), 3)

    def test_build_report_reconciles_and_renders(self):
        manifest = _make_manifest()
        ledger = AttemptLedger(run_id=manifest.run_id)
        spec = io.load_json(FIXTURES / "conservation" / "100-attempts.json")
        for a in builders.attempts_from_conservation_rows(spec["rows"]):
            ledger.add(a)
        report = build_report(manifest, ledger, event_ledger=None)
        self.assertEqual(report.denominators.accounting, 100)
        text = render_text(report)
        self.assertIn("accounting 100 / scoring trials 79", text)
        as_json = render_json(report)
        self.assertEqual(as_json["denominators"]["accounting"], 100)
        md = render_markdown(report)
        self.assertIn("# agentic report", md)

    def test_assert_native_claims_refuses_when_no_native_proven_evidence(self):
        manifest = _make_manifest()
        ledger = AttemptLedger(run_id=manifest.run_id)
        ledger.add(builders.make_attempt(evidence_class=EvidenceClass.FRAMEWORK))
        report = build_report(manifest, ledger, event_ledger=None)
        with self.assertRaises(NativeProofRequired):
            from evals.agentic.framework.reporting import assert_native_claims
            assert_native_claims(report, None)

    def test_assert_native_claims_refuses_when_ledger_unverified_even_with_native_evidence(self):
        class _UnverifiedLedger:
            def has_event(self, event_id):
                return True

            def session_ids(self):
                return frozenset({"s1"})

            def host_observed_session_ids(self):
                return frozenset({"s1"})

            def is_verified(self):
                return False

            def signature_class(self, event_id):
                return None

        manifest = _make_manifest()
        ledger = AttemptLedger(run_id=manifest.run_id)
        ledger.add(builders.make_attempt(evidence_class=EvidenceClass.NATIVE_PROVEN, session_id="s1"))
        report = build_report(manifest, ledger, event_ledger=None)
        from evals.agentic.framework.reporting import assert_native_claims
        with self.assertRaises(NativeProofRequired):
            assert_native_claims(report, _UnverifiedLedger())

    def test_assert_native_claims_passes_with_verified_ledger_and_native_evidence(self):
        class _VerifiedLedger:
            def has_event(self, event_id):
                return True

            def session_ids(self):
                return frozenset({"s1"})

            def host_observed_session_ids(self):
                return frozenset({"s1"})

            def is_verified(self):
                return True

            def signature_class(self, event_id):
                return None

        manifest = _make_manifest()
        ledger = AttemptLedger(run_id=manifest.run_id)
        ledger.add(builders.make_attempt(evidence_class=EvidenceClass.NATIVE_PROVEN, session_id="s1"))
        report = build_report(manifest, ledger, event_ledger=None)
        from evals.agentic.framework.reporting import assert_native_claims
        assert_native_claims(report, _VerifiedLedger())  # must not raise

    # -- negative control: printing a native claim from offline-only evidence

    def test_render_text_never_claims_native_when_evidence_is_all_framework(self):
        """T09/T29/T31/T47 negative control: an offline-only report (every
        attempt EvidenceClass.FRAMEWORK) must never contain a 'native' /
        'proven in a real harness' sentence. render_text does not gate any
        such sentence behind assert_native_claims internally -- it prints
        exactly the evidence counts and nothing more -- so the assertion is
        that no narrative native-claim phrase appears in the plain-evidence
        case, only the bare enum-value label."""
        manifest = _make_manifest()
        ledger = AttemptLedger(run_id=manifest.run_id)
        ledger.add(builders.make_attempt(evidence_class=EvidenceClass.FRAMEWORK))
        report = build_report(manifest, ledger, event_ledger=None)
        text = render_text(report)
        self.assertNotRegex(text, r"proven in a (?:real|live) harness")
        self.assertNotRegex(text, r"\b52\b[^\n]{0,40}\bproven\b")


if __name__ == "__main__":
    unittest.main()
