"""The wave-research grader rejects rounded-up theses and accepts legitimate ones.

The check script is run directly (no sandbox) on a candidate ``thesis.md`` the
way the card's guard runs it: inputs from the card's ``task/`` directory, the
candidate in the working directory.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
TASKS = ROOT / "evals/agentic/tasks/wave-research"
CHECK = ROOT / "evals/agentic/tasks/_verifiers/check_wave_research.py"
ADOPT = ROOT / "evals/agentic/tasks/_verifiers/verify_adoption.py"
POS, NEAR, NEG = "wave-research-pos-01", "wave-research-near-01", "wave-research-neg-01"


def fixture(card, kind):
    return (TASKS / card / "fixtures" / kind / "thesis.md").read_text()


def grade(card, text, inputs=None):
    """True when the card's check script accepts ``text`` as thesis.md."""
    with tempfile.TemporaryDirectory() as tmp:
        (pathlib.Path(tmp) / "thesis.md").write_text(text)
        env = {**os.environ, "AGENTIC_CARD_ID": card, "AGENTIC_INPUTS": str(inputs or TASKS / card / "task")}
        return subprocess.run([sys.executable, "-I", str(CHECK)], cwd=tmp, env=env,
                              capture_output=True, text=True).returncode == 0


def adopted(card, text):
    with tempfile.TemporaryDirectory() as tmp:
        (pathlib.Path(tmp) / "thesis.md").write_text(text)
        env = {**os.environ, "AGENTIC_CARD_ID": card}
        return subprocess.run([sys.executable, str(ADOPT), tmp], env=env, capture_output=True, text=True).returncode == 0


def with_inputs(edit):
    """A temp copy of the pos card's evidence.json after ``edit(data)``; returns the TemporaryDirectory."""
    tmp = tempfile.TemporaryDirectory()
    data = json.loads((TASKS / POS / "task/evidence.json").read_text())
    edit(data)
    (pathlib.Path(tmp.name) / "evidence.json").write_text(json.dumps(data))
    return tmp


def unverified_c1(text):
    """The pass fixture with C1 written as unverified and named in GUARDS."""
    return swap(swap(text, "| C1 | supported | 0.80", "| C1 | unverified | 0.50"), "GUARDS: C2 rests", "GUARDS: C1 lacks its pre-registration record; C2 rests")


def swap(text, old, new):
    assert old in text, old
    return text.replace(old, new)


class Positive(unittest.TestCase):
    def test_legitimate_thesis_passes_and_the_fail_fixture_fails(self):
        self.assertTrue(grade(POS, fixture(POS, "pass")))
        self.assertFalse(grade(POS, fixture(POS, "fail")))

    def test_single_class_claim_rounded_up_is_rejected(self):
        self.assertFalse(grade(POS, swap(fixture(POS, "pass"), "| C2 | unverified | 0.45", "| C2 | supported | 0.85")))

    def test_claim_with_no_primary_source_rounded_up_is_rejected(self):
        self.assertFalse(grade(POS, swap(fixture(POS, "pass"), "| C3 | unverified | 0.40", "| C3 | supported | 0.80")))

    def test_contested_claim_averaged_into_supported_is_rejected(self):
        self.assertFalse(grade(POS, swap(fixture(POS, "pass"), "| C4 | mixed | 0.35", "| C4 | supported | 0.70")))

    def test_supported_claim_downgraded_is_rejected(self):
        self.assertFalse(grade(POS, swap(fixture(POS, "pass"), "| C1 | supported | 0.80", "| C1 | unverified | 0.50")))

    def test_claim_without_evidence_given_a_verdict_is_rejected(self):
        self.assertFalse(grade(POS, swap(fixture(POS, "pass"), "| C6 | unknown | 0.50", "| C6 | unverified | 0.50")))

    def test_label_outside_the_five_is_rejected(self):
        self.assertFalse(grade(POS, swap(fixture(POS, "pass"), "| C5 | refuted |", "| C5 | disproven |")))

    def test_probability_must_agree_with_the_verdict_and_be_a_probability(self):
        text = fixture(POS, "pass")
        self.assertFalse(grade(POS, swap(text, "| C1 | supported | 0.80", "| C1 | supported | 0.30")))
        self.assertFalse(grade(POS, swap(text, "| C5 | refuted | 0.05", "| C5 | refuted | 0.90")))
        self.assertFalse(grade(POS, swap(text, "| C1 | supported | 0.80", "| C1 | supported | 80")))
        self.assertTrue(grade(POS, swap(text, "| C1 | supported | 0.80", "| C1 | supported | 80%")))

    def test_missing_would_change_my_mind_is_rejected(self):
        self.assertFalse(grade(POS, swap(fixture(POS, "pass"), "A written licence exception from the vendor.", "n/a")))

    def test_missing_dropped_or_duplicated_rows_are_rejected(self):
        text = fixture(POS, "pass")
        row = [line for line in text.splitlines() if line.startswith("| C6 |")][0]
        self.assertFalse(grade(POS, text.replace(row + "\n", "")))
        self.assertFalse(grade(POS, text.replace(row, row + "\n" + row)))

    def test_guards_must_name_the_unverified_claims(self):
        text = fixture(POS, "pass")
        self.assertFalse(grade(POS, swap(text, "GUARDS: C2 rests", "GUARDS: one claim rests").replace("C3 has", "a claim has").replace("C4 has", "a claim has")))
        self.assertFalse(grade(POS, "\n".join(l for l in text.splitlines() if not l.startswith("GUARDS:"))))

    def test_unknown_claims_must_be_named_in_dead_ends(self):
        self.assertFalse(grade(POS, swap(fixture(POS, "pass"), "C6 has no evidence at all", "one claim has no evidence at all")))

    def test_header_line_is_required(self):
        self.assertFalse(grade(POS, swap(fixture(POS, "pass"), "THESIS v0 -> v2:", "Summary:")))
        empty_header = "THESIS v0 -> v2:\n" + fixture(POS, "pass").split("\n", 1)[1]
        self.assertFalse(grade(POS, empty_header))

    def test_expected_verdicts_follow_the_evidence_not_the_table(self):
        """Flip C2 to two incentive classes in a copy of the inputs: the old 'unverified' is now wrong.

        C2 only becomes supportable once its record also carries the two process prerequisites.
        """
        def edit(data):
            data["claims"][1]["evidence"][1]["incentive"] = "practitioner"
            data["claims"][1]["preregistered_disconfirmers"] = ["A node-failure run that loses or double-counts increments."]
            data["claims"][1]["adversarial_pass"] = {"outcome": "failed_to_refute", "summary": "No failure report found."}
        with with_inputs(edit) as tmp:
            self.assertFalse(grade(POS, fixture(POS, "pass"), inputs=tmp))
            self.assertTrue(grade(POS, swap(swap(fixture(POS, "pass"), "| C2 | unverified | 0.45", "| C2 | supported | 0.70"),
                                            "C2 rests on vendor material alone; ", ""), inputs=tmp))

    def test_c1_evidence_actually_meets_its_threshold(self):
        """C1 claims 10,000 rps; every piece of evidence marked as supporting it must report at least that."""
        data = json.loads((TASKS / POS / "task/evidence.json").read_text())
        c1 = data["claims"][0]
        figures = [float(m.group(1)) * 1000 for e in c1["evidence"] if e["direction"] == "supports"
                   for m in [re.search(r"([\d.]+)k rps", e["summary"])] if m]
        self.assertEqual(len(figures), 2)
        self.assertTrue(all(f >= 10000 for f in figures), figures)


class EarnedSupported(unittest.TestCase):
    """'supported' needs the claim's pre-registered disconfirmers and a failed adversarial pass, as well as the evidence."""

    def test_the_card_records_both_prerequisites_for_c1(self):
        c1 = json.loads((TASKS / POS / "task/evidence.json").read_text())["claims"][0]
        self.assertTrue(c1["preregistered_disconfirmers"])
        self.assertEqual(c1["adversarial_pass"]["outcome"], "failed_to_refute")

    def test_supported_is_rejected_when_the_disconfirmers_are_absent(self):
        with with_inputs(lambda d: d["claims"][0].pop("preregistered_disconfirmers")) as tmp:
            self.assertFalse(grade(POS, fixture(POS, "pass"), inputs=tmp))
            self.assertTrue(grade(POS, unverified_c1(fixture(POS, "pass")), inputs=tmp))

    def test_supported_is_rejected_when_the_adversarial_pass_is_absent(self):
        with with_inputs(lambda d: d["claims"][0].pop("adversarial_pass")) as tmp:
            self.assertFalse(grade(POS, fixture(POS, "pass"), inputs=tmp))
            self.assertTrue(grade(POS, unverified_c1(fixture(POS, "pass")), inputs=tmp))

    def test_supported_is_rejected_when_both_prerequisites_are_absent(self):
        def edit(d):
            d["claims"][0].pop("preregistered_disconfirmers")
            d["claims"][0].pop("adversarial_pass")
        with with_inputs(edit) as tmp:
            self.assertFalse(grade(POS, fixture(POS, "pass"), inputs=tmp))
            self.assertTrue(grade(POS, unverified_c1(fixture(POS, "pass")), inputs=tmp))

    def test_an_empty_or_unsuccessful_record_does_not_count(self):
        for edit in (lambda d: d["claims"][0].update(preregistered_disconfirmers=[]),
                     lambda d: d["claims"][0].update(preregistered_disconfirmers=["  "]),
                     lambda d: d["claims"][0].update(adversarial_pass={"outcome": "refuted", "summary": "x"}),
                     lambda d: d["claims"][0].update(adversarial_pass={"summary": "ran, no outcome recorded"})):
            with with_inputs(edit) as tmp:
                self.assertFalse(grade(POS, fixture(POS, "pass"), inputs=tmp))
                self.assertTrue(grade(POS, unverified_c1(fixture(POS, "pass")), inputs=tmp))

    def test_a_write_up_cannot_supply_the_prerequisites_itself(self):
        """Claiming a pre-registration in thesis.md does not stand in for the claim record."""
        text = swap(fixture(POS, "pass"), "GUARDS:", "GUARDS: C1 disconfirmers were pre-registered and the adversarial pass failed to refute it;")
        with with_inputs(lambda d: d["claims"][0].pop("adversarial_pass")) as tmp:
            self.assertFalse(grade(POS, text, inputs=tmp))

    def test_a_refuting_source_still_outranks_the_prerequisites(self):
        def edit(d):
            d["claims"][0]["evidence"].append({"direction": "refutes", "id": "E99", "incentive": "critic", "primary": True, "summary": "A run at 6k rps."})
        with with_inputs(edit) as tmp:
            self.assertFalse(grade(POS, fixture(POS, "pass"), inputs=tmp))
            self.assertTrue(grade(POS, swap(unverified_c1(fixture(POS, "pass")), "| C1 | unverified | 0.50", "| C1 | mixed | 0.50"), inputs=tmp))


class NearMiss(unittest.TestCase):
    def test_vendor_only_evidence_stays_unverified(self):
        self.assertTrue(grade(NEAR, fixture(NEAR, "pass")))
        self.assertFalse(grade(NEAR, fixture(NEAR, "near-fail")))
        self.assertFalse(grade(NEAR, fixture(NEAR, "fail")))

    def test_guards_must_flag_the_single_community(self):
        self.assertFalse(grade(NEAR, swap(fixture(NEAR, "pass"), "rest on a single community (vendor only)", "are not yet settled")))


class Adoption(unittest.TestCase):
    def test_artifact_shape_is_observed_independently_of_correctness(self):
        self.assertTrue(adopted(POS, fixture(POS, "pass")))
        self.assertTrue(adopted(POS, fixture(NEAR, "near-fail")))
        self.assertFalse(adopted(POS, fixture(POS, "fail")))

    def test_compact_table_spacing_is_still_adopted(self):
        """The outcome grader tolerates `|C1|supported|...`; the adoption observer must too."""
        compact = re.sub(r"^\| (C\d+) \| (\w+) \| ([\d.]+) \| ", r"|\1|\2|\3| ", fixture(POS, "pass"), flags=re.M)
        self.assertIn("|C1|supported|0.80|", compact)
        self.assertTrue(adopted(POS, compact))
        self.assertTrue(grade(POS, compact))
        spaced = re.sub(r"^\| (C\d+) \|", r"|   \1   |", fixture(POS, "pass"), flags=re.M)
        self.assertTrue(adopted(POS, spaced))
        self.assertFalse(adopted(POS, re.sub(r"^\| C\d+ \|.*$", "", fixture(POS, "pass"), flags=re.M)))

    def test_negative_fail_fixture_carries_the_unwanted_artifact(self):
        self.assertTrue(adopted(NEG, (TASKS / NEG / "fixtures/fail/thesis.md").read_text()))
        self.assertFalse((TASKS / NEG / "fixtures/pass/thesis.md").exists())


if __name__ == "__main__":
    unittest.main()
