"""Free tool policy and host-selection controls; never initialize a model client."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "ci" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

policy = load("check_toolchain")
host = load("host_tools")


class Tools(unittest.TestCase):
    def test_unknown_lifecycle_and_vulnerable_versions_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "ci/tools").mkdir(parents=True)
            for filename in ("package.json", "package-lock.json", "lifecycle-policy.json"):
                shutil.copyfile(ROOT / "ci/tools" / filename, root / "ci/tools" / filename)
            self.assertEqual(policy.check(root), [])
            path = root / "ci/tools/package-lock.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["packages"]["node_modules/unreviewed"] = {"version": "1.0.0", "hasInstallScript": True}
            path.write_text(json.dumps(data), encoding="utf-8")
            self.assertTrue(any("lifecycle inventory" in problem for problem in policy.check(root)))
            del data["packages"]["node_modules/unreviewed"]
            name = next(key for key in data["packages"] if key.endswith("node_modules/simple-git"))
            data["packages"][name]["version"] = "3.36.0"
            path.write_text(json.dumps(data), encoding="utf-8")
            self.assertTrue(any("advisory override" in problem for problem in policy.check(root)))

    def test_windows_prefers_git_bash_and_missing_support_fails_clearly(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            candidate = root / "Git/bin/bash.exe"
            candidate.parent.mkdir(parents=True)
            candidate.write_bytes(b"selection fixture only")
            self.assertEqual(host.select_bash({"ProgramFiles": str(root)}, windows=True), str(candidate))
            self.assertEqual(host.select_bash({"TEST_BASH": str(candidate)}, windows=True), str(candidate))
            with self.assertRaisesRegex(RuntimeError, "WSL shim is not selected"):
                host.select_bash({"PATH": str(root)}, windows=True)


if __name__ == "__main__":
    unittest.main()
