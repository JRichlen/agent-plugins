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

_FORGED_NATIVE_ATTEMPT_KWARGS = dict(
    evidence_class=EvidenceClass.NATIVE_PROVEN,
    session_id="harness-sess-NEVER-ACKED",
    event_ids=("11111111-1111-4111-8111-111111111111",),
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


# ---------------------------------------------------------------------------
# REPAIR N-01: render_* must gate a native-proven count behind
# assert_native_claims, never print it as a bare trustworthy number.
# ---------------------------------------------------------------------------

class _VerifiedLedger:
    def has_event(self, event_id):
        return True

    def session_ids(self):
        return frozenset({"harness-sess-NEVER-ACKED"})

    def host_observed_session_ids(self):
        return frozenset({"harness-sess-NEVER-ACKED"})

    def is_verified(self):
        return True

    def signature_class(self, event_id):
        from evals.agentic.framework.contract import SignatureClass
        return SignatureClass.HOST_OBSERVED


class NativeEvidenceGating(unittest.TestCase):
    """N-01 (blocker): reproduces the lane's own negative control -- an
    attempt asserting evidence_class="native-proven" with a session_id no
    SESSION_ACK ever carried and an event_id in no ledger -- through
    build_report and every renderer with no event_ledger supplied."""

    def _forged_report(self):
        manifest = _make_manifest()
        ledger = AttemptLedger(run_id=manifest.run_id)
        ledger.add(builders.make_attempt(card_id="redgate-pos-01", **_FORGED_NATIVE_ATTEMPT_KWARGS))
        return build_report(manifest, ledger, event_ledger=None)

    def test_render_markdown_never_prints_a_bare_forged_native_count(self):
        report = self._forged_report()
        md = render_markdown(report)
        self.assertIn("native-proven", md)
        self.assertNotIn("| native-proven | 1 |", md)  # the exact banned rendering
        self.assertIn("UNVERIFIABLE", md)

    def test_render_text_never_prints_a_bare_forged_native_count(self):
        report = self._forged_report()
        text = render_text(report)
        self.assertNotIn("native-proven: 1\n", text)
        self.assertIn("UNVERIFIABLE", text)

    def test_render_json_carries_an_explicit_unverified_flag(self):
        report = self._forged_report()
        as_json = render_json(report)
        self.assertEqual(as_json["evidence"]["native-proven"], 1)  # the raw count is still honest
        self.assertFalse(as_json["evidence_native_proven_verified"])
        self.assertIsNotNone(as_json["evidence_native_proven_unverifiable_reason"])

    def test_a_verified_ledger_supplied_to_the_renderer_clears_the_flag(self):
        report = self._forged_report()
        as_json = render_json(report, event_ledger=_VerifiedLedger())
        self.assertTrue(as_json["evidence_native_proven_verified"])
        md = render_markdown(report, event_ledger=_VerifiedLedger())
        self.assertIn("| native-proven | 1 |", md)
        self.assertNotIn("UNVERIFIABLE", md)

    def test_render_markdown_never_prints_a_bare_forged_native_count__negative(self):
        """Catalog sibling for the N-01 fix: the pre-fix renderer printed
        exactly '| native-proven | 1 |' for this forged attempt with no
        assert_native_claims call anywhere."""
        report = self._forged_report()
        md = render_markdown(report)
        self.assertNotEqual(
            [l for l in md.splitlines() if "native-proven" in l],
            ["| native-proven | 1 |"],
        )


# ---------------------------------------------------------------------------
# REPAIR S-06: a plugin whose every attempt is scoring-invalid must still
# appear, rendered "unavailable" with a reason -- never silently absent.
# ---------------------------------------------------------------------------

class AllFaultPluginStillAppears(unittest.TestCase):
    def test_all_fault_plugin_appears_with_a_reason_not_absent(self):
        attempts = builders.attempts_for_card("voice-neg-02", ["fault"] * 5) + \
            builders.attempts_for_card("redgate-pos-01", ["pass"] * 3)
        matrix = outcome_adoption_matrix(attempts)
        self.assertIn("voice", matrix)  # S-06 repro: this used to be absent
        cell = matrix["voice"]
        self.assertEqual(cell.evaluated(), 0)
        rate = cell.outcome_rate()
        self.assertIsNone(rate.value)
        self.assertEqual(rate.unavailable_reason, "no valid samples: 5/5 FAULT")

    def test_scoring_valid_but_unevaluated_plugin_gets_a_distinct_reason(self):
        """A plugin whose scoring-valid attempts are all unevaluated (the
        verifier never ran) must not be told it had 'no valid samples' --
        five valid samples existed; the verifier is what failed."""
        attempts = [
            builders.make_attempt(card_id="p-pos-01", outcome=None, adoption=None)
            for _ in range(5)
        ]
        matrix = outcome_adoption_matrix(attempts)
        cell = matrix["p"]
        self.assertEqual(cell.scoring_valid_total, 5)
        reason = cell.outcome_rate().unavailable_reason
        self.assertIn("no evaluated verdicts", reason)
        self.assertNotIn("FAULT", reason)

    def test_all_fault_plugin_appears_with_a_reason_not_absent__negative(self):
        """Catalog sibling for the S-06 fix: the pre-fix matrix builder never
        created a bucket for an all-FAULT plugin at all."""
        attempts = builders.attempts_for_card("voice-neg-02", ["fault"] * 5)
        matrix = outcome_adoption_matrix(attempts)
        naive_keys_before_fix: dict = {}
        self.assertNotEqual(sorted(matrix), sorted(naive_keys_before_fix))
        self.assertIn("voice", matrix)


# ---------------------------------------------------------------------------
# REPAIR S-05: min_valid, declared on the manifest, gates the 2x2 rates too
# ---------------------------------------------------------------------------

class MinValidGatesTheMatrixToo(unittest.TestCase):
    def test_a_single_sample_cell_renders_starved_not_100_percent(self):
        manifest = _make_manifest(min_valid=3)
        ledger = AttemptLedger(run_id=manifest.run_id)
        ledger.add(builders.make_attempt(card_id="p-pos-01", outcome=True, adoption=True))
        report = build_report(manifest, ledger, event_ledger=None)
        cell = report.per_plugin["p"]
        self.assertIsNone(cell.outcome_rate(min_valid=manifest.min_valid).value)
        self.assertIn("starved", cell.outcome_rate(min_valid=manifest.min_valid).unavailable_reason)
        text = render_text(report)
        self.assertIn("starved", text)
        self.assertNotIn("outcome=1.0000 (1/1)", text)

    def test_a_single_sample_cell_renders_starved_not_100_percent__negative(self):
        """Catalog sibling for the S-05 fix: Cell2x2.outcome_rate() with no
        min_valid argument (the pre-fix call site) reads this exact one-trial
        cell as a clean 100%."""
        manifest = _make_manifest(min_valid=3)
        ledger = AttemptLedger(run_id=manifest.run_id)
        ledger.add(builders.make_attempt(card_id="p-pos-01", outcome=True, adoption=True))
        report = build_report(manifest, ledger, event_ledger=None)
        cell = report.per_plugin["p"]
        naive = cell.outcome_rate()  # no min_valid -- the pre-fix call shape
        self.assertIsNotNone(naive.value)
        self.assertNotEqual(naive.render(), cell.outcome_rate(min_valid=manifest.min_valid).render())


# ---------------------------------------------------------------------------
# REPAIR S-09: a genuine cross-model token contamination must be visible as
# a warning, never swallowed into an empty, unremarkable section.
# ---------------------------------------------------------------------------

class CrossModelContaminationIsVisible(unittest.TestCase):
    def test_build_report_surfaces_the_contamination_as_a_warning(self):
        attempts = [
            builders.make_attempt(card_id="p-pos-01", usage=builders.make_usage(model_id="claude-opus-5")),
            builders.make_attempt(card_id="p-pos-01", usage=builders.make_usage(model_id="claude-sonnet-5")),
        ]
        manifest = _make_manifest()
        ledger = AttemptLedger(run_id=manifest.run_id)
        for a in attempts:
            ledger.add(a)
        report = build_report(manifest, ledger, event_ledger=None)
        self.assertEqual(report.per_stratum_tokens, {})  # still refused, never pooled
        self.assertTrue(any("pool_tokens" in w and "model_id" in w for w in report.warnings))
        text = render_text(report)
        self.assertIn("WARNING", text)
        md = render_markdown(report)
        self.assertIn("Warnings", md)

    def test_build_report_surfaces_the_contamination_as_a_warning__negative(self):
        """Catalog sibling for the S-09 fix: the pre-fix build_report caught
        CrossModelPoolingRefused and discarded it with `per_field = {}`,
        leaving `report.warnings == ()` on this exact contaminated ledger."""
        attempts = [
            builders.make_attempt(card_id="p-pos-01", usage=builders.make_usage(model_id="claude-opus-5")),
            builders.make_attempt(card_id="p-pos-01", usage=builders.make_usage(model_id="claude-sonnet-5")),
        ]
        manifest = _make_manifest()
        ledger = AttemptLedger(run_id=manifest.run_id)
        for a in attempts:
            ledger.add(a)
        report = build_report(manifest, ledger, event_ledger=None)
        naive_warnings_before_fix: tuple = ()
        self.assertNotEqual(report.warnings, naive_warnings_before_fix)


# ---------------------------------------------------------------------------
# REPAIR S-04: renderer parity -- every count/reason string in render_json
# must also appear in render_text and render_markdown.
# ---------------------------------------------------------------------------

class RendererParity(unittest.TestCase):
    def _rich_report(self):
        import dataclasses as dc
        from evals.agentic.framework.analysis import Interval, NoninferiorityResult

        manifest = _make_manifest()
        ledger = AttemptLedger(run_id=manifest.run_id)
        ledger.add(builders.make_attempt(card_id="voice-pos-01", outcome=True, adoption=True))
        for _ in range(9):
            ledger.add(builders.make_attempt(card_id="voice-pos-01", outcome=None, adoption=None))
        report = build_report(manifest, ledger, event_ledger=None)
        interval = Interval(point=0.1375, lo=-0.2596, hi=0.5346, method="cluster-t", n_clusters=4,
                             cluster_variable="card", deff=None, deff_method=None, icc_raw=None,
                             unavailable_reason=None)
        noninf = NoninferiorityResult(established=False, margin=0.05, lower_bound=-0.2596, reason="not established")
        return dc.replace(
            report,
            effects={"full-package": interval},
            noninferiority={"full-package": noninf},
            warnings=("no native evidence in this run",),
        )

    def test_unevaluated_counts_appear_in_every_renderer(self):
        report = self._rich_report()
        text = render_text(report)
        md = render_markdown(report)
        self.assertIn("unevaluated: outcome=9 adoption=9", text)
        self.assertIn("outcome=9 adoption=9", md)

    def test_header_fields_appear_in_both_text_and_markdown(self):
        report = self._rich_report()
        text = render_text(report)
        md = render_markdown(report)
        for token in ("min_valid=3", "min_clusters=8", "noninferiority_margin=0.05", "holdout_seed=1"):
            self.assertIn(token, text)
            self.assertIn(token, md)

    def test_noninferiority_appears_in_markdown_not_just_text_and_json(self):
        report = self._rich_report()
        md = render_markdown(report)
        as_json = render_json(report)
        self.assertIn("not established", md)
        self.assertEqual(as_json["noninferiority"]["full-package"]["reason"], "not established")

    def test_warnings_appear_in_markdown_not_just_text(self):
        report = self._rich_report()
        md = render_markdown(report)
        self.assertIn("no native evidence in this run", md)

    def test_effects_appear_in_markdown(self):
        report = self._rich_report()
        md = render_markdown(report)
        self.assertIn("full-package", md)
        self.assertIn("cluster-t", md)

    def test_unevaluated_counts_appear_in_every_renderer__negative(self):
        """Catalog sibling for the S-04 fix: the pre-fix render_markdown
        table had exactly 4 columns (plugin/outcome/adoption/ritual columns)
        with no unevaluated column at all -- reproduced literally here as the
        naive table row -- which must disagree with the real, fixed one."""
        report = self._rich_report()
        cell = report.per_plugin["voice"]
        naive_row = (
            f"| voice | {cell.outcome_rate(min_valid=report.manifest.min_valid).render()} | "
            f"{cell.adoption_rate(min_valid=report.manifest.min_valid).render()} | "
            f"{cell.ritual_without_outcome().render()} | {cell.outcome_without_ritual().render()} |"
        )
        self.assertNotIn("unevaluated", naive_row)
        md = render_markdown(report)
        real_row = [l for l in md.splitlines() if l.startswith("| voice |")][0]
        self.assertNotEqual(real_row, naive_row)
        self.assertIn("unevaluated", md)


if __name__ == "__main__":
    unittest.main()
