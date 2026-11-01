"""Free pipeline contracts at real process/filesystem seams; no model calls."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import copy
import yaml

ROOT = Path(__file__).resolve().parents[2]
BASH = None

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

refresh = load("refresh_preflight", ROOT / "evals/paid/preflight_refresh.py")
schedule = load("paid_schedule", ROOT / "ci/check_paid_scheduling.py")
BASH = load("host_tools", ROOT / "ci/host_tools.py").select_bash()

class WorkflowContracts(unittest.TestCase):
    def test_paid_gates_are_preserved_and_follow_free_checks(self):
        text = (ROOT / ".github/workflows/evals.yml").read_text(encoding="utf-8")
        self.assertEqual(schedule.check_text(text), [])
        jobs = yaml.load(text, Loader=yaml.BaseLoader)["jobs"]
        for name in ("grader-model", "subject-model", "routing-eval"):
            self.assertEqual(jobs[name]["needs"], ["cheap"])
        for name in ("behavioral", "deep"):
            self.assertIn("cheap", jobs[name]["needs"])
            self.assertIn("!cancelled()", jobs[name]["if"])
            step = jobs[name]["steps"][0]
            self.assertIn("needs.cheap.result", step["env"]["CHEAP"])
            # Execute the actual aggregate script with a failed dependency; no
            # fake provider is involved, and it must fail before later branches.
            outcome = subprocess.run([BASH, "-c", step["run"]], env={**os.environ, "CHEAP": "failure"}, capture_output=True)
            self.assertNotEqual(outcome.returncode, 0)
            self.assertIn(b"blocked by cheap", outcome.stdout)
        for name in ("behavioral-run", "routing-eval"):
            setup = [step for step in jobs[name]["steps"] if step.get("uses") == "./.github/actions/setup-eval-tools"]
            self.assertEqual(len(setup), 1)
            self.assertEqual(setup[0]["with"]["offline-sandbox"], "false")
        paths = jobs["counterfeit-detect"]["steps"][1]["with"]["filters"]
        for surface in (".github/actions/**", "ci/setup-eval-tools.sh", "ci/eval-profile.sh", "ci/tools/**"):
            self.assertIn(surface, paths)

    def test_refresh_launch_and_full_free_gate_precede_any_spend(self):
        text = (ROOT / ".github/workflows/refresh-examples.yml").read_text(encoding="utf-8")
        steps = yaml.load(text, Loader=yaml.BaseLoader)["jobs"]["refresh"]["steps"]
        scripts = [(index, step.get("run", "")) for index, step in enumerate(steps)]
        preflight = next(i for i, script in scripts if "preflight_refresh.py" in script)
        full_free = [i for i, script in scripts if script.strip() == "evals/cheap/run.sh"]
        ping = next(i for i, script in scripts if "check-subject-model.sh" in script)
        paid = next(i for i, script in scripts if 'entrypoint.js" eval' in script)
        self.assertLess(preflight, ping)
        self.assertLess(full_free[0], ping)
        self.assertLess(ping, paid)
        self.assertGreater(full_free[-1], paid)
        cleanup = next(i for i, script in scripts if "rm -fv plugins/*/evals/promptfoo/results.json" in script)
        self.assertLess(paid, cleanup)
        self.assertLess(cleanup, full_free[-1])
        self.assertTrue(any(step.get("uses") == "actions/upload-artifact@v4" and step.get("if") == "always()" for step in steps))

    def test_manual_evaluators_use_the_same_locked_tools(self):
        for name in ("subject-matrix.yml", "grader-agreement.yml"):
            text = (ROOT / ".github/workflows" / name).read_text(encoding="utf-8")
            jobs = yaml.load(text, Loader=yaml.BaseLoader)["jobs"]
            self.assertNotIn("npx --yes promptfoo", text)
            self.assertIn('node "$PROMPTFOO_HOME/dist/src/entrypoint.js" eval', text)
            self.assertTrue(any(step.get("uses") == "./.github/actions/setup-eval-tools" for job in jobs.values() for step in job["steps"]))

    def test_tool_lock_and_reviewed_lifecycle_policy(self):
        policy = load("toolchain", ROOT / "ci/check_toolchain.py")
        self.assertEqual(policy.check(ROOT), [])
        pin = json.loads((ROOT / "evals/redteam/pin.json").read_text(encoding="utf-8"))
        package = json.loads((ROOT / "ci/tools/package.json").read_text(encoding="utf-8"))
        self.assertEqual(package["dependencies"]["promptfoo"], pin["promptfoo"]["version"])
        setup = (ROOT / "ci/setup-eval-tools.sh").read_text(encoding="utf-8")
        self.assertIn("--ignore-scripts", setup)
        self.assertIn("check_toolchain.py", setup)
        self.assertIn(".bin/claude", setup)
        self.assertIn("source.read(4)", setup)
        self.assertNotIn("npm rebuild", setup)
        self.assertNotIn("entrypoint.js", setup)
        # Missing infrastructure must not turn the repository gate into a skip.
        gate = (ROOT / "evals/cheap/run.sh").read_text(encoding="utf-8")
        self.assertIn("required runner or composite action missing", gate)

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

    def test_later_matching_pair_is_not_lost_to_an_unpaired_first_row(self):
        with tempfile.TemporaryDirectory(prefix="capture-later-") as folder:
            root = Path(folder)
            (root / "promptfooconfig.yaml").write_text("defaultTest:\n  options:\n    provider:\n      id: anthropic:messages:claude-test\n", encoding="utf-8")
            rows = [{"vars": {"skill": skill, "question": question}, "provider": {"id": "openrouter:qwen/test"}, "response": {"output": "fixture"}, "success": True} for skill, question in (("real", "unpaired"), ("real", "paired"), ("calibration", "paired"))]
            (root / "results.json").write_text(json.dumps({"results": {"results": rows}}), encoding="utf-8")
            subprocess.run([BASH, (ROOT / "evals/paid/capture-example.sh").as_posix(), (root / "results.json").as_posix(), "test", "--pack", root.as_posix(), "--out", (root / "out").as_posix()], check=True, capture_output=True)
            self.assertEqual(json.loads((root / "out/test.json").read_text(encoding="utf-8"))["prompt"], "paired")

if __name__ == "__main__": unittest.main()
