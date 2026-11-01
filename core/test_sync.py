"""Filesystem-level checks for the fixed core packaging boundary."""
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name("sync.py")
CONTEXTS = ("delegated-intelligence", "verify-before-claim")


class CoreProjectionTests(unittest.TestCase):
    def setUp(self):
        # Exercise atomic writes on the checkout filesystem, not a virtualized
        # host temp volume with different rename permissions.
        self.temporary = tempfile.TemporaryDirectory(prefix="core-sync-test-", dir=SCRIPT.parent)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "repo"
        (self.root / "core").mkdir(parents=True)
        self.policy = self.root / "core/OPERATING.md"
        self.index = self.root / "core/ownership.json"
        self.policy.write_bytes(b"# Policy\n\nKeep evidence honest.\n")
        self.index.write_bytes(b'{"schemaVersion":1,"services":[]}\n')

    def run_sync(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), "--root", str(self.root), *args],
                              capture_output=True, text=True)

    def output(self, plugin=CONTEXTS[0], name="OPERATING.md"):
        return self.root / "plugins" / plugin / "context" / name

    def test_missing_check_is_read_only_then_build_is_exact_and_idempotent(self):
        self.assertEqual(self.run_sync("--check").returncode, 1)
        self.assertFalse((self.root / "plugins").exists())
        self.assertEqual(self.run_sync().returncode, 0)
        digest = hashlib.sha256(self.policy.read_bytes()).hexdigest().encode()
        for plugin in CONTEXTS:
            content = self.output(plugin).read_bytes()
            self.assertIn(digest, content)
            self.assertTrue(content.endswith(self.policy.read_bytes()))
            self.assertEqual(self.output(plugin, "ownership.json").read_bytes(), self.index.read_bytes())
        self.assertEqual(self.run_sync("--check").returncode, 0)
        self.assertIn("0 updated", self.run_sync().stdout)

    def test_mutated_and_missing_outputs_fail_then_restore(self):
        self.assertEqual(self.run_sync().returncode, 0)
        for plugin in CONTEXTS:
            for name in ("OPERATING.md", "ownership.json"):
                with self.subTest(plugin=plugin, name=name):
                    target = self.output(plugin, name)
                    original = target.read_bytes()
                    target.write_bytes(original + b"tamper\n")
                    self.assertEqual(self.run_sync("--check").returncode, 1)
                    self.assertEqual(self.run_sync().returncode, 0)
                    self.assertEqual(target.read_bytes(), original)
                    target.unlink()
                    self.assertEqual(self.run_sync("--check").returncode, 1)
                    self.assertEqual(self.run_sync().returncode, 0)

    def test_either_source_change_updates_both_policy_headers(self):
        self.assertEqual(self.run_sync().returncode, 0)
        before = self.output().read_bytes()
        self.index.write_bytes(b'{"schemaVersion":1,"services":["changed"]}\n')
        self.assertEqual(self.run_sync("--check").returncode, 1)
        self.assertEqual(self.run_sync().returncode, 0)
        self.assertNotEqual(self.output().read_bytes(), before)
        self.policy.write_bytes(self.policy.read_bytes() + b"New rule.\n")
        self.assertEqual(self.run_sync("--check").returncode, 1)

    def test_bad_source_schema_or_duplicate_keys_never_writes(self):
        for data in ('{"schemaVersion":2}', '{"schemaVersion":true}',
                     '{"schemaVersion":1,"schemaVersion":1}', 'not json'):
            with self.subTest(data=data):
                self.index.write_text(data)
                self.assertEqual(self.run_sync().returncode, 2)
                self.assertFalse((self.root / "plugins").exists())

    def test_empty_policy_cannot_make_empty_projections_pass(self):
        self.policy.write_bytes(b" \n")
        self.assertEqual(self.run_sync().returncode, 2)
        self.assertFalse((self.root / "plugins").exists())

    def test_unrelated_files_survive_and_unsafe_second_parent_prevents_all_writes(self):
        unrelated = self.root / "keep.txt"
        unrelated.write_bytes(b"keep\n")
        blocked = self.root / "plugins" / CONTEXTS[1] / "context"
        blocked.parent.mkdir(parents=True)
        blocked.write_bytes(b"not a directory\n")
        self.assertEqual(self.run_sync().returncode, 2)
        self.assertFalse(self.output().exists())
        self.assertEqual(unrelated.read_bytes(), b"keep\n")

    def test_output_override_is_rejected(self):
        self.assertEqual(self.run_sync("--output", "../outside").returncode, 2)
        self.assertFalse((self.root.parent / "outside").exists())

    def test_linked_context_cannot_redirect_writes_outside_repository(self):
        outside = self.root.parent / "outside"
        outside.mkdir()
        context = self.output().parent
        context.parent.mkdir(parents=True)
        try:
            context.symlink_to(outside, target_is_directory=True)
        except OSError as error:
            self.skipTest(f"host cannot create test symlink: {error}")
        self.assertEqual(self.run_sync().returncode, 2)
        self.assertEqual(list(outside.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
