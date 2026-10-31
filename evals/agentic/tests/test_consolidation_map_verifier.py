"""The consolidation-map graders reject degenerate maps and accept legitimate ones.

The check script is run directly (no sandbox) on a candidate ``consolidation-map.md``
the way the card's guard runs it: inputs from the card's ``task/`` directory, the
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
TASKS = ROOT / "evals/agentic/tasks/consolidation-map"
CHECK = ROOT / "evals/agentic/tasks/_verifiers/check_consolidation_map.py"
POS, NEAR, NEG = "consolidation-map-pos-01", "consolidation-map-near-01", "consolidation-map-neg-01"


def fixture(card, kind):
    return (TASKS / card / "fixtures" / kind / "consolidation-map.md").read_text()


def grade(card, text):
    """True when the card's check script accepts ``text`` as consolidation-map.md."""
    with tempfile.TemporaryDirectory() as tmp:
        (pathlib.Path(tmp) / "consolidation-map.md").write_text(text)
        env = {**os.environ, "AGENTIC_CARD_ID": card, "AGENTIC_INPUTS": str(TASKS / card / "task")}
        return subprocess.run([sys.executable, "-I", str(CHECK)], cwd=tmp, env=env,
                              capture_output=True, text=True).returncode == 0


def swap(text, old, new):
    assert old in text, old
    return text.replace(old, new)


class NearMiss(unittest.TestCase):
    def test_legitimate_draft_passes_and_adjacent_fixtures_fail(self):
        self.assertTrue(grade(NEAR, fixture(NEAR, "pass")))
        self.assertFalse(grade(NEAR, fixture(NEAR, "near-fail")))
        self.assertFalse(grade(NEAR, fixture(NEAR, "fail")))

    def test_draft_after_and_net_values_are_allowed(self):
        text = swap(fixture(NEAR, "pass"), "After n/a | Net n/a", "After 3 | Net -2")
        self.assertTrue(grade(NEAR, text))

    def test_decided_rows_under_one_unchanged_heading_are_rejected(self):
        text = """Consolidation map: reporting packages (DRAFT)
Before 5 | After n/a | Net n/a   (1 undecided)

## Unchanged
- absorb      report-builder
- merge-into  report-viewer -> report-builder
- retire  theme-pack
- keep  chart-lib

## Reconciliation
RECONCILIATION FAILED
- report-exporter is UNDECIDED.
"""
        self.assertFalse(grade(NEAR, text))

    def test_decided_rows_under_reconciliation_without_units_are_rejected(self):
        text = """## Reconciliation
RECONCILIATION FAILED: report-exporter UNDECIDED
- absorb      report-builder
- merge-into  report-viewer -> report-builder
- retire  theme-pack
- keep  chart-lib
"""
        self.assertFalse(grade(NEAR, text))

    def test_unit_sections_without_why_lost_or_evidence_are_rejected(self):
        good = fixture(NEAR, "pass")
        for line in ("Why: the viewer only rendered what the builder already produced.\n",
                     "What's lost: the standalone embed script.\n",
                     "Evidence: no imports in 90 days.\n"):
            with self.subTest(removed=line.split(":")[0]):
                self.assertFalse(grade(NEAR, swap(good, line, "")))

    def test_invented_reason_and_denied_loss_are_rejected(self):
        good = fixture(NEAR, "pass")
        self.assertFalse(grade(NEAR, swap(good, "Why: the viewer only rendered what the builder already produced.",
                                          "Why: leadership requested it.")))
        self.assertFalse(grade(NEAR, swap(good, "What's lost: the standalone embed script.",
                                          "What's lost: nothing was lost.")))

    def test_missing_undecided_marker_or_failure_is_rejected(self):
        good = fixture(NEAR, "pass")
        self.assertFalse(grade(NEAR, swap(good, "RECONCILIATION FAILED", "all good")))
        self.assertFalse(grade(NEAR, re.sub(r"UNDECIDED", "pending", good)))


class Positive(unittest.TestCase):
    def test_legitimate_map_passes_and_the_summary_fails(self):
        self.assertTrue(grade(POS, fixture(POS, "pass")))
        self.assertFalse(grade(POS, fixture(POS, "fail")))

    def test_wrong_reconciliation_arithmetic_is_rejected(self):
        good = fixture(POS, "pass")
        self.assertFalse(grade(POS, swap(good, "N = K + X + R : 8 = 3 + 4 + 1   OK", "4 = 0 + 0 OK")))
        self.assertFalse(grade(POS, swap(good, "N = K + X + R : 8 = 3 + 4 + 1   OK", "N = K + X + R : 8 = 3 + 3 + 2   OK")))
        self.assertFalse(grade(POS, swap(good, "M = K + W     : 4 = 3 + 1       OK", "M = K + W     : 5 = 4 + 1       OK")))

    def test_reconciliation_body_replaced_by_ok_or_missing_checks_is_rejected(self):
        good = fixture(POS, "pass")
        head = good[:good.index("## Reconciliation")]
        self.assertFalse(grade(POS, head + "## Reconciliation\nOK\n"))
        self.assertFalse(grade(POS, swap(good, "Every merge-into target survives:    OK\n", "")))
        self.assertFalse(grade(POS, swap(good, "Every inventory entity appears once: OK\n", "")))

    def test_invented_reasons_are_rejected_but_paraphrase_passes(self):
        good = fixture(POS, "pass")
        reason = "Why: nothing has called it in 90 days and no replacement is planned."
        self.assertFalse(grade(POS, swap(good, reason, "Why: leadership requested it.")))
        self.assertTrue(grade(POS, swap(good, reason, "Why: no replacement is planned and nothing called it for 90 days.")))

    def test_denied_losses_are_rejected_but_paraphrase_passes(self):
        good = fixture(POS, "pass")
        loss = "What's lost: the 30-day replay endpoint, which audit-log does not offer."
        for denial in ("nothing was lost.", "Nothing", "None.", "No functionality was lost.", "No loss.", "n/a"):
            with self.subTest(denial=denial):
                self.assertFalse(grade(POS, swap(good, loss, "What's lost: " + denial)))
        self.assertTrue(grade(POS, swap(good, loss, "What's lost: audit-log has no 30-day replay endpoint, so that goes.")))

    def test_denying_the_resend_button_loss_is_rejected(self):
        good = fixture(POS, "pass")
        loss = "What's lost: nothing yet; removal will drop the manual resend button."
        self.assertFalse(grade(POS, swap(good, loss, "What's lost: nothing.")))
        self.assertTrue(grade(POS, swap(good, loss, "What's lost: nothing yet; the manual resend button goes at removal.")))

    def test_retire_needs_its_own_evidence_line(self):
        good = fixture(POS, "pass")
        self.assertFalse(grade(POS, swap(good, "Evidence: no inbound calls in 90 days.\n", "")))
        self.assertFalse(grade(POS, swap(good, "Evidence: no inbound calls in 90 days.", "Evidence: it seemed old.")))


class NegativeGuard(unittest.TestCase):
    """The unnecessary-ritual card's guard compares the bytes against the supplied notes."""

    def guard(self, notes):
        line = [l for l in (TASKS / NEG / "fixtures/pass/guard.sh").read_text().splitlines() if "# GUARD_CHECK" in l][0]
        with tempfile.TemporaryDirectory() as tmp:
            (pathlib.Path(tmp) / "notes.md").write_text(notes)
            env = {**os.environ, "AGENTIC_INPUTS": str(TASKS / NEG / "task")}
            return subprocess.run(["bash", "-c", line], cwd=tmp, env=env, capture_output=True).returncode == 0

    def test_only_the_typo_fix_passes(self):
        source = (TASKS / NEG / "task/notes.md").read_text()
        self.assertTrue(self.guard(source.replace("recieve", "receive")))
        self.assertFalse(self.guard(source))
        self.assertFalse(self.guard("# Notes\n\nwe receive\nnothing else\n"))
        self.assertFalse(self.guard(source.replace("recieve", "receive") + "extra line\n"))
        self.assertFalse(self.guard(source.replace("recieve", "receive").replace("retry", "backoff")))

    def test_pass_and_fail_guards_are_identical(self):
        self.assertEqual((TASKS / NEG / "fixtures/pass/guard.sh").read_bytes(),
                         (TASKS / NEG / "fixtures/fail/guard.sh").read_bytes())


class ArmManifest(unittest.TestCase):
    def test_committed_treatment_footprint_matches_the_shipped_skill(self):
        from evals.agentic.framework import pairing
        committed = json.loads((ROOT / "evals/agentic/manifests/arms/consolidation-map.json").read_text())
        arm = pairing.Arm.from_dict(committed["full_package_arm"])
        with tempfile.TemporaryDirectory() as tmp:
            pairing.materialize(arm, pathlib.Path(tmp))  # raises ContractError when the footprint is stale


if __name__ == "__main__":
    unittest.main()
