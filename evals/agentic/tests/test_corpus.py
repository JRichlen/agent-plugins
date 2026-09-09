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

import hashlib
import functools
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

from evals.agentic.framework import controls, io, validate
from evals.agentic.framework.contract import Card, CardKind, ContractError

REPO_ROOT = io.repo_root()
FIXTURES = REPO_ROOT / "evals" / "agentic" / "fixtures" / "pairing"


def run_verifier(spec: str, workspace: pathlib.Path, *, card_id: str) -> bool:
    """Executes a card's outcome_verifier/adoption_verifier (the
    "path/to/script" form every corpus card uses) against a workspace and
    returns its JSON verdict's "passed" field. Raises if the process
    misbehaves (non-JSON stdout, wrong exit-code convention) rather than
    guessing -- an untrustworthy verifier is a framework defect, not a card
    failure to paper over.

    `card_id` is passed via AGENTIC_CARD_ID. Outcome uses the canonical task
    check; adoption observes this plugin's artifacts. Workspace-written
    guards, hashes, and generic event ledgers cannot choose the criteria."""
    script = REPO_ROOT / spec
    env = dict(os.environ)
    env["AGENTIC_CARD_ID"] = card_id
    proc = subprocess.run(
        [sys.executable, str(script), str(workspace)],
        capture_output=True, text=True, env=env,
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


@functools.lru_cache(maxsize=1)
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
                pass_outcome = run_verifier(card.outcome_verifier, pass_ws, card_id=card.card_id)
                pass_adoption = run_verifier(card.adoption_verifier, pass_ws, card_id=card.card_id)
                fail_outcome = run_verifier(card.outcome_verifier, fail_ws, card_id=card.card_id)
                fail_adoption = run_verifier(card.adoption_verifier, fail_ws, card_id=card.card_id)

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
        outcome_twice = run_verifier(card.outcome_verifier, pass_ws, card_id=card.card_id)
        adoption_twice = run_verifier(card.adoption_verifier, pass_ws, card_id=card.card_id)
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

                pass_outcome = run_verifier(card.outcome_verifier, pass_ws, card_id=card.card_id)
                pass_adoption = run_verifier(card.adoption_verifier, pass_ws, card_id=card.card_id)
                fail_outcome = run_verifier(card.outcome_verifier, fail_ws, card_id=card.card_id)
                fail_adoption = run_verifier(card.adoption_verifier, fail_ws, card_id=card.card_id)

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
        outcome = run_verifier(card.outcome_verifier, pass_ws, card_id=card.card_id)
        naive_inverted_rule = not outcome
        self.assertFalse(
            naive_inverted_rule,
            "the naive 'positive verifier inverted' rule wrongly rejects a correct "
            "oracle-direct solution -- this is exactly the trap T13 names",
        )
        # ...while the real rule (outcome AND NOT adoption) correctly accepts it.
        adoption = run_verifier(card.adoption_verifier, pass_ws, card_id=card.card_id)
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

                pass_outcome = run_verifier(card.outcome_verifier, pass_ws, card_id=card.card_id)
                fail_outcome = run_verifier(card.outcome_verifier, fail_ws, card_id=card.card_id)
                near_fail_outcome = run_verifier(card.outcome_verifier, near_fail_ws, card_id=card.card_id)

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
        real_outcome = run_verifier(card.outcome_verifier, near_fail_ws, card_id=card.card_id)
        self.assertFalse(real_outcome, "the real verifier must reject this adjacent behavior")


class VerifierBinding(unittest.TestCase):
    """CV-01/CV-02/CV-03/CV-04: the shared generic verifiers must bind their
    check/digest to the CARD being graded, resolved from this repo's own
    committed fixtures/pass/guard.sh -- never trust anything the subject
    workspace itself supplies, and never require the subject workspace to
    carry scaffolding no task prompt discloses."""

    def _isolated(self, tmp: str) -> pathlib.Path:
        ws = pathlib.Path(tmp) / "ws"
        ws.mkdir()
        return ws

    def test_forged_workspace_guard_cannot_force_an_outcome_pass(self):
        """CV-01's exact reproduction: a workspace supplies its own guard.sh
        carrying a trivially-true check. The real graveyard-pos-01 check
        (a diff against the real plugin's script output) must still be the
        one that executes, and it must fail against an empty workspace."""
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._isolated(tmp)
            (ws / "guard.sh").write_text("#!/usr/bin/env bash\ntrue  # GUARD_CHECK\n")
            passed = run_verifier(
                "evals/agentic/tasks/_verifiers/verify_outcome.py", ws, card_id="graveyard-pos-01",
            )
            self.assertFalse(passed, "a forged workspace guard.sh must not be able to force a pass")

    def test_forged_workspace_guard_cannot_force_an_outcome_pass__negative(self):
        """Negative control: the SAME forged guard.sh, called with the OLD
        (pre-repair) trust model of 'whatever's in the workspace IS the
        check', would pass -- demonstrating the forgery this binding
        closes, not just asserting the new behavior in isolation."""
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._isolated(tmp)
            (ws / "guard.sh").write_text("#!/usr/bin/env bash\ntrue  # GUARD_CHECK\n")
            naive_proc = subprocess.run(
                ["bash", "-c", "true"], cwd=ws, capture_output=True,
            )
            self.assertEqual(
                naive_proc.returncode, 0,
                "the forged line itself is trivially-true -- confirms the forgery would have "
                "worked under a verifier that trusted the workspace's own guard.sh",
            )

    def test_copied_fixture_from_another_card_fails_this_cards_verifiers(self):
        """CV-04: copying a DIFFERENT card's entire pass fixture verbatim
        must not satisfy this card's outcome/adoption verifiers -- the
        verdict must depend on card identity, not on what files happen to
        be sitting in the workspace."""
        donor = next(c for c in all_cards() if c.card_id == "stop-rule-pos-01")
        victim_id = "voice-pos-01"
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._isolated(tmp)
            shutil.copytree(REPO_ROOT / donor.pass_fixture, ws, dirs_exist_ok=True)
            outcome = run_verifier(donor.outcome_verifier, ws, card_id=victim_id)
            adoption = run_verifier(donor.adoption_verifier, ws, card_id=victim_id)
            self.assertFalse(outcome, "a donor card's pass fixture must not pass a different card's outcome check")
            self.assertFalse(adoption, "a donor card's pass fixture must not pass a different card's adoption check")

    def test_copied_fixture_from_another_card_fails_this_cards_verifiers__negative(self):
        """Negative control: the SAME donor fixture, graded as ITS OWN card
        (not the victim's), passes -- proving the rejection above is about
        card identity, not that the donor fixture is simply broken."""
        donor = next(c for c in all_cards() if c.card_id == "stop-rule-pos-01")
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._isolated(tmp)
            shutil.copytree(REPO_ROOT / donor.pass_fixture, ws, dirs_exist_ok=True)
            outcome = run_verifier(donor.outcome_verifier, ws, card_id=donor.card_id)
            self.assertTrue(outcome, "graded as its own card, the donor's pass fixture must still pass")

    def test_honest_direct_solution_passes_outcome_with_no_disclosed_scaffolding(self):
        """CV-02's outcome half: a correct direct solution to graveyard-pos-01's
        actual task -- produce delete-originals.sh, per its README, which
        never mentions guard.sh or events.jsonl -- must pass the outcome
        verifier. It is graded purely on its own deliverable file; the
        harness-owned guard.sh check is resolved from the repo, not required
        to already exist in the agent's workspace."""
        card = next(c for c in all_cards() if c.card_id == "graveyard-pos-01")
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._isolated(tmp)
            self.assertNotIn(
                "guard.sh", (REPO_ROOT / card.task_path / "README.md").read_text(),
                "sanity: the task prompt genuinely does not mention the grading scaffolding",
            )
            script = REPO_ROOT / "plugins/graveyard/skills/graveyard/scripts/generate-delete-script.sh"
            proc = subprocess.run(
                ["bash", str(script), "acme", "graveyard", "--bundled", "old-tool", "--unbundled", "empty-scratch"],
                capture_output=True, text=True, check=True,
            )
            (ws / "delete-originals.sh").write_text(proc.stdout)
            outcome = run_verifier(card.outcome_verifier, ws, card_id=card.card_id)
            self.assertTrue(outcome, "a correct direct solution must pass outcome grading (handoff requirement)")

    def test_honest_direct_solution_passes_outcome_with_no_disclosed_scaffolding__negative(self):
        """Negative control: an INCORRECT direct solution (wrong flags, so the
        generated script differs from the reference) must still fail --
        proving the pass above is about matching the real deliverable, not
        that the outcome check has been made vacuously permissive."""
        card = next(c for c in all_cards() if c.card_id == "graveyard-pos-01")
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._isolated(tmp)
            (ws / "delete-originals.sh").write_text("#!/usr/bin/env bash\necho wrong\n")
            outcome = run_verifier(card.outcome_verifier, ws, card_id=card.card_id)
            self.assertFalse(outcome, "an incorrect deliverable must still fail outcome grading")

    def test_forged_adoption_digest_bound_to_canonical_guard(self):
        """CV-03: a workspace that forges its OWN guard.sh and then hashes
        that same forged file for events.jsonl's pinned digest must not
        pass adoption -- the expected digest is this card's canonical,
        repo-committed guard.sh, not whatever the workspace supplies."""
        card = next(c for c in all_cards() if c.card_id == "graveyard-pos-01")
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._isolated(tmp)
            (ws / "guard.sh").write_text("#!/usr/bin/env bash\nfalse  # GUARD_CHECK\n")
            forged_digest = hashlib.sha256((ws / "guard.sh").read_bytes()).hexdigest()
            (ws / "events.jsonl").write_text(
                json.dumps({"at": 1, "op": "backup", "digest": forged_digest}) + "\n"
                + json.dumps({"at": 2, "op": "delete"}) + "\n"
            )
            adoption = run_verifier(card.adoption_verifier, ws, card_id=card.card_id)
            self.assertFalse(adoption, "a self-consistent forged digest must not satisfy adoption")

    def test_forged_adoption_digest_bound_to_canonical_guard__negative(self):
        """A real reviewable script shows artifact adoption without a ledger.
        The counterexample to a forged digest is actual work, not a better
        forged digest. No deletion needs to occur in the user's session.
        """
        card = next(c for c in all_cards() if c.card_id == "graveyard-pos-01")
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._isolated(tmp)
            shutil.copy(REPO_ROOT / card.pass_fixture / "delete-originals.sh", ws / "delete-originals.sh")
            adoption = run_verifier(card.adoption_verifier, ws, card_id=card.card_id)
            self.assertTrue(adoption, "a reviewable script is observable work without a fictional deletion ledger")


class EvidenceManifestBinding(unittest.TestCase):
    """CV-04 (evidence/manifest.json half): stop-rule's three cards are this
    delivery's one worked plugin -- each carries a real evidence/
    manifest.json (tasks/_verifiers/generate_evidence_manifest.py), and
    copying a donor fixture's ENTIRE directory (evidence/ included, exactly
    the CV-04 attack shape one level up) into a different card's fixture
    slot must be caught: the manifest still names the donor's card_id, not
    the victim's. Cards with no evidence/ directory yet are the recorded
    known-gaps.md remainder and are untouched by this class."""

    def test_stop_rule_fixtures_carry_a_current_evidence_manifest(self):
        for card_id in ("stop-rule-pos-01", "stop-rule-near-01", "stop-rule-neg-01"):
            card = next(c for c in all_cards() if c.card_id == card_id)
            with self.subTest(card=card_id, fixture="pass"):
                self.assertFalse(
                    controls.detect_forged_fixture_evidence(card_id, REPO_ROOT / card.pass_fixture)
                )
            with self.subTest(card=card_id, fixture="fail"):
                self.assertFalse(
                    controls.detect_forged_fixture_evidence(card_id, REPO_ROOT / card.fail_fixture)
                )

    def test_evidence_copied_from_a_donor_card_is_detected_as_forged(self):
        """CV-04's exact repro, one layer down: copy stop-rule-pos-01's
        ENTIRE pass fixture -- including its evidence/manifest.json -- into
        a temp directory and check it AS a different card. The manifest
        still says card_id=stop-rule-pos-01, so the victim card_id must be
        flagged as forged, and validate_card (loading a card.json pointed
        at this contaminated directory) must refuse to load it."""
        donor = next(c for c in all_cards() if c.card_id == "stop-rule-pos-01")
        victim_id = "voice-pos-01"
        with tempfile.TemporaryDirectory() as tmp:
            ws = pathlib.Path(tmp) / "contaminated-fixture"
            shutil.copytree(REPO_ROOT / donor.pass_fixture, ws)
            self.assertTrue(
                controls.detect_forged_fixture_evidence(victim_id, ws),
                "a donor card's evidence manifest, read under a different card_id, must be forged",
            )
            with self.assertRaises(ContractError):
                controls.assert_fixture_evidence_current(victim_id, ws)

    def test_evidence_copied_from_a_donor_card_is_detected_as_forged__negative(self):
        """Negative control: the SAME copied directory, checked under the
        donor's OWN card_id, is current -- proving the detection above is
        about card identity, not that the copy itself corrupted anything."""
        donor = next(c for c in all_cards() if c.card_id == "stop-rule-pos-01")
        with tempfile.TemporaryDirectory() as tmp:
            ws = pathlib.Path(tmp) / "copied-fixture"
            shutil.copytree(REPO_ROOT / donor.pass_fixture, ws)
            self.assertFalse(controls.detect_forged_fixture_evidence(donor.card_id, ws))
            controls.assert_fixture_evidence_current(donor.card_id, ws)  # must not raise

    def test_stale_content_with_an_unregenerated_manifest_is_detected(self):
        """A fixture whose content changed after the manifest was generated
        (regardless of card_id) must also be caught -- not just a wrong
        card_id, but any drift between the manifest and the fixture it
        claims to describe."""
        donor = next(c for c in all_cards() if c.card_id == "stop-rule-pos-01")
        with tempfile.TemporaryDirectory() as tmp:
            ws = pathlib.Path(tmp) / "drifted-fixture"
            shutil.copytree(REPO_ROOT / donor.pass_fixture, ws)
            (ws / "guard.sh").write_text("#!/usr/bin/env bash\necho tampered\n")
            self.assertTrue(controls.detect_forged_fixture_evidence(donor.card_id, ws))

    def test_every_real_corpus_fixture_carries_a_current_evidence_manifest(self):
        """The rollout is complete (known-gaps.md, CV-04, closed 2026-09-07):
        every card's pass AND fail fixture must carry an evidence/manifest.json
        that is bound to that card and current for that fixture's content.
        A missing manifest on a real corpus fixture is a regression, not a
        phase."""
        missing = []
        for card in all_cards():
            for fx in (card.pass_fixture, card.fail_fixture):
                fixture_dir = REPO_ROOT / fx
                if not (fixture_dir / "evidence" / "manifest.json").is_file():
                    missing.append(f"{card.card_id}: {fx}")
                    continue
                self.assertFalse(
                    controls.detect_forged_fixture_evidence(card.card_id, fixture_dir),
                    f"{card.card_id}: {fx} manifest is not current for its content",
                )
                controls.assert_fixture_evidence_current(card.card_id, fixture_dir)
        self.assertEqual(missing, [], f"fixtures without an evidence manifest: {missing}")

    def test_a_fixture_with_no_evidence_directory_is_not_flagged(self):
        """Opt-in semantics are still the detector's contract for NON-corpus
        directories (a scratch workspace, a fixture under construction): the
        absence of an evidence/ directory is 'nothing to check', never
        'forged'. Exercised on a temp copy so the real corpus stays complete."""
        card = next(c for c in all_cards() if c.card_id == "graveyard-pos-01")
        with tempfile.TemporaryDirectory() as tmp:
            ws = pathlib.Path(tmp) / "no-evidence"
            shutil.copytree(REPO_ROOT / card.pass_fixture, ws)
            shutil.rmtree(ws / "evidence")
            self.assertFalse((ws / "evidence").exists())
            self.assertFalse(controls.detect_forged_fixture_evidence(card.card_id, ws))
            controls.assert_fixture_evidence_current(card.card_id, ws)  # must not raise

    def test_a_fixture_with_no_evidence_directory_is_not_flagged__negative(self):
        """The same temp copy with a manifest belonging to ANOTHER card is
        flagged: presence of a wrong manifest, not absence, is the defect."""
        card = next(c for c in all_cards() if c.card_id == "graveyard-pos-01")
        donor = next(c for c in all_cards() if c.card_id == "stop-rule-pos-01")
        with tempfile.TemporaryDirectory() as tmp:
            ws = pathlib.Path(tmp) / "wrong-manifest"
            shutil.copytree(REPO_ROOT / card.pass_fixture, ws)
            shutil.copy(REPO_ROOT / donor.pass_fixture / "evidence" / "manifest.json", ws / "evidence" / "manifest.json")
            self.assertTrue(controls.detect_forged_fixture_evidence(card.card_id, ws))

if __name__ == "__main__":
    unittest.main()
