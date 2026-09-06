"""Core-lane tests for evals.agentic.framework.classify (T02, T03).

Every row of fixtures/classify/truth-table.json is exercised as its own
sub-test (generated from the fixture, so the test count tracks the table),
plus dedicated negative-control tests proving the classifier cannot degenerate
into a naive `else: return FAULT` tail or a blanket "any transport_error is a
fault" rule.
"""
from __future__ import annotations

import unittest

from evals.agentic.framework.classify import (
    RunFacts,
    TruthRow,
    classify,
    counts_as_fault,
    counts_in_accounting,
    counts_in_scoring,
    facts_digest,
    load_truth_table,
)
from evals.agentic.framework.contract import ContractError, TerminalState, UnclassifiableRun

TRUTH_TABLE: tuple[TruthRow, ...] = load_truth_table()


def _facts(**overrides) -> RunFacts:
    base = dict(
        exit_status=0, signalled=None, deliverable_present=False,
        verifier_verdict=None, verifier_green_at_ms=None, cancel_issued_at_ms=None,
        wall_clock_ms=1000, wall_clock_limit_ms=60000, transport_error=None, bytes_out=0,
    )
    base.update(overrides)
    return RunFacts(**base)


def _slug(text: str) -> str:
    out = []
    for ch in text.lower():
        out.append(ch if ch.isalnum() else "_")
    slug = "".join(out).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug[:60]


class TerminalStateTruthTable(unittest.TestCase):
    """T02: every row of the truth table produces its expected state.

    One real test method per row is generated below the class body (not a
    subTest loop) so the discovered test COUNT itself is >= the number of
    truth-table rows, per the §8.1 acceptance line, and a single bad row
    shows up as its own named failure rather than folding into one bit."""

    def test_truth_table_loads_and_is_nonempty(self):
        self.assertGreater(len(TRUTH_TABLE), 0)

    def test_negative_control_naive_isinstance_check_is_vacuous(self):
        """A test that only checks classify() returns a TerminalState member
        (any member) would pass a classifier that always returns FAULT. Prove
        the real assertion actually discriminates by state, not just by type."""
        states_seen = {classify(row.facts) for row in TRUTH_TABLE}
        self.assertGreater(
            len(states_seen), 1,
            "the truth table must exercise more than one terminal state, or "
            "a constant-returning classifier would pass every row",
        )

    def test_transport_crash_with_zero_output_is_fault_not_incomplete(self):
        """T02's named negative control, independent of the JSON fixture."""
        facts = _facts(exit_status=None, transport_error="reset by peer", bytes_out=0)
        self.assertEqual(classify(facts), TerminalState.FAULT)
        self.assertNotEqual(classify(facts), TerminalState.INCOMPLETE)

    def test_transport_crash_with_zero_output_is_fault_not_incomplete__negative(self):
        """Catalog sibling (contract §7.4 item 4) for T02. entry.negative_control
        names fixtures/classify/truth-table.json's own
        'transport-error-with-output-is-not-automatically-fault' row: the
        rule is specifically zero-byte transport failures, and this must
        correctly NOT classify that row as fault."""
        return self.test_transport_error_with_nonzero_output_is_not_automatically_fault()

    def test_timeout_after_delivery_is_not_fault(self):
        """T03, as a fixed-name method independent of the dynamically
        generated per-row tests below (whose names depend on fixture note
        text and are therefore unstable as a catalog anchor)."""
        facts = _facts(
            exit_status=None, signalled="SIGKILL", deliverable_present=True,
            verifier_verdict=True, verifier_green_at_ms=45000,
            wall_clock_ms=60050, wall_clock_limit_ms=60000, bytes_out=2048,
        )
        self.assertEqual(classify(facts), TerminalState.TIMEOUT_AFTER_DELIVERY)
        self.assertFalse(counts_as_fault(classify(facts)))

    def test_timeout_after_delivery_is_not_fault__negative(self):
        """Catalog sibling (contract §7.4 item 4) for T03. entry.negative_control
        names fixtures/classify/truth-table.json's own boundary rows: a
        deliverable with no verified-green timestamp must NOT be upgraded to
        timeout-after-delivery -- it must classify FAULT."""
        facts = _facts(
            exit_status=None, signalled="SIGKILL", deliverable_present=True,
            verifier_verdict=None, verifier_green_at_ms=None,
            wall_clock_ms=60050, wall_clock_limit_ms=60000, bytes_out=2048,
        )
        self.assertEqual(classify(facts), TerminalState.FAULT)
        self.assertNotEqual(classify(facts), TerminalState.TIMEOUT_AFTER_DELIVERY)

    def test_user_cancel_is_never_classified_as_fault(self):
        """T02's other named negative control: a user stop must not launder
        into an infrastructure excuse, even when the process also looks like
        a transport failure."""
        facts = _facts(
            exit_status=None, signalled="SIGTERM", cancel_issued_at_ms=100, wall_clock_ms=150,
            transport_error="connection reset by peer", bytes_out=0,
        )
        self.assertEqual(classify(facts), TerminalState.CANCELLED)
        self.assertNotEqual(classify(facts), TerminalState.FAULT)

    def test_transport_error_with_nonzero_output_is_not_automatically_fault(self):
        """Negative control: the FAULT rule is specifically zero-byte
        transport failures. A classifier that treats ANY transport_error
        string as fault regardless of bytes_out would wrongly red this."""
        facts = _facts(
            deliverable_present=True, verifier_verdict=True, verifier_green_at_ms=10,
            wall_clock_ms=20, transport_error="flaky blip, recovered", bytes_out=500,
        )
        self.assertEqual(classify(facts), TerminalState.DELIVERED)

    def test_unclassifiable_combination_raises_rather_than_defaulting(self):
        """T02: 'a combination absent from the table raises UnclassifiableRun
        rather than defaulting.' A genuinely contradictory fact combination
        (a verified-green timestamp with no deliverable to have verified) has
        no sensible terminal state and must raise, not fall through to some
        default."""
        contradictory = _facts(deliverable_present=False, verifier_green_at_ms=500, verifier_verdict=True)
        with self.assertRaises(UnclassifiableRun):
            classify(contradictory)

    def test_second_unclassifiable_combination_both_exit_and_signal(self):
        contradictory = _facts(exit_status=0, signalled="SIGKILL")
        with self.assertRaises(UnclassifiableRun):
            classify(contradictory)

    def test_negative_control_a_default_fault_tail_would_pass_naive_tests_but_fails_here(self):
        """Directly demonstrates the backlog's named defect: a classifier
        with an `else: return FAULT` tail would return FAULT for the
        DELIVERED and INCOMPLETE rows below. The real classifier must not."""
        delivered_facts = _facts(exit_status=0, deliverable_present=True, wall_clock_ms=10)
        incomplete_facts = _facts(exit_status=0, deliverable_present=False, wall_clock_ms=10)
        self.assertEqual(classify(delivered_facts), TerminalState.DELIVERED)
        self.assertEqual(classify(incomplete_facts), TerminalState.INCOMPLETE)
        self.assertNotEqual(classify(delivered_facts), TerminalState.FAULT)
        self.assertNotEqual(classify(incomplete_facts), TerminalState.FAULT)


def _make_row_test(index: int, row: TruthRow):
    def _test(self):
        self.assertEqual(
            classify(row.facts), row.expected,
            f"row {index} ({row.note!r}): expected {row.expected}, got {classify(row.facts)}",
        )
    _test.__doc__ = f"truth-table row {index}: {row.note}"
    return _test


for _i, _row in enumerate(TRUTH_TABLE):
    _name = f"test_row_{_i:02d}_{_slug(_row.note) or _row.expected.value}"
    setattr(TerminalStateTruthTable, _name, _make_row_test(_i, _row))
del _i, _row


class ClassifyHelpers(unittest.TestCase):
    def test_counts_as_fault_only_true_for_fault(self):
        for state in TerminalState:
            self.assertEqual(counts_as_fault(state), state is TerminalState.FAULT)

    def test_counts_in_scoring_matches_scoring_valid_states(self):
        self.assertTrue(counts_in_scoring(TerminalState.DELIVERED))
        self.assertTrue(counts_in_scoring(TerminalState.INCOMPLETE))
        self.assertTrue(counts_in_scoring(TerminalState.TIMEOUT_AFTER_DELIVERY))
        self.assertFalse(counts_in_scoring(TerminalState.FAULT))
        self.assertFalse(counts_in_scoring(TerminalState.CANCELLED))

    def test_counts_in_accounting_is_always_true(self):
        """Negative control for T32/accounting-leak style bugs: a classifier
        helper that excludes any state from accounting would let a reporter
        silently drop attempts from its denominator."""
        for state in TerminalState:
            self.assertTrue(counts_in_accounting(state))

    def test_facts_digest_is_stable_and_content_sensitive(self):
        a = _facts(wall_clock_ms=10)
        b = _facts(wall_clock_ms=10)
        c = _facts(wall_clock_ms=11)
        self.assertEqual(facts_digest(a), facts_digest(b))
        self.assertNotEqual(facts_digest(a), facts_digest(c))


class RunFactsRoundTrip(unittest.TestCase):
    def test_from_dict_rejects_unknown_key(self):
        good = _facts().to_dict()
        RunFacts.from_dict(good)  # sanity
        bad = dict(good, extra="nope")
        with self.assertRaises(ContractError):
            RunFacts.from_dict(bad)

    def test_from_dict_rejects_missing_key(self):
        good = _facts().to_dict()
        del good["bytes_out"]
        with self.assertRaises(ContractError):
            RunFacts.from_dict(good)


if __name__ == "__main__":
    unittest.main()
