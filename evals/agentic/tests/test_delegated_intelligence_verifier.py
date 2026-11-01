"""The delegated-intelligence grader reads files on disk and rejects trust in a "done".

The check script is run directly (no sandbox) on a copy of a card's fixture
workspace, the way the card's guard runs it: inputs from the card's ``task/``
directory, the candidate workspace as the working directory. Each test edits
the copy to break exactly one thing.
"""
from __future__ import annotations

import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
TASKS = ROOT / "evals/agentic/tasks/delegated-intelligence"
CHECK = ROOT / "evals/agentic/tasks/_verifiers/check_delegated_intelligence.py"
ADOPT = ROOT / "evals/agentic/tasks/_verifiers/verify_adoption.py"
POS, NEAR, NEG = "delegated-intelligence-pos-01", "delegated-intelligence-near-01", "delegated-intelligence-neg-01"


def workspace(card, kind, edit=None):
    """A TemporaryDirectory holding a copy of the fixture, after ``edit(path)``."""
    tmp = tempfile.TemporaryDirectory()
    shutil.copytree(TASKS / card / "fixtures" / kind, tmp.name, dirs_exist_ok=True)
    if edit:
        edit(pathlib.Path(tmp.name))
    return tmp


def inputs_copy(card, edit):
    tmp = tempfile.TemporaryDirectory()
    shutil.copytree(TASKS / card / "task", tmp.name, dirs_exist_ok=True)
    edit(pathlib.Path(tmp.name))
    return tmp


def grade(card, kind, edit=None, inputs=None):
    with workspace(card, kind, edit) as ws:
        env = {**os.environ, "AGENTIC_CARD_ID": card, "AGENTIC_INPUTS": str(inputs or TASKS / card / "task")}
        return subprocess.run([sys.executable, "-I", str(CHECK)], cwd=ws, env=env, capture_output=True, text=True).returncode == 0


def adopted(card, kind, edit=None):
    with workspace(card, kind, edit) as ws:
        env = {**os.environ, "AGENTIC_CARD_ID": card}
        return subprocess.run([sys.executable, str(ADOPT), ws], env=env, capture_output=True, text=True).returncode == 0


def sub(path, old, new):
    text = path.read_text()
    assert old in text, old
    path.write_text(text.replace(old, new))


class Positive(unittest.TestCase):
    def test_a_true_resume_passes_and_trusting_the_handbacks_fails(self):
        self.assertTrue(grade(POS, "pass"))
        self.assertFalse(grade(POS, "fail"))

    def test_a_complete_output_that_was_redone_is_rejected(self):
        self.assertFalse(grade(POS, "pass", lambda w: sub(w / "out/api.md", "# api", "# api (re-audited)")))

    def test_a_missing_output_behind_a_done_is_rejected(self):
        self.assertFalse(grade(POS, "pass", lambda w: (w / "out/notify.md").unlink()))

    def test_an_empty_output_behind_a_done_is_rejected(self):
        self.assertFalse(grade(POS, "pass", lambda w: (w / "out/search.md").write_text("  \n")))

    def test_an_output_naming_the_wrong_setting_is_rejected(self):
        self.assertFalse(grade(POS, "pass", lambda w: (w / "out/search.md").write_text("# search\nRISKY SETTING: tls_verify = false\n")))

    def test_an_output_that_lists_every_setting_is_rejected(self):
        self.assertFalse(grade(POS, "pass", lambda w: (w / "out/search.md").write_text("cors_origin = * and also tls_verify = false\n")))

    def test_a_look_alike_setting_is_not_the_finding(self):
        self.assertFalse(grade(POS, "pass", lambda w: (w / "out/notify.md").write_text("# notify\nRISKY SETTING: retry_delay = 0\n")))

    def test_report_row_with_the_wrong_setting_is_rejected(self):
        self.assertFalse(grade(POS, "pass", lambda w: sub(w / "report.md", "| notify | request_timeout = 0 |", "| notify | admin_password = admin |")))

    def test_report_row_naming_two_services_settings_is_rejected(self):
        self.assertFalse(grade(POS, "pass", lambda w: sub(w / "report.md", "| search | cors_origin = * |", "| search | cors_origin = *, tls_verify = false |")))

    def test_missing_report_or_row_is_rejected(self):
        self.assertFalse(grade(POS, "pass", lambda w: (w / "report.md").unlink()))
        self.assertFalse(grade(POS, "pass", lambda w: sub(w / "report.md", "| notify | request_timeout = 0 | out/notify.md |\n", "")))

    def test_board_must_show_the_rerun_and_leave_kept_rows_alone(self):
        self.assertFalse(grade(POS, "pass", lambda w: sub(w / "status.md", "out/search.md | landed | 2", "out/search.md | landed | 1")))
        self.assertFalse(grade(POS, "pass", lambda w: sub(w / "status.md", "out/api.md | landed | 1", "out/api.md | landed | 2")))
        self.assertFalse(grade(POS, "pass", lambda w: sub(w / "status.md", "out/notify.md | landed | 2", "out/notify.md | landed | 4")))

    def test_board_state_must_be_finished_and_every_row_present_once(self):
        self.assertFalse(grade(POS, "pass", lambda w: sub(w / "status.md", "out/notify.md | landed | 2", "out/notify.md | running | 2")))
        self.assertFalse(grade(POS, "pass", lambda w: sub(w / "status.md", "| audit billing | haiku | out/billing.md | landed | 1 |\n", "")))
        self.assertFalse(grade(POS, "pass", lambda w: sub(w / "status.md", "| audit billing | haiku | out/billing.md", "| audit billing | haiku | out/api.md")))
        self.assertTrue(grade(POS, "pass", lambda w: sub(w / "status.md", "out/notify.md | landed | 2", "out/notify.md | verified | 2")))

    def test_shared_inputs_are_read_only(self):
        self.assertFalse(grade(POS, "pass", lambda w: sub(w / "services/search.conf", "cors_origin = *", "cors_origin = https://x.example.com")))

    def test_the_expected_finding_follows_the_configs_not_the_deliverable(self):
        """Flip search's risky setting in a copy of the inputs: the old write-up is now wrong."""
        def flip(root):
            sub(root / "services/search.conf", "cors_origin = *", "cors_origin = https://x.example.com\ntls_verify = false")
            sub(root / "services/search.conf", "tls_verify = true\n", "")

        def flip_ws(w):
            flip(w)
        with inputs_copy(POS, flip) as tmp:
            self.assertFalse(grade(POS, "pass", flip_ws, inputs=tmp))

            def rewrite(w):
                flip(w)
                (w / "out/search.md").write_text("# search\nRISKY SETTING: tls_verify = false\n")
                sub(w / "report.md", "| search | cors_origin = * |", "| search | tls_verify = false |")
            self.assertTrue(grade(POS, "pass", rewrite, inputs=tmp))

    def test_an_input_with_two_risky_settings_is_refused(self):
        def two(root):
            (root / "services/api.conf").write_text((root / "services/api.conf").read_text() + "tls_verify = false\n")
        with inputs_copy(POS, two) as tmp:
            self.assertFalse(grade(POS, "pass", inputs=tmp))


class NearMiss(unittest.TestCase):
    def test_a_known_file_answered_inline_passes_and_the_alternatives_fail(self):
        self.assertTrue(grade(NEAR, "pass"))
        self.assertFalse(grade(NEAR, "near-fail"))
        self.assertFalse(grade(NEAR, "fail"))

    def test_each_fan_out_artifact_alone_is_rejected(self):
        for name in ("briefs", "out", "handbacks"):
            self.assertFalse(grade(NEAR, "pass", lambda w, n=name: (w / n).mkdir()), name)
        self.assertFalse(grade(NEAR, "pass", lambda w: (w / "status.md").write_text("| a | b | c | d | e |\n")))

    def test_the_right_number_with_a_unit_is_accepted_and_prose_is_not(self):
        self.assertTrue(grade(NEAR, "pass", lambda w: (w / "answer.txt").write_text("60 seconds\n")))
        self.assertFalse(grade(NEAR, "pass", lambda w: (w / "answer.txt").write_text("about 60\n")))
        self.assertFalse(grade(NEAR, "pass", lambda w: (w / "answer.txt").write_text("45\n")))
        self.assertFalse(grade(NEAR, "pass", lambda w: (w / "answer.txt").unlink()))

    def test_an_edited_config_is_rejected(self):
        self.assertFalse(grade(NEAR, "pass", lambda w: sub(w / "services/billing.conf", "request_timeout = 60", "request_timeout = 61")))


class Adoption(unittest.TestCase):
    def test_a_brief_with_a_tier_and_an_output_path_is_observed(self):
        self.assertTrue(adopted(POS, "pass"))
        self.assertTrue(adopted(NEAR, "near-fail"))
        self.assertFalse(adopted(POS, "fail"))
        self.assertFalse(adopted(NEAR, "pass"))

    def test_a_board_alone_is_not_adoption(self):
        """The seeded board already has tiers; only a brief counts as the run's own artifact."""
        self.assertFalse(adopted(POS, "fail"))
        self.assertTrue((TASKS / POS / "fixtures/fail/status.md").exists())

    def test_a_brief_missing_its_tier_or_output_path_is_not_adoption(self):
        self.assertFalse(adopted(POS, "pass", lambda w: [p.write_text("OBJECTIVE: x\nOUTPUT PATH: out/x.md\n") for p in (w / "briefs").glob("*.md")]))
        self.assertFalse(adopted(POS, "pass", lambda w: [p.write_text("TIER: haiku\nOBJECTIVE: x\n") for p in (w / "briefs").glob("*.md")]))
        self.assertFalse(adopted(POS, "pass", lambda w: [p.write_text("TIER: gpt\nOUTPUT PATH: out/x.md\n") for p in (w / "briefs").glob("*.md")]))


class Negative(unittest.TestCase):
    def guard(self, kind, edit=None):
        with workspace(NEG, kind, edit) as ws:
            env = {**os.environ, "AGENTIC_INPUTS": str(TASKS / NEG / "task")}
            return subprocess.run(["bash", str(TASKS / NEG / "fixtures" / kind / "guard.sh")], cwd=ws, env=env).returncode == 0

    def test_the_rename_is_graded_and_the_fan_out_is_the_unwanted_artifact(self):
        self.assertTrue(self.guard("pass"))
        self.assertTrue(self.guard("fail"))
        self.assertFalse(adopted(NEG, "pass"))
        self.assertTrue(adopted(NEG, "fail"))

    def test_an_incomplete_or_over_broad_rename_is_rejected(self):
        self.assertFalse(self.guard("pass", lambda w: sub(w / "util.py", "count = len(values)", "cnt = len(values)")))
        self.assertFalse(self.guard("pass", lambda w: sub(w / "util.py", "def total", "def sum_all")))


if __name__ == "__main__":
    unittest.main()
