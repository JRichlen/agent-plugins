"""Free tool policy and host-selection controls; never initialize a model client."""
import importlib.util
import hashlib
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
    def test_distribution_manifest_uses_case_sensitive_posix_order(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            dist = home / "dist/src"
            dist.mkdir(parents=True)
            for name, data in (("a.js", b"lower"), ("B.js", b"upper"), ("types.d.ts", b"types")):
                (dist / name).write_bytes(data)
            expected = "".join(f"dist/src/{name}  {hashlib.sha256(data).hexdigest()}\n"
                               for name, data in (("B.js", b"upper"), ("a.js", b"lower"), ("types.d.ts", b"types")))
            self.assertEqual(policy.promptfoo_dist_manifest(home), (hashlib.sha256(expected.encode()).hexdigest(), 3))
            # Emulate Windows Path comparison even on Linux CI. Replacing the
            # explicit string key with Path.sort() must fail this control.
            class CasefoldFile:
                def __init__(self, path):
                    self.path, self.name = path, path.name
                def is_file(self):
                    return True
                def read_bytes(self):
                    return self.path.read_bytes()
                def relative_to(self, ignored):
                    return self.path.relative_to(home)
                def __lt__(self, other):
                    return self.name.casefold() < other.name.casefold()
            class WindowsLikeHome:
                def __truediv__(self, ignored):
                    return self
                def iterdir(self):
                    return [CasefoldFile(path) for path in dist.iterdir()]
            self.assertEqual(policy.promptfoo_dist_manifest(WindowsLikeHome()), (hashlib.sha256(expected.encode()).hexdigest(), 3))
            changed = expected.replace("dist/src/B.js", "dist\\src\\B.js")
            self.assertNotEqual(hashlib.sha256(changed.encode()).hexdigest(), policy.promptfoo_dist_manifest(home)[0])

    def test_unknown_lifecycle_and_vulnerable_versions_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "ci/tools").mkdir(parents=True)
            for filename in ("package.json", "package-lock.json", "lifecycle-policy.json"):
                shutil.copyfile(ROOT / "ci/tools" / filename, root / "ci/tools" / filename)
            self.assertEqual(policy.check(root), [])
            self.assertEqual(json.loads((root / "ci/tools/package.json").read_text(encoding="utf-8"))["packageManager"], "npm@10.9.8")
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
