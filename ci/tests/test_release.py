"""Exercise candidate packaging against real Git objects; no network or model."""
import importlib.util
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("candidate", ROOT / "release/build_candidate.py")
candidate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(candidate)


class Candidate(unittest.TestCase):
    def test_workflow_stages_only_on_manual_event_with_read_token(self):
        text = (ROOT / ".github/workflows/release-candidate.yml").read_text(encoding="utf-8")
        self.assertIn("contents: read", text)
        self.assertNotIn(": write", text)
        self.assertNotIn("secrets.", text)
        self.assertIn("if: github.event_name == 'workflow_dispatch'", text)
        self.assertIn("needs: [verify]", text)
        self.assertNotIn("gh release", text)
        self.assertNotIn("git tag", text)
        self.assertIn('"$CANDIDATE_SHA" =~ ^[0-9a-f]{40}$', text)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="source-candidate-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        (self.repo / "hello.sh").write_bytes(b"#!/bin/sh\nprintf hello\\n\n")
        self.git("add", ".")
        self.git("update-index", "--chmod=+x", "hello.sh")
        self.git("-c", "user.name=Candidate test", "-c", "user.email=candidate@example.invalid", "commit", "-qm", "fixture")

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.repo), *args], check=True, capture_output=True).stdout

    def test_exact_git_bytes_modes_and_reproducibility(self):
        first = candidate.build(self.repo, "HEAD", self.root / "first")
        (self.repo / "hello.sh").write_text("dirty working copy", encoding="utf-8")
        second = candidate.build(self.repo, "HEAD", self.root / "second")
        self.assertEqual(first, second)
        for name in (first["archive"], "manifest.json", "SHA256SUMS"):
            self.assertEqual((self.root / "first" / name).read_bytes(), (self.root / "second" / name).read_bytes())
        with tarfile.open(self.root / "first" / first["archive"], "r:gz") as archive:
            member = archive.getmembers()[0]
            self.assertEqual(member.mode, 0o755)
            self.assertIn(b"printf hello", archive.extractfile(member).read())
        with self.assertRaises(FileExistsError):
            candidate.build(self.repo, "HEAD", self.root / "first")

    def test_missing_commit_does_not_create_candidate(self):
        with self.assertRaises(subprocess.CalledProcessError):
            candidate.build(self.repo, "nonexistent", self.root / "missing")
        self.assertFalse((self.root / "missing").exists())

    def test_escaping_symlink_fails_closed(self):
        oid = subprocess.run(
            ["git", "-C", str(self.repo), "hash-object", "-w", "--stdin"], input=b"../outside", capture_output=True, check=True).stdout.decode().strip()
        self.git("update-index", "--add", "--cacheinfo", "120000," + oid + ",escape")
        self.git("-c", "user.name=Candidate test", "-c", "user.email=candidate@example.invalid", "commit", "-qm", "escaping link")
        with self.assertRaisesRegex(ValueError, "escaping"):
            candidate.build(self.repo, "HEAD", self.root / "unsafe")
        self.assertFalse((self.root / "unsafe").exists())

    def test_alias_dotdot_escape_is_rejected_before_output(self):
        for name, target in (("alias", b"."), ("escape", b"alias/..")):
            oid = subprocess.run(["git", "-C", str(self.repo), "hash-object", "-w", "--stdin"], input=target, capture_output=True, check=True).stdout.decode().strip()
            self.git("update-index", "--add", "--cacheinfo", "120000," + oid + "," + name)
        self.git("-c", "user.name=Candidate test", "-c", "user.email=candidate@example.invalid", "commit", "-qm", "alias escape")
        with self.assertRaisesRegex(ValueError, "symlink-component traversal"):
            candidate.build(self.repo, "HEAD", self.root / "alias-output")
        self.assertFalse((self.root / "alias-output").exists())

    def test_dangling_manifest_link_never_creates_external_file(self):
        output = self.root / "existing-output"
        output.mkdir()
        external = self.root / "outside-manifest.json"
        try:
            (output / "manifest.json").symlink_to(external)
        except OSError as error:
            self.skipTest("host cannot create filesystem symlinks: " + str(error))
        with self.assertRaises(FileExistsError):
            candidate.build(self.repo, "HEAD", output)
        self.assertFalse(external.exists())

    def test_existing_empty_output_directory_is_not_adopted(self):
        output = self.root / "empty-output"
        output.mkdir()
        with self.assertRaises(FileExistsError):
            candidate.build(self.repo, "HEAD", output)
        self.assertEqual(list(output.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
