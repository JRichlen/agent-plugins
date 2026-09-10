"""Measurement-lane tests for evals.agentic.framework.accounting.

Covers T32 (every attempt is accounted for -- the conservation identity) and
T33 (UNKNOWN usage never becomes zero). Every test asserts observable
behavior and is paired with a negative case built from a real mutated/negative
fixture, per the task brief's instruction (rather than the catalog's
`<test_name>__negative` sibling-method convention, whose wiring the T01
implementer already deferred to registry/integration for the same reason:
these are executable behavior tests, not catalog-resolution plumbing).
"""
from __future__ import annotations

import importlib.util
import pathlib
import unittest

from evals.agentic.framework import io
from evals.agentic.framework.accounting import (
    AttemptLedger,
    MoneyTotal,
    Total,
    assert_planned_reconciles,
    coordination_attempts,
    cost_of,
    denominators,
    sum_usage,
)
from evals.agentic.framework.contract import (
    UNKNOWN,
    AccountingLeak,
    ArmRole,
    CrossModelPoolingRefused,
    TerminalState,
)

FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "measurement"


def _load_builders():
    spec = importlib.util.spec_from_file_location(
        "measurement_fixture_builders", FIXTURES / "builders.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builders = _load_builders()


# ---------------------------------------------------------------------------
# T32 -- every attempt is accounted for
# ---------------------------------------------------------------------------

class AttemptCompleteness(unittest.TestCase):
    """T32: accounting.py counts all attempts -- delivered, incomplete,
    cancelled, faulted, coordination -- and the conservation identity
    (accounting == scoring_trials + coordination + faults + cancels) holds."""

    def test_conservation_identity_100_attempts(self):
        spec = io.load_json(FIXTURES / "conservation" / "100-attempts.json")
        attempts = builders.attempts_from_conservation_rows(spec["rows"])
        self.assertEqual(len(attempts), spec["expected"]["accounting"])

        ledger = AttemptLedger(run_id="run-t32")
        for a in attempts:
            ledger.add(a)
        ledger.conserve()  # must not raise

        denoms = denominators(ledger.attempts())
        denoms.assert_reconciles()  # must not raise -- this is the T32 assertion

        exp = spec["expected"]
        self.assertEqual(denoms.accounting, exp["accounting"])
        self.assertEqual(denoms.scoring_valid, exp["scoring_valid"])
        self.assertEqual(denoms.scoring_trials, exp["scoring_trials"])
        self.assertEqual(denoms.coordination, exp["coordination"])
        self.assertEqual(denoms.coordination_total, exp["coordination_total"])
        self.assertEqual(denoms.faults, exp["faults"])
        self.assertEqual(denoms.cancels, exp["cancels"])
        self.assertEqual(
            denoms.render(),
            "accounting 100 / scoring trials 79 / coordination 5 / faults 7 / cancels 9",
        )
        # the reconciliation identity, spelled out numerically per the spec
        self.assertEqual(100, 79 + 5 + 7 + 9)
        self.assertEqual(
            denoms.accounting,
            denoms.scoring_trials + denoms.coordination + denoms.faults + denoms.cancels,
        )

    def test_retries_are_distinct_rows_sharing_parent_attempt_id(self):
        parent = builders.make_attempt(terminal_state=TerminalState.FAULT, attempt_id="parent-1")
        retry = builders.make_attempt(
            terminal_state=TerminalState.DELIVERED, attempt_id="retry-1", parent_attempt_id="parent-1",
        )
        ledger = AttemptLedger(run_id="run-retry")
        ledger.add(parent)
        ledger.add(retry)
        ledger.conserve()  # both rows resolve
        self.assertEqual(len(ledger.attempts()), 2)  # NOT collapsed into one row
        retries = ledger.retries()
        self.assertEqual(retries["parent-1"], (retry,))

    def test_coordination_attempts_appear_with_role_coordination(self):
        worker = builders.make_attempt(role=ArmRole.COORDINATION, terminal_state=TerminalState.DELIVERED)
        subject = builders.make_attempt(role=ArmRole.TREATMENT, terminal_state=TerminalState.DELIVERED)
        found = coordination_attempts([worker, subject])
        self.assertEqual(found, (worker,))

    def test_duplicate_attempt_id_raises_accounting_leak(self):
        ledger = AttemptLedger(run_id="run-dup")
        a = builders.make_attempt(attempt_id="dup-1")
        b = builders.make_attempt(attempt_id="dup-1")
        ledger.add(a)
        with self.assertRaises(AccountingLeak):
            ledger.add(b)

    # -- negative control: the naive "success rate over completed attempts"
    #    reporter, and the dropped-coordination-rows fixture -----------------

    def test_naive_completed_attempts_rate_differs_from_correct_scoring_trials(self):
        """T32 negative control: 'success rate over completed attempts', which
        quietly drops faults/cancellations from the denominator. On the 100-row
        fixture this gives 65/80 = 0.8125 -- a different, wrong number from the
        correct per-card scoring-trial accounting this module performs."""
        spec = io.load_json(FIXTURES / "conservation" / "100-attempts.json")
        attempts = builders.attempts_from_conservation_rows(spec["rows"])
        delivered = sum(1 for a in attempts if a.terminal_state is TerminalState.DELIVERED)
        completed = sum(
            1 for a in attempts
            if a.terminal_state in (TerminalState.DELIVERED, TerminalState.INCOMPLETE)
        )
        naive_rate = delivered / completed
        self.assertAlmostEqual(naive_rate, 0.8125)

        denoms = denominators(attempts)
        # the correct accounting figure is a completely different number and
        # a completely different kind of quantity (a trial count, not a rate)
        self.assertNotEqual(denoms.scoring_trials, completed)
        self.assertEqual(denoms.scoring_trials, 79)

    def test_dropped_coordination_rows_break_the_claimed_total(self):
        """T32 negative control, fixture-driven: 5 coordination rows were
        silently collapsed before the ledger was built. A report that still
        claims the original run size (100) is caught because the ledger's own
        accounting denominator (95) disagrees with the claim -- exactly the
        'retries collapsed into their parent, hiding cost' failure mode."""
        spec = io.load_json(FIXTURES / "negative" / "dropped-coordination.json")
        attempts = builders.attempts_from_conservation_rows(spec["rows"])
        ledger = AttemptLedger(run_id="run-dropped")
        for a in attempts:
            ledger.add(a)
        ledger.conserve()  # internally consistent -- the leak is invisible locally

        denoms = denominators(ledger.attempts())
        self.assertEqual(denoms.accounting, spec["expected_actual_total"])
        self.assertNotEqual(denoms.accounting, spec["claimed_total"])

    def test_conservation_identity_100_attempts__negative(self):
        """Catalog sibling (contract §7.4 item 4) for T32. entry.negative_control
        names fixtures/measurement/negative/dropped-coordination.json: this
        must FAIL the conservation identity's own claim (accounting equals the
        claimed total) for the T32 catalog entry to be considered non-vacuous."""
        return self.test_dropped_coordination_rows_break_the_claimed_total()

    # -- REPAIR S-10: conserve()/assert_reconciles() are tautological against
    #    a ledger built by dropping rows before it is ever built; planned_n
    #    is the one external check available inside this lane. ---------------

    def test_conserve_is_tautological_on_a_ledger_missing_rows(self):
        """S-10 repro: drop rows BEFORE building the ledger and conserve() /
        assert_reconciles() still pass, because both re-derive their
        comparison from the very list they check."""
        spec = io.load_json(FIXTURES / "negative" / "dropped-coordination.json")
        attempts = builders.attempts_from_conservation_rows(spec["rows"])
        ledger = AttemptLedger(run_id="run-tautology")
        for a in attempts:
            ledger.add(a)
        ledger.conserve()  # does not raise -- the leak is invisible locally
        denoms = denominators(ledger.attempts())
        denoms.assert_reconciles()  # also does not raise, for the same reason

    def test_planned_n_catches_the_shortfall_conserve_cannot_see(self):
        """The external check: the manifest declared 100 planned trials
        (matching the fixture's own claimed_total) but the ledger only
        accounts for 95 (5 coordination rows were dropped before the ledger
        was built), and no Manifest.skipped entry explains it."""
        spec = io.load_json(FIXTURES / "negative" / "dropped-coordination.json")
        attempts = builders.attempts_from_conservation_rows(spec["rows"])
        ledger = AttemptLedger(run_id="run-planned")
        for a in attempts:
            ledger.add(a)
        denoms = denominators(ledger.attempts())
        planned_n = {"total": spec["claimed_total"]}
        with self.assertRaises(AccountingLeak):
            assert_planned_reconciles(denoms, planned_n, skipped=())

    def test_planned_n_undeclared_is_a_no_op(self):
        """run.py writes planned_n={} today (cross-lane; see the REPAIR
        handoff) -- this must not turn every existing report red."""
        denoms = denominators([])
        assert_planned_reconciles(denoms, {}, skipped=())  # must not raise

    def test_planned_n_matching_accounting_does_not_raise(self):
        spec = io.load_json(FIXTURES / "conservation" / "100-attempts.json")
        attempts = builders.attempts_from_conservation_rows(spec["rows"])
        ledger = AttemptLedger(run_id="run-match")
        for a in attempts:
            ledger.add(a)
        denoms = denominators(ledger.attempts())
        assert_planned_reconciles(denoms, {"total": 100}, skipped=())

    def test_planned_n_shortfall_acknowledged_by_skipped_does_not_raise(self):
        spec = io.load_json(FIXTURES / "negative" / "dropped-coordination.json")
        attempts = builders.attempts_from_conservation_rows(spec["rows"])
        ledger = AttemptLedger(run_id="run-acked")
        for a in attempts:
            ledger.add(a)
        denoms = denominators(ledger.attempts())
        planned_n = {"total": spec["claimed_total"]}
        assert_planned_reconciles(
            denoms, planned_n, skipped=({"id": "cell-x", "reason": "provider outage"},)
        )

    def test_conserve_is_tautological_on_a_ledger_missing_rows__negative(self):
        """Catalog sibling for the S-10 fix: conserve()/assert_reconciles()
        alone must FAIL to catch the same dropped-row shortfall that
        assert_planned_reconciles catches."""
        return self.test_planned_n_catches_the_shortfall_conserve_cannot_see()


# ---------------------------------------------------------------------------
# T33 -- unknown usage is UNKNOWN, never zero
# ---------------------------------------------------------------------------

class UnknownUsagePropagates(unittest.TestCase):
    """T33: an UNKNOWN usage field propagates through sum_usage/cost_of as a
    tracked unknown_count, never silently treated as 0."""

    def _attempts_from_fixture(self):
        spec = io.load_json(FIXTURES / "usage" / "ten-attempts-one-unknown.json")
        model_id = spec["model_id"]
        stratum = builders.Stratum(
            provider=builders.DEFAULT_STRATUM.provider, model=model_id,
            revision=builders.DEFAULT_STRATUM.revision, effort=builders.DEFAULT_STRATUM.effort,
            harness=builders.DEFAULT_STRATUM.harness,
        )
        attempts = []
        for value in spec["output_tokens"]:
            usage = builders.make_usage(
                model_id=model_id,
                output_tokens=(UNKNOWN if value == "UNKNOWN" else value),
            )
            attempts.append(builders.make_attempt(usage=usage, realized=stratum))
        return attempts, spec

    def test_total_is_partial_and_never_understated(self):
        attempts, spec = self._attempts_from_fixture()
        total = sum_usage(attempts, "output_tokens", model_id=spec["model_id"])
        exp = spec["expected"]
        self.assertEqual(total.known, exp["known"])
        self.assertEqual(total.unknown_count, exp["unknown_count"])
        self.assertEqual(total.contributors, exp["contributors"])
        self.assertTrue(total.partial)
        self.assertEqual(total.render(), exp["render"])

    def test_unknown_field_is_not_a_zero(self):
        # UNKNOWN + 1 must raise -- this is what makes T33 impossible to
        # violate by accident (contract §2.2).
        with self.assertRaises(TypeError):
            UNKNOWN + 1  # type: ignore[operator]

    def test_cost_of_renders_not_computed_when_any_cost_is_none(self):
        a = builders.make_attempt(usage=builders.make_usage(cost_usd=1.0))
        b = builders.make_attempt(usage=builders.make_usage(cost_usd=None))
        total = cost_of([a, b], model_id="claude-sonnet-5")
        self.assertIsInstance(total, MoneyTotal)
        self.assertTrue(total.partial)
        self.assertEqual(total.render(), "not computed")

    def test_cost_of_none_on_empty_iterable(self):
        self.assertIsNone(cost_of([], model_id="claude-sonnet-5"))

    def test_cross_model_usage_is_refused(self):
        a = builders.make_attempt(usage=builders.make_usage(model_id="claude-sonnet-5"))
        b = builders.make_attempt(usage=builders.make_usage(model_id="claude-opus-5"))
        with self.assertRaises(CrossModelPoolingRefused):
            sum_usage([a, b], "output_tokens", model_id="claude-sonnet-5")

    # -- negative control: sum(x or 0 for x in tokens) --------------------

    def test_naive_or_zero_sum_understates_and_hides_the_gap(self):
        """T33 negative control: sum(x or 0 for x in tokens) passes every naive
        test and silently reports the exact same number as the correct known
        total, WITHOUT ever surfacing that one contributor's field was
        unknown -- the understatement this backlog item exists to prevent."""
        attempts, spec = self._attempts_from_fixture()
        raw_values = [
            (0 if a.usage.output_tokens is UNKNOWN else a.usage.output_tokens)
            for a in attempts
        ]
        naive_sum = sum(raw_values)
        self.assertEqual(naive_sum, spec["expected"]["known"])  # numerically equal...

        total = sum_usage(attempts, "output_tokens", model_id=spec["model_id"])
        # ...but the correct total additionally flags that it is partial, which
        # a bare naive_sum integer can never do -- that flag is the point.
        self.assertTrue(total.partial)
        self.assertNotEqual(str(naive_sum), total.render())

    def test_total_is_partial_and_never_understated__negative(self):
        """Catalog sibling (contract §7.4 item 4) for T33. entry.negative_control
        names fixtures/measurement/usage/ten-attempts-one-unknown.json: this
        must FAIL the naive sum(x or 0) rendering (it must not equal the
        correct, flagged-partial total) for the T33 catalog entry to be
        considered non-vacuous."""
        return self.test_naive_or_zero_sum_understates_and_hides_the_gap()


if __name__ == "__main__":
    unittest.main()
