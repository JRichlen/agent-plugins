"""Exercise candidate packaging against real Git objects; no network or model."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import time
import unittest
from unittest import mock

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
        return subprocess.run(["git", "-c", "commit.gpgsign=false", "-C", str(self.repo), *args],
                              env=candidate.git_environment(), check=True, capture_output=True).stdout

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
            self.assertEqual((member.uid, member.gid, member.uname, member.gname), (0, 0, "", ""))
            self.assertEqual(member.mtime, int(self.git("log", "-1", "--no-show-signature", "--format=%ct")))
            self.assertIn(b"printf hello", archive.extractfile(member).read())
        header = (self.root / "first" / first["archive"]).read_bytes()[:10]
        self.assertEqual(header[:4], bytes([31, 139, 8, 0]))
        self.assertEqual(header[4:8], bytes(4))
        self.assertRegex(first["builder"]["source_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(first["builder"]["python"], sys.version.split()[0])
        with self.assertRaises(FileExistsError):
            candidate.build(self.repo, "HEAD", self.root / "first")

    def test_missing_commit_does_not_create_candidate(self):
        with self.assertRaisesRegex(ValueError, "git rev-parse failed"):
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

    def test_git_replace_cannot_change_archived_object_identity(self):
        original = self.git("rev-parse", "HEAD:hello.sh").decode().strip()
        replacement = subprocess.run(["git", "-C", str(self.repo), "hash-object", "-w", "--stdin"], input=b"substituted", capture_output=True, check=True).stdout.decode().strip()
        self.git("replace", original, replacement)
        manifest = candidate.build(self.repo, "HEAD", self.root / "replace-output")
        self.assertEqual(manifest["files"][0]["git_blob"], original)
        with tarfile.open(self.root / "replace-output" / manifest["archive"], "r:gz") as archive:
            self.assertIn(b"printf hello", archive.extractfile(archive.getmembers()[0]).read())

    def test_global_signing_and_git_environment_do_not_contaminate_build(self):
        baseline = candidate.build(self.repo, "HEAD", self.root / "clean")
        configuration = self.root / "global.gitconfig"
        configuration.write_text("[commit]\n gpgsign = true\n[log]\n showSignature = true\n", encoding="utf-8")
        with mock.patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": str(configuration), "GIT_DIR": str(self.root / "missing-git-dir")}):
            other = candidate.build(self.repo, "HEAD", self.root / "hostile-config")
        self.assertEqual(baseline, other)

    def test_separate_processes_reproduce_after_clock_and_environment_change(self):
        outputs = []
        for index, timezone in enumerate(("Asia/Kolkata", "America/Los_Angeles")):
            output = self.root / ("process-" + str(index))
            result = subprocess.run([sys.executable, str(ROOT / "release/build_candidate.py"), "--repo", str(self.repo), "--revision", "HEAD", "--output", str(output)], env={**os.environ, "TZ": timezone}, check=True, capture_output=True)
            outputs.append((output, json.loads(result.stdout)))
            if not index:
                time.sleep(1.1)
        for name in (outputs[0][1]["archive"], "manifest.json", "SHA256SUMS"):
            self.assertEqual((outputs[0][0] / name).read_bytes(), (outputs[1][0] / name).read_bytes())

    def test_failed_publication_leaves_no_partial_candidate(self):
        output = self.root / "failed-publication"
        with mock.patch.object(candidate.os, "rename", side_effect=PermissionError("fixture rename failure")):
            with self.assertRaises(PermissionError):
                candidate.build(self.repo, "HEAD", output)
        self.assertFalse(output.exists())
        self.assertEqual(list(self.root.glob(".failed-publication.build-*")), [])
        candidate.build(self.repo, "HEAD", output)

    def test_empty_target_and_git_metadata_target_are_rejected(self):
        for index, target in enumerate((b"", b".git/config")):
            with self.subTest(target=target):
                oid = subprocess.run(["git", "-C", str(self.repo), "hash-object", "-w", "--stdin"], input=target, capture_output=True, check=True).stdout.decode().strip()
                self.git("update-index", "--add", "--cacheinfo", "120000," + oid + ",link")
                self.git("-c", "user.name=Candidate test", "-c", "user.email=candidate@example.invalid", "commit", "-qm", "unsafe link")
                with self.assertRaisesRegex(ValueError, "unsafe symlink"):
                    candidate.build(self.repo, "HEAD", self.root / ("invalid-link-" + str(index)))

    def test_second_component_escape_fixture(self):
        for name, target in (("sub/s", b".."), ("t", b"sub/s/..")):
            oid = subprocess.run(["git", "-C", str(self.repo), "hash-object", "-w", "--stdin"], input=target, capture_output=True, check=True).stdout.decode().strip()
            self.git("update-index", "--add", "--cacheinfo", "120000," + oid + "," + name)
        self.git("-c", "user.name=Candidate test", "-c", "user.email=candidate@example.invalid", "commit", "-qm", "second chain")
        with self.assertRaisesRegex(ValueError, "symlink-component traversal"):
            candidate.build(self.repo, "HEAD", self.root / "second-chain")

    def test_implicit_parent_directories_extract_normally(self):
        nested = self.repo / "nested/deeper/file.txt"
        nested.parent.mkdir(parents=True)
        nested.write_bytes(b"nested source")
        self.git("add", ".")
        self.git("-c", "user.name=Candidate test", "-c", "user.email=candidate@example.invalid", "commit", "-qm", "nested file")
        output = self.root / "nested-output"
        manifest = candidate.build(self.repo, "HEAD", output)
        with tarfile.open(output / manifest["archive"], "r:gz") as archive:
            self.assertFalse(any(member.isdir() for member in archive.getmembers()))
            archive.extractall(self.root / "extracted", filter="data")
        prefix = "agent-plugins-" + manifest["commit"][:12]
        self.assertEqual((self.root / "extracted" / prefix / "nested/deeper/file.txt").read_bytes(), b"nested source")

    def test_non_utf8_filename_fails_with_explicit_error(self):
        oid = self.git("rev-parse", "HEAD:hello.sh").strip()
        subprocess.run(["git", "-C", str(self.repo), "update-index", "-z", "--index-info"],
                       input=b"100644 " + oid + b"\tinvalid-\xff\0", check=True, capture_output=True,
                       env=candidate.git_environment())
        self.git("-c", "user.name=Candidate test", "-c", "user.email=candidate@example.invalid", "commit", "-qm", "raw filename")
        with self.assertRaisesRegex(ValueError, "UTF-8"):
            candidate.build(self.repo, "HEAD", self.root / "non-utf8")


if __name__ == "__main__":
    unittest.main()
