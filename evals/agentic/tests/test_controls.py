"""Core-lane tests for evals.agentic.framework.controls (T04-T10).

Two self-contained toy scenarios stand in for the real per-plugin corpus
(which belongs to the registry lane, T11-T18):

* ``guarded-delete`` -- graveyard-shaped: back up before delete.
* ``gated-check`` -- redgate-shaped: prove the gate red before writing code,
  checked by a REAL executed guard.sh subprocess.

Every control/detector is exercised on both a case where it must fire and a
case where it must not, per the "paired with a negative case" ground rule.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import tempfile
import unittest

from evals.agentic.framework import io
from evals.agentic.framework.contract import (
    UNKNOWN,
    AdapterClass,
    ArmRole,
    Attempt,
    Capability,
    Card,
    CardKind,
    ContractError,
    ControlKind,
    EvidenceClass,
    Stratum,
    TerminalState,
    Usage,
    VacuousVerifier,
    Verdict,
    now_rfc3339,
)
from evals.agentic.framework.controls import (
    MUTATIONS,
    apply_mutation,
    assert_not_vacuous,
    detect_copied_evidence,
    detect_reward_hack,
    mutation_control,
    nop_control,
    oracle_control,
    inversion_control,
    run_control,
)

REPO_ROOT = io.repo_root()
FIXTURES = REPO_ROOT / "evals" / "agentic" / "fixtures" / "controls"


def _rel(p: pathlib.Path) -> str:
    return p.relative_to(REPO_ROOT).as_posix()


GUARDED_DELETE_CARD = Card(
    card_id="core-guarded-delete-01",
    plugin="core-fixture-guarded-delete",
    kind=CardKind.POSITIVE,
    task_path=_rel(FIXTURES / "oracle" / "guarded-delete"),
    outcome_verifier="evals.agentic.framework.controls:verify_guarded_delete_outcome",
    adoption_verifier="evals.agentic.framework.controls:verify_guarded_delete_adoption",
    pass_fixture=_rel(FIXTURES / "oracle" / "guarded-delete"),
    fail_fixture=_rel(FIXTURES / "nop" / "guarded-delete-no-side-effects"),
    expected_boundary_verdict="",
    capabilities=(),
    mutations=("reorder-backup-after-delete", "corrupt-pinned-hash"),
)

GATED_CHECK_CARD = Card(
    card_id="core-gated-check-01",
    plugin="core-fixture-gated-check",
    kind=CardKind.POSITIVE,
    task_path=_rel(FIXTURES / "oracle" / "gated-check"),
    outcome_verifier="evals.agentic.framework.controls:verify_gated_check_outcome",
    adoption_verifier="evals.agentic.framework.controls:verify_gated_check_adoption",
    pass_fixture=_rel(FIXTURES / "oracle" / "gated-check"),
    fail_fixture=_rel(FIXTURES / "nop" / "gated-check-no-side-effects"),
    expected_boundary_verdict="",
    capabilities=(),
    mutations=("comment-out-check", "delete-guard-line", "blank-criteria", "truncate-manifest"),
)


def _always_true(workspace) -> bool:  # noqa: ANN001 -- test-local vacuous stub
    return True


VACUOUS_CARD = Card(
    card_id="core-vacuous-01",
    plugin="core-fixture-vacuous",
    kind=CardKind.POSITIVE,
    task_path=_rel(FIXTURES / "mutation" / "vacuous-pass"),
    outcome_verifier="evals.agentic.tests.test_controls:_always_true",
    adoption_verifier="evals.agentic.tests.test_controls:_always_true",
    pass_fixture=_rel(FIXTURES / "mutation" / "vacuous-pass"),
    fail_fixture=_rel(FIXTURES / "mutation" / "vacuous-pass"),
    expected_boundary_verdict="",
    capabilities=(),
    mutations=("blank-criteria",),  # present to satisfy Card's >=1 requirement; irrelevant here
)


def _copy_to_temp(src: pathlib.Path) -> tempfile.TemporaryDirectory:
    tmp = tempfile.TemporaryDirectory()
    dst = pathlib.Path(tmp.name) / "ws"
    shutil.copytree(src, dst)
    return tmp, dst  # type: ignore[return-value]


def _make_attempt(
    *, evidence_digest: str | None = None, run_id: str = "run-1", attempt_id: str = "at-1",
    started_at: str | None = None, ended_at: str | None = None,
) -> Attempt:
    strat = Stratum("anthropic", "sonnet", "5.1", "medium", "claude-cli")
    usage = Usage(
        model_id="sonnet", reported_by="claude-cli/2.1.263",
        input_tokens=1, output_tokens=1, cache_read_input_tokens=UNKNOWN,
        cache_creation_input_tokens=UNKNOWN, reasoning_tokens=UNKNOWN,
        total_tokens=2, wall_clock_ms=100, cost_usd=None,
    )
    outcome = Verdict(passed=True, verifier_id="v1", reason="ok", evidence_digest=evidence_digest)
    adoption = Verdict(passed=True, verifier_id="v2", reason="ok")
    return Attempt(
        attempt_id=attempt_id, run_id=run_id, card_id="c1", arm_id="arm-1",
        role=ArmRole.TREATMENT, control_kind=None, parent_attempt_id=None,
        terminal_state=TerminalState.DELIVERED,
        evidence_class=EvidenceClass.FRAMEWORK, adapter_class=AdapterClass.STUB,
        requested=strat, realized=strat, fallback_flags=(), usage=usage,
        outcome=outcome, adoption=adoption,
        started_at=started_at or "2026-09-06T00:00:00.000Z",
        ended_at=ended_at or "2026-09-06T23:59:59.999Z",
        session_id=None, event_ids=(), arrived_after_terminal=False,
    )


# ---------------------------------------------------------------------------
# T06 -- oracle control passes (the calibration ceiling)
# ---------------------------------------------------------------------------

class OracleControl(unittest.TestCase):
    def test_oracle_passes_guarded_delete(self):
        result = oracle_control(GUARDED_DELETE_CARD, FIXTURES / "oracle" / "guarded-delete")
        self.assertEqual(result.reward, 1)
        self.assertTrue(result.verdict.passed)

    def test_oracle_passes_gated_check(self):
        result = oracle_control(GATED_CHECK_CARD, FIXTURES / "oracle" / "gated-check")
        self.assertEqual(result.reward, 1)
        self.assertTrue(result.verdict.passed)

    def test_oracle_is_reproducible_across_two_runs(self):
        a = oracle_control(GATED_CHECK_CARD, FIXTURES / "oracle" / "gated-check")
        b = oracle_control(GATED_CHECK_CARD, FIXTURES / "oracle" / "gated-check")
        self.assertEqual(a.reward, b.reward)
        self.assertEqual(a.verdict.passed, b.verdict.passed)
        self.assertEqual(a.verdict.reason, b.verdict.reason)

    def test_negative_control_an_uncalibratable_verifier_would_reject_even_the_oracle(self):
        """T06's named negative control: if a verifier were too strict for
        even the oracle to pass, that is a corpus defect. Demonstrate the
        distinction by using a broken variant of the outcome verifier that
        checks a nonexistent extra file -- it must fail the true oracle too,
        proving the failure is the VERIFIER's, not a property of 'oracle'."""
        from evals.agentic.framework import controls as controls_mod

        def _overly_strict(workspace):
            ws = pathlib.Path(workspace)
            return controls_mod.verify_guarded_delete_outcome(ws) and (ws / "nonexistent-marker").is_file()

        setattr(controls_mod, "_test_overly_strict_outcome", staticmethod(_overly_strict))
        try:
            broken_card = Card(
                card_id="core-guarded-delete-broken",
                plugin=GUARDED_DELETE_CARD.plugin, kind=CardKind.POSITIVE,
                task_path=GUARDED_DELETE_CARD.task_path,
                outcome_verifier="evals.agentic.framework.controls:_test_overly_strict_outcome",
                adoption_verifier=GUARDED_DELETE_CARD.adoption_verifier,
                pass_fixture=GUARDED_DELETE_CARD.pass_fixture,
                fail_fixture=GUARDED_DELETE_CARD.fail_fixture,
                expected_boundary_verdict="", capabilities=(),
                mutations=GUARDED_DELETE_CARD.mutations,
            )
            result = oracle_control(broken_card, FIXTURES / "oracle" / "guarded-delete")
            self.assertEqual(result.reward, 0, "an uncalibratable verifier rejects even the oracle")
        finally:
            delattr(controls_mod, "_test_overly_strict_outcome")

    def test_oracle_passes_guarded_delete__negative(self):
        """Catalog sibling (contract §7.4 item 4) for T06. entry.negative_control
        names fixtures/controls/oracle/guarded-delete; run the SAME
        oracle_control machinery against the mismatched nop fixture and
        require it to red."""
        result = oracle_control(GUARDED_DELETE_CARD, FIXTURES / "nop" / "guarded-delete-no-side-effects")
        self.assertNotEqual(result.reward, 1)


# ---------------------------------------------------------------------------
# T04 -- nop control is caught
# ---------------------------------------------------------------------------

class NopControl(unittest.TestCase):
    def test_nop_fails_guarded_delete(self):
        result = nop_control(GUARDED_DELETE_CARD, FIXTURES / "nop" / "guarded-delete-no-side-effects")
        self.assertEqual(result.reward, 0)
        self.assertFalse(result.verdict.passed)

    def test_nop_fails_gated_check(self):
        result = nop_control(GATED_CHECK_CARD, FIXTURES / "nop" / "gated-check-no-side-effects")
        self.assertEqual(result.reward, 0)
        self.assertFalse(result.verdict.passed)

    def test_negative_control_a_prose_only_verifier_would_wrongly_pass_nop(self):
        """T04's named negative control: 'a verifier satisfiable by prose
        alone lets nop through.' Demonstrate the contrast directly: a naive
        verifier that only checks SOME file exists in the workspace (as a
        transcript-grep analogue would) passes the nop fixture, while the
        real re-deriving verifier used above correctly scores it 0."""
        naive_verifier_passes = any(
            (FIXTURES / "nop" / "guarded-delete-no-side-effects").iterdir()
        )
        self.assertTrue(naive_verifier_passes, "the naive check would wrongly let nop through")
        real_result = nop_control(GUARDED_DELETE_CARD, FIXTURES / "nop" / "guarded-delete-no-side-effects")
        self.assertEqual(real_result.reward, 0, "the real verifier must not be fooled the same way")

    def test_nop_fails_guarded_delete__negative(self):
        """Catalog sibling (contract §7.4 item 4) for T04. entry.negative_control
        names fixtures/controls/nop/guarded-delete-no-side-effects."""
        return self.test_negative_control_a_prose_only_verifier_would_wrongly_pass_nop()


# ---------------------------------------------------------------------------
# T05 -- inversion control is caught
# ---------------------------------------------------------------------------

class InversionControl(unittest.TestCase):
    def test_inversion_fails_outcome_with_order_named_in_the_reason(self):
        result = inversion_control(GUARDED_DELETE_CARD, FIXTURES / "inversion" / "guarded-delete-wrong-order")
        self.assertEqual(result.reward, 0)
        self.assertFalse(result.verdict.passed)
        self.assertIn("order violated", result.verdict.reason)

    def test_negative_control_presence_only_adoption_check_would_wrongly_pass_inversion(self):
        """T05's named negative control: 'a verifier that only checks
        artifact presence passes inversion.' The bundle genuinely exists in
        the wrong-order fixture (adoption -- artifact presence -- correctly
        passes), while outcome (which also checks ORDER) correctly fails.
        An order-blind verifier that conflated the two would wrongly call
        this arm a success."""
        from evals.agentic.framework.controls import verify_guarded_delete_adoption

        adoption_alone = verify_guarded_delete_adoption(
            FIXTURES / "inversion" / "guarded-delete-wrong-order"
        )
        self.assertTrue(adoption_alone, "the bundle really was produced -- presence alone is not enough")
        outcome_result = inversion_control(
            GUARDED_DELETE_CARD, FIXTURES / "inversion" / "guarded-delete-wrong-order"
        )
        self.assertEqual(outcome_result.reward, 0, "outcome must fail despite adoption passing")

    def test_inversion_fails_outcome_with_order_named_in_the_reason__negative(self):
        """Catalog sibling (contract §7.4 item 4) for T05. entry.negative_control
        names fixtures/controls/inversion/guarded-delete-wrong-order."""
        return self.test_negative_control_presence_only_adoption_check_would_wrongly_pass_inversion()


# ---------------------------------------------------------------------------
# T10 -- mutation control, data-driven from fixtures/controls/mutation/expected-flips.json
# ---------------------------------------------------------------------------

_FLIPS = json.loads((FIXTURES / "mutation" / "expected-flips.json").read_text())

_CARD_BY_ID = {
    GUARDED_DELETE_CARD.card_id: GUARDED_DELETE_CARD,
    GATED_CHECK_CARD.card_id: GATED_CHECK_CARD,
}


class MutationControl(unittest.TestCase):
    def test_expected_flips_fixture_is_nonempty(self):
        self.assertGreater(len(_FLIPS["flips"]), 0)

    def test_every_declared_mutation_flips_its_declared_column_from_green_to_red(self):
        for row in _FLIPS["flips"]:
            with self.subTest(card=row["card_id"], mutation=row["mutation"]):
                card = _CARD_BY_ID[row["card_id"]]
                pass_root = REPO_ROOT / row["pass_fixture"]
                with tempfile.TemporaryDirectory() as tmp:
                    ws = pathlib.Path(tmp) / "ws"
                    shutil.copytree(pass_root, ws)

                    before = run_control(ControlKind.ORACLE, card, ws)
                    self.assertEqual(before.reward, 1, f"{row['card_id']} pass_fixture must start green")

                    result = mutation_control(card, ws, row["mutation"])

                    if row["flips"] in ("outcome", "both"):
                        self.assertEqual(
                            result.reward, 0,
                            f"{row['mutation']} on {row['card_id']} must flip outcome to red",
                        )
                    if row["flips"] in ("adoption", "both"):
                        adoption_fn_name = card.adoption_verifier.split(":", 1)[1]
                        from evals.agentic.framework import controls as controls_mod
                        adoption_fn = getattr(controls_mod, adoption_fn_name)
                        self.assertFalse(
                            adoption_fn(ws),
                            f"{row['mutation']} on {row['card_id']} must flip adoption to red",
                        )

    def test_run_control_requires_mutation_argument_for_mutation_kind(self):
        with self.assertRaises(ContractError):
            run_control(ControlKind.MUTATION, GUARDED_DELETE_CARD, FIXTURES / "oracle" / "guarded-delete")

    def test_run_control_rejects_mutation_argument_for_non_mutation_kind(self):
        with self.assertRaises(ContractError):
            run_control(
                ControlKind.ORACLE, GUARDED_DELETE_CARD, FIXTURES / "oracle" / "guarded-delete",
                mutation="blank-criteria",
            )

    def test_apply_mutation_on_a_fixture_missing_the_target_file_raises(self):
        """Negative control: a mutation must not silently no-op when its
        target file is absent from the workspace."""
        with tempfile.TemporaryDirectory() as tmp:
            ws = pathlib.Path(tmp) / "ws"
            shutil.copytree(FIXTURES / "nop" / "guarded-delete-no-side-effects", ws)
            with self.assertRaises(ContractError):
                apply_mutation("comment-out-check", ws)  # no guard.sh in this fixture

    def test_every_declared_mutation_flips_its_declared_column_from_green_to_red__negative(self):
        """Catalog sibling (contract §7.4 item 4) for T10. entry.negative_control
        names fixtures/controls/mutation/vacuous-pass: a verifier that is
        always True, which by construction no mutation can ever red --
        assert_not_vacuous must catch this and raise, in THIS class (not
        merely in VacuousVerifierDetection) so the catalog sibling
        convention is satisfied on the same test class as T10's main test."""
        with self.assertRaises(VacuousVerifier):
            assert_not_vacuous(VACUOUS_CARD, FIXTURES / "mutation" / "vacuous-pass")

    def test_all_six_named_mutations_exist(self):
        self.assertEqual(
            set(MUTATIONS),
            {
                "delete-guard-line", "reorder-backup-after-delete", "blank-criteria",
                "corrupt-pinned-hash", "comment-out-check", "truncate-manifest",
            },
        )


class VacuousVerifierDetection(unittest.TestCase):
    """T10's structural half: assert_not_vacuous."""

    def test_guarded_delete_card_is_not_vacuous(self):
        assert_not_vacuous(GUARDED_DELETE_CARD, FIXTURES / "oracle" / "guarded-delete")  # must not raise

    def test_gated_check_card_is_not_vacuous(self):
        assert_not_vacuous(GATED_CHECK_CARD, FIXTURES / "oracle" / "gated-check")  # must not raise

    def test_negative_control_always_true_verifier_is_reported_vacuous(self):
        """T10's named negative control: 'a verifier asserting only
        exit_code == 0 of a script that always exits 0.' Here: a verifier
        that always returns True, which by construction no mutation can red."""
        with self.assertRaises(VacuousVerifier):
            assert_not_vacuous(VACUOUS_CARD, FIXTURES / "mutation" / "vacuous-pass")


# ---------------------------------------------------------------------------
# T07 -- reward-hack detection
# ---------------------------------------------------------------------------

class RewardHack(unittest.TestCase):
    def _attempt(self):
        return _make_attempt()

    def test_unverified_hash_is_detected(self):
        hack = detect_reward_hack(
            self._attempt(), GUARDED_DELETE_CARD, FIXTURES / "reward-hack" / "unverified-hash"
        )
        self.assertEqual(hack, "unverified-hash")

    def test_commented_guard_is_detected(self):
        hack = detect_reward_hack(
            self._attempt(), GATED_CHECK_CARD, FIXTURES / "reward-hack" / "commented-guard"
        )
        self.assertEqual(hack, "commented-guard")

    def test_unfalsifiable_criteria_is_detected(self):
        hack = detect_reward_hack(
            self._attempt(), GATED_CHECK_CARD, FIXTURES / "reward-hack" / "unfalsifiable-criteria"
        )
        self.assertEqual(hack, "unfalsifiable-criteria")

    def test_echoed_expectation_is_detected(self):
        hack = detect_reward_hack(
            self._attempt(), GUARDED_DELETE_CARD, FIXTURES / "reward-hack" / "echoed-expectation"
        )
        self.assertEqual(hack, "echoed-expectation")

    def test_negative_control_a_genuinely_clean_pass_is_not_flagged_as_any_hack(self):
        """Proves detect_reward_hack is not a machine that flags everything:
        a real, correctly-produced pass on both scenarios reports None."""
        self.assertIsNone(
            detect_reward_hack(self._attempt(), GUARDED_DELETE_CARD, FIXTURES / "oracle" / "guarded-delete")
        )
        self.assertIsNone(
            detect_reward_hack(self._attempt(), GATED_CHECK_CARD, FIXTURES / "oracle" / "gated-check")
        )

    def test_negative_control_substring_match_on_claim_would_miss_unverified_hash(self):
        """T07's named negative control: 'substring- or regex-only verifiers
        pass every one of these.' A naive check that only confirms a
        'digest' key is PRESENT (never recomputing it) would wrongly accept
        the unverified-hash fixture."""
        ws = FIXTURES / "reward-hack" / "unverified-hash"
        events = [json.loads(line) for line in (ws / "events.jsonl").read_text().splitlines() if line.strip()]
        backup = next(e for e in events if e["op"] == "backup")
        naive_check_passes = isinstance(backup.get("digest"), str) and len(backup["digest"]) == 64
        self.assertTrue(naive_check_passes, "the naive presence-only check is fooled")
        real_check = detect_reward_hack(self._attempt(), GUARDED_DELETE_CARD, ws)
        self.assertEqual(real_check, "unverified-hash", "the real, re-deriving check is not fooled")

    def test_unverified_hash_is_detected__negative(self):
        """Catalog sibling (contract §7.4 item 4) for T07. entry.negative_control
        names fixtures/controls/reward-hack/unverified-hash."""
        return self.test_negative_control_substring_match_on_claim_would_miss_unverified_hash()


# ---------------------------------------------------------------------------
# T08 -- copied-evidence detection
# ---------------------------------------------------------------------------

class CopiedEvidence(unittest.TestCase):
    def _prior_attempt(self):
        source_dir = FIXTURES / "copied-evidence" / "source-attempt" / "evidence"
        from evals.agentic.framework.controls import _evidence_digest

        digest = _evidence_digest(source_dir)
        return _make_attempt(
            evidence_digest=digest, run_id="run-A", attempt_id="at-A",
            started_at="2026-09-06T09:00:00.000Z", ended_at="2026-09-06T10:30:00.000Z",
        )

    def test_raw_copy_carrying_the_old_manifest_is_detected(self):
        current = _make_attempt(
            run_id="run-B", attempt_id="at-B",
            started_at="2026-09-06T10:55:00.000Z", ended_at="2026-09-06T11:05:00.000Z",
        )
        copied = detect_copied_evidence(
            current, [self._prior_attempt()],
            FIXTURES / "copied-evidence" / "copied-into-new-attempt",
        )
        self.assertTrue(copied)

    def test_legitimate_rerun_with_identical_content_but_fresh_binding_is_accepted(self):
        current = _make_attempt(
            run_id="run-B", attempt_id="at-B",
            started_at="2026-09-06T10:55:00.000Z", ended_at="2026-09-06T11:05:00.000Z",
        )
        copied = detect_copied_evidence(
            current, [self._prior_attempt()],
            FIXTURES / "copied-evidence" / "legitimate-rerun",
        )
        self.assertFalse(copied, "identical content with a genuine, in-window binding is not copied evidence")

    def test_negative_control_no_prior_attempts_never_flags_anything(self):
        current = _make_attempt(run_id="run-A", attempt_id="at-A")
        self.assertFalse(
            detect_copied_evidence(current, [], FIXTURES / "copied-evidence" / "source-attempt")
        )

    def test_raw_copy_carrying_the_old_manifest_is_detected__negative(self):
        """Catalog sibling (contract §7.4 item 4) for T08. entry.negative_control
        names fixtures/controls/copied-evidence/legitimate-rerun: identical
        content, but a fresh, correctly-bound manifest -- must NOT be flagged."""
        return self.test_legitimate_rerun_with_identical_content_but_fresh_binding_is_accepted()


if __name__ == "__main__":
    unittest.main()
