"""Real sandbox probes of subject code trying to short-circuit its grader."""
import difflib
import json
import pathlib
import shutil
import tempfile
import unittest

from evals.agentic.tasks._verifiers import verify_outcome as outcome

ROOT = pathlib.Path(__file__).resolve().parents[3]


class GraderForgery(unittest.TestCase):
    def grade(self, card_id, edits):
        card = outcome._find_card(ROOT, card_id)
        with tempfile.TemporaryDirectory(prefix="grader-forgery-") as tmp:
            workspace = pathlib.Path(tmp) / "subject"
            shutil.copytree(ROOT / card["pass_fixture"], workspace)
            for name, data in edits.items():
                target = workspace / name
                if data is None:
                    target.unlink(missing_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(data)
            return outcome._verdict(ROOT, card_id, workspace)

    def test_subject_json_module_cannot_replace_canonical_parser(self):
        cases = {
            "plugin-factory-pos-01": {"plugin.json": "NOT JSON\n"},
            "wayfinder-pos-01": {"tickets.json": "NOT JSON\n"},
            "jori-near-01": {"dashboard.json": "NOT JSON\n"},
            "agent-compiler-pos-01": {"rendered.md": "imageHash: totally-made-up\n"},
        }
        for card, edits in cases.items():
            with self.subTest(card=card):
                self.assertFalse(self.grade(card, {**edits, "json.py": "import os; os._exit(0)\n"})[0])

    def test_early_exit_cannot_replace_function_results(self):
        for exit_code in ("import sys; sys.exit(0)", "import os; os._exit(0)"):
            cases = {
                "codebase-design-pos-01": {"rate_limiter.py": exit_code},
                "find-before-build-pos-01": {"client.py": exit_code},
                "diagnosing-bugs-pos-01": {"parse_duration.py": exit_code + "\ndef parse_duration(value): return -1\n"},
                "verify-before-claim-pos-01": {
                    "module.py": exit_code,
                    "module_test.py": "import sys,os\nprint('Ran 4 tests\\nOK',file=sys.stderr,flush=True)\nos._exit(0)\n",
                },
            }
            for card, edits in cases.items():
                with self.subTest(card=card, exit_code=exit_code):
                    self.assertFalse(self.grade(card, edits)[0])

    def test_fake_unittest_summary_cannot_replace_supplied_tests(self):
        fake = "import sys,os\nprint('Ran 4 tests\\nOK',file=sys.stderr,flush=True)\nos._exit(0)\n"
        for name in ("module_test.py", "inputs/module_test.py"):
            self.assertFalse(self.grade("verify-before-claim-pos-01", {name: fake})[0])
        # The checker runs the supplied immutable source even when no test
        # file is returned with the candidate's genuine passing module.
        self.assertTrue(self.grade("verify-before-claim-pos-01", {"module_test.py": None})[0])

    def test_prerecorded_result_json_cannot_replace_live_calls(self):
        fake = "import os\nos.write(1,b'[true,true,false,true,false,true,true,false]\\n')\nos._exit(0)\n"
        self.assertFalse(self.grade("codebase-design-pos-01", {"rate_limiter.py": fake})[0])

    def test_candidate_functions_cannot_read_hidden_grader(self):
        module = ("import pathlib\n"
                  "assert not pathlib.Path('/repo/evals/agentic/tasks/_verifiers/check_task.py').exists()\n"
                  "def add(a,b): return a+b\n")
        passed, reason = self.grade("verify-before-claim-pos-01", {"module.py": module})
        self.assertTrue(passed, reason)

    def test_patch_function_cannot_exit_before_independent_checks(self):
        old = 'def parse_config(cfg):\n    result = cfg.get("name", "default")\n    return result\n\n# TODO: remove migration shim (stale)\nif False:\n    print("unused legacy configuration")\n'
        new = old.replace('    result = cfg.get', '    import os; os._exit(0)\n    result = cfg.get')
        patch = ''.join(difflib.unified_diff(old.splitlines(keepends=True), new.splitlines(keepends=True),
                                            fromfile="a/parse_config.py", tofile="b/parse_config.py"))
        self.assertFalse(self.grade("scope-fence-pos-01", {"diff.patch": patch})[0])

    def test_correct_originals_still_pass(self):
        for card in ("plugin-factory-pos-01", "wayfinder-pos-01", "jori-near-01", "agent-compiler-pos-01",
                     "codebase-design-pos-01", "find-before-build-pos-01", "diagnosing-bugs-pos-01",
                     "verify-before-claim-pos-01", "scope-fence-pos-01"):
            with self.subTest(card=card):
                passed, reason = self.grade(card, {})
                self.assertTrue(passed, reason)


if __name__ == "__main__":
    unittest.main()
