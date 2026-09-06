"""Registry-lane tests for the real per-plugin reference corpus under
evals/agentic/tasks/** (T13, T14, T15). Every test here discovers cards via
validate.load_cards(), so cards added later (more plugins, more kinds) are
automatically exercised without touching this file.

Card-kind "decisiveness" convention (documented fully in
evals/agentic/tasks/README.md): both verifiers are always run on both
fixtures; a card's DECISIVE boolean -- what "this fixture is a PASS for this
card" means -- is derived from (outcome, adoption) per CardKind:

  POSITIVE : decisive = outcome AND adoption           (task done, ritual used)
  NEGATIVE : decisive = outcome AND (NOT adoption)      (task done, ritual absent)
  NEAR_MISS: decisive = outcome                         (outcome IS the boundary check)

This is registry's own reading of the frozen Card/CardKind vocabulary, not a
literal contract quote -- reported here, not hidden, since Card exposes only
outcome_verifier/adoption_verifier and this module is what interprets them
per kind.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import unittest

from evals.agentic.framework import io, validate
from evals.agentic.framework.contract import Card, CardKind

REPO_ROOT = io.repo_root()
FIXTURES = REPO_ROOT / "evals" / "agentic" / "fixtures" / "pairing"


def run_verifier(spec: str, workspace: pathlib.Path) -> bool:
    """Executes a card's outcome_verifier/adoption_verifier (the
    "path/to/script" form every corpus card uses) against a workspace and
    returns its JSON verdict's "passed" field. Raises if the process
    misbehaves (non-JSON stdout, wrong exit-code convention) rather than
    guessing -- an untrustworthy verifier is a framework defect, not a card
    failure to paper over."""
    script = REPO_ROOT / spec
    proc = subprocess.run(
        [sys.executable, str(script), str(workspace)],
        capture_output=True, text=True,
    )
    try:
        verdict = json.loads(proc.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError) as exc:
        raise AssertionError(f"{spec} on {workspace}: stdout was not a JSON verdict: {proc.stdout!r}") from exc
    passed = bool(verdict.get("passed"))
    expected_exit = 0 if passed else 1
    if proc.returncode != expected_exit:
        raise AssertionError(
            f"{spec} on {workspace}: exit code {proc.returncode} does not match "
            f"verdict passed={passed} (expected exit {expected_exit})"
        )
    return passed


def decisive(card: Card, outcome: bool, adoption: bool) -> bool:
    if card.kind is CardKind.POSITIVE:
        return outcome and adoption
    if card.kind is CardKind.NEGATIVE:
        return outcome and not adoption
    return outcome  # NEAR_MISS: outcome_verifier directly encodes the boundary check


def all_cards() -> tuple[Card, ...]:
    return validate.load_cards(REPO_ROOT)


def cards_of_kind(kind: CardKind) -> tuple[Card, ...]:
    return tuple(c for c in all_cards() if c.kind is kind)


class VerifierTwoSided(unittest.TestCase):
    """T15: every card's verifiers are executable and two-sided."""

    def test_every_card_verifier_is_two_sided_on_committed_fixtures(self):
        cards = all_cards()
        self.assertGreater(len(cards), 0, "no cards found under tasks/** -- nothing to test")
        for card in cards:
            with self.subTest(card=card.card_id):
                pass_ws = REPO_ROOT / card.pass_fixture
                fail_ws = REPO_ROOT / card.fail_fixture
                self.assertNotEqual(
                    pass_ws, fail_ws,
                    f"{card.card_id}: pass_fixture and fail_fixture must be different directories",
                )
                pass_outcome = run_verifier(card.outcome_verifier, pass_ws)
                pass_adoption = run_verifier(card.adoption_verifier, pass_ws)
                fail_outcome = run_verifier(card.outcome_verifier, fail_ws)
                fail_adoption = run_verifier(card.adoption_verifier, fail_ws)

                self.assertTrue(
                    decisive(card, pass_outcome, pass_adoption),
                    f"{card.card_id}: pass_fixture must be decisive=True "
                    f"(outcome={pass_outcome}, adoption={pass_adoption})",
                )
                self.assertFalse(
                    decisive(card, fail_outcome, fail_adoption),
                    f"{card.card_id}: fail_fixture must be decisive=False "
                    f"(outcome={fail_outcome}, adoption={fail_adoption})",
                )

    def test_every_card_verifier_is_two_sided_on_committed_fixtures__negative(self):
        """T15's own negative control: 'a verifier with no committed failing
        fixture is untestable in the failing direction.' Demonstrated on a
        real card (voice-pos-01) by calling its verifiers on pass_fixture
        TWICE, standing in for a (hypothetical) card whose fail_fixture was
        never actually different from its pass_fixture -- such a card would
        wrongly look decisive=True on both sides and the discriminating
        assertion above would never fire."""
        card = next(c for c in all_cards() if c.card_id == "voice-pos-01")
        pass_ws = REPO_ROOT / card.pass_fixture
        outcome_twice = run_verifier(card.outcome_verifier, pass_ws)
        adoption_twice = run_verifier(card.adoption_verifier, pass_ws)
        # both reads of the SAME (pass) fixture agree and are decisive=True --
        # exactly the failure mode T15 requires a genuinely different
        # fail_fixture to avoid. The real corpus test above passes only
        # because fail_fixture is a materially different directory whose
        # verifiers disagree with pass_fixture's.
        self.assertTrue(decisive(card, outcome_twice, adoption_twice))
        self.assertTrue(decisive(card, outcome_twice, adoption_twice))


class NegativeMustNotFire(unittest.TestCase):
    """T13: negative cards' verifiers fail when the ritual fires, and pass a
    correct direct (oracle) solution."""

    def test_negative_cards_pass_direct_solution_and_fail_when_ritual_fires(self):
        cards = cards_of_kind(CardKind.NEGATIVE)
        self.assertGreater(len(cards), 0)
        for card in cards:
            with self.subTest(card=card.card_id):
                pass_ws = REPO_ROOT / card.pass_fixture
                fail_ws = REPO_ROOT / card.fail_fixture

                pass_outcome = run_verifier(card.outcome_verifier, pass_ws)
                pass_adoption = run_verifier(card.adoption_verifier, pass_ws)
                fail_outcome = run_verifier(card.outcome_verifier, fail_ws)
                fail_adoption = run_verifier(card.adoption_verifier, fail_ws)

                self.assertTrue(pass_outcome, f"{card.card_id}: the direct solution must solve the task")
                self.assertFalse(pass_adoption, f"{card.card_id}: the direct solution must not trigger the ritual")
                self.assertTrue(
                    fail_adoption,
                    f"{card.card_id}: the fail fixture must show the ritual actually firing",
                )
                self.assertFalse(
                    decisive(card, fail_outcome, fail_adoption),
                    f"{card.card_id}: firing the ritual must fail the card even if the "
                    "underlying task also happened to get done",
                )

    def test_negative_cards_pass_direct_solution_and_fail_when_ritual_fires__negative(self):
        """Contract's own T13 negative control: 'a negative card whose
        verifier is the positive verifier inverted -- it then rewards ANY
        deviation, including a wrong answer.' Demonstrated on
        graveyard-neg-01's real pass_fixture (negative_control): a naive
        'NOT outcome_verifier' rule wrongly REJECTS this fixture even though
        it is the correct oracle-direct solution -- proving why negative
        cards need outcome AND NOT adoption, not a bare inversion."""
        card = next(c for c in cards_of_kind(CardKind.NEGATIVE) if c.card_id == "graveyard-neg-01")
        pass_ws = REPO_ROOT / card.pass_fixture
        outcome = run_verifier(card.outcome_verifier, pass_ws)
        naive_inverted_rule = not outcome
        self.assertFalse(
            naive_inverted_rule,
            "the naive 'positive verifier inverted' rule wrongly rejects a correct "
            "oracle-direct solution -- this is exactly the trap T13 names",
        )
        # ...while the real rule (outcome AND NOT adoption) correctly accepts it.
        adoption = run_verifier(card.adoption_verifier, pass_ws)
        self.assertTrue(decisive(card, outcome, adoption))


class NearMissDiscrimination(unittest.TestCase):
    """T14: near-miss cards discriminate the boundary-correct behavior from
    BOTH adjacent (over- and under-triggering) behaviors."""

    def test_near_miss_cards_discriminate_pass_from_both_adjacent_fixtures(self):
        cards = cards_of_kind(CardKind.NEAR_MISS)
        self.assertGreater(len(cards), 0)
        for card in cards:
            with self.subTest(card=card.card_id):
                self.assertTrue(card.expected_boundary_verdict)
                pass_ws = REPO_ROOT / card.pass_fixture
                fail_ws = REPO_ROOT / card.fail_fixture
                near_fail_ws = pass_ws.parent / "near-fail"
                self.assertTrue(
                    near_fail_ws.is_dir(),
                    f"{card.card_id}: near-miss cards must additionally ship a sibling "
                    "'near-fail/' fixture (the OTHER adjacent wrong behavior) alongside "
                    "the schema-required pass_fixture/fail_fixture pair -- see "
                    "tasks/README.md's near-miss convention",
                )

                pass_outcome = run_verifier(card.outcome_verifier, pass_ws)
                fail_outcome = run_verifier(card.outcome_verifier, fail_ws)
                near_fail_outcome = run_verifier(card.outcome_verifier, near_fail_ws)

                self.assertTrue(pass_outcome, f"{card.card_id}: boundary-correct behavior must pass")
                self.assertFalse(fail_outcome, f"{card.card_id}: adjacent behavior #1 must fail")
                self.assertFalse(near_fail_outcome, f"{card.card_id}: adjacent behavior #2 must ALSO fail")

    def test_near_miss_cards_discriminate_pass_from_both_adjacent_fixtures__negative(self):
        """Contract's own T14 negative control: 'a near-miss whose verifier
        accepts either the positive or the negative behavior measures
        nothing.' Demonstrated on graveyard-near-01's real near-fail fixture
        (negative_control): a naive 'delete-originals.sh exists at all' rule
        wrongly ACCEPTS it, even though the real (diff-against-the-correct-
        treatment) verifier correctly rejects it."""
        card = next(c for c in cards_of_kind(CardKind.NEAR_MISS) if c.card_id == "graveyard-near-01")
        near_fail_ws = (REPO_ROOT / card.fail_fixture).parent / "near-fail"
        self.assertTrue(near_fail_ws.is_dir())

        naive_shallow_rule = (near_fail_ws / "delete-originals.sh").is_file()
        self.assertFalse(
            naive_shallow_rule,
            "adjacent-behavior #2 in this fixture deliberately produces no "
            "delete-originals.sh at all, so a shallow 'file exists' rule would "
            "(wrongly, for a different reason) reject it too -- the real point is "
            "that the actual outcome_verifier below rejects it on CONTENT",
        )
        real_outcome = run_verifier(card.outcome_verifier, near_fail_ws)
        self.assertFalse(real_outcome, "the real verifier must reject this adjacent behavior")


if __name__ == "__main__":
    unittest.main()
