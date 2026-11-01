"""Free pipeline contracts at real process/filesystem seams; no model calls."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
BASH = os.environ.get("TEST_BASH", "bash")

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

refresh = load("refresh_preflight", ROOT / "evals/paid/preflight_refresh.py")
schedule = load("paid_schedule", ROOT / "ci/check_paid_scheduling.py")

class WorkflowContracts(unittest.TestCase):
    def test_paid_gates_are_preserved_and_follow_free_checks(self):
        text = (ROOT / ".github/workflows/evals.yml").read_text(encoding="utf-8")
        self.assertEqual(schedule.check_text(text), [])
        for name in ("grader-model", "subject-model", "routing-eval"):
            self.assertEqual(schedule._field(schedule._job(text, name), "needs", 4), "[cheap]")
        self.assertIn("cheap", schedule._field(schedule._job(text, "deep-run"), "needs", 4))
        self.assertEqual(text.count("uses: ./.github/actions/setup-eval-tools"), 2)
        self.assertEqual(text.count("uses: ./.github/actions/eval-profile"), 3)

    def test_refresh_launch_checks_precede_any_spend(self):
        text = (ROOT / ".github/workflows/refresh-examples.yml").read_text(encoding="utf-8")
        self.assertLess(text.index("preflight_refresh.py"), text.index("run: evals/paid/check-subject-model.sh"))
        self.assertLess(text.index("preflight_refresh.py"), text.index("npx --yes promptfoo"))
        self.assertIn('bash evals/paid/capture-example.sh', text)
        self.assertIn("if: always()\n        uses: actions/upload-artifact@v4", text)

    def test_tool_lock_and_setup_do_not_initialize_promptfoo(self):
        package = json.loads((ROOT / "ci/tools/package.json").read_text(encoding="utf-8"))
        lock = json.loads((ROOT / "ci/tools/package-lock.json").read_text(encoding="utf-8"))
        pin = json.loads((ROOT / "evals/redteam/pin.json").read_text(encoding="utf-8"))
        self.assertEqual(package["dependencies"], lock["packages"][""]["dependencies"])
        self.assertEqual(package["dependencies"]["promptfoo"], pin["promptfoo"]["version"])
        for name, version in package["dependencies"].items():
            self.assertEqual(lock["packages"]["node_modules/" + name]["version"], version)
        setup = (ROOT / "ci/setup-eval-tools.sh").read_text(encoding="utf-8")
        self.assertIn("--ignore-scripts", setup)
        self.assertIn("npm ci", setup)
        self.assertIn("@anthropic-ai/claude-code/install.cjs", setup)
        self.assertIn("source.read(4)", setup)
        self.assertNotIn("npm rebuild", setup)
        self.assertNotIn("entrypoint.js", setup)
        self.assertNotIn("--version", setup)

class RefreshPreflight(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="refresh-contract-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for rel in ("evals/paid/capture-example.sh", "evals/paid/discover-paid-packs.sh", "plugins/scope-fence/.claude-plugin/plugin.json", "plugins/scope-fence/evals/promptfoo/promptfooconfig.yaml"):
            dest = self.root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / rel, dest)
        (self.root / ".claude-plugin").mkdir()
        (self.root / ".claude-plugin/marketplace.json").write_text(json.dumps({"plugins": [{"name": "scope-fence", "source": "./plugins/scope-fence"}]}), encoding="utf-8")
        self.git("init", "-q")
        self.git("add", ".")
        self.git("update-index", "--chmod=+x", "evals/paid/capture-example.sh")

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, capture_output=True, text=True, check=True)

    def test_real_capture_launcher_and_selection_pass_without_models(self):
        result = refresh.preflight(self.root, "scope-fence", BASH)
        self.assertEqual(result["plugins"], ["scope-fence"])
        self.assertEqual(result["model_calls"], 0)

    def test_missing_executable_mode_fails_before_spending(self):
        self.git("update-index", "--chmod=-x", "evals/paid/capture-example.sh")
        with self.assertRaisesRegex(ValueError, "100755"):
            refresh.preflight(self.root, "scope-fence", BASH)

    def test_invalid_retired_duplicate_and_path_selection_fail(self):
        for selected in ("jori", "../scope-fence", "scope-fence scope-fence", "unknown"):
            with self.subTest(selected=selected), self.assertRaises(ValueError):
                refresh.preflight(self.root, selected, BASH)

    def test_broken_capture_help_fails_before_spending(self):
        (self.root / "evals/paid/capture-example.sh").write_text("#!/usr/bin/env bash\nexit 9\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "launcher"):
            refresh.preflight(self.root, "scope-fence", BASH)

    def test_profile_uses_new_empty_paths_each_time(self):
        out = self.root / "github-env"
        env = {**os.environ, "RUNNER_TEMP": self.root.as_posix(), "GITHUB_ENV": out.as_posix()}
        for _ in range(2):
            subprocess.run([BASH, (ROOT / "ci/eval-profile.sh").as_posix()], env=env, check=True)
        paths = [line.split("=",1)[1] for line in out.read_text(encoding="utf-8").splitlines() if line.startswith("PROMPTFOO_CONFIG_DIR=")]
        self.assertEqual(len(set(paths)), 2)
        self.assertTrue(all(Path(path).is_dir() for path in paths))
        self.assertIn("PROMPTFOO_DISABLE_TELEMETRY=1", out.read_text(encoding="utf-8"))

class CaptureEligibility(unittest.TestCase):
    def test_only_matching_nonfaulted_controls_are_publishable(self):
        with tempfile.TemporaryDirectory(prefix="capture-contract-") as folder:
            root = Path(folder)
            (root / "promptfooconfig.yaml").write_text("defaultTest:\n  options:\n    provider:\n      id: anthropic:messages:claude-test\n", encoding="utf-8")
            def row(skill, question="same task", provider="openrouter:qwen/test", output="actual output", failure=0):
                return {"vars": {"skill": skill, "question": question}, "provider": {"id": provider}, "response": {"output": output}, "success": True, "failureReason": failure, "gradingResult": {"reason": "fixture grade"}}
            for label, control, expected in (
                ("matched", row("calibration"), True),
                ("different task", row("calibration", question="other task"), False),
                ("different provider", row("calibration", provider="openrouter:other/test"), False),
                ("faulted", row("calibration", failure=2), False),
                ("empty", row("calibration", output=""), False),
            ):
                with self.subTest(label=label):
                    result = root / "results.json"
                    result.write_text(json.dumps({"results": {"results": [row("real method"), control]}}), encoding="utf-8")
                    output = root / label.replace(" ", "-")
                    subprocess.run([BASH, (ROOT / "evals/paid/capture-example.sh").as_posix(), result.as_posix(), "test", "--pack", root.as_posix(), "--out", output.as_posix()], check=True, capture_output=True)
                    self.assertEqual((output / "test.json").exists(), expected)

if __name__ == "__main__": unittest.main()
