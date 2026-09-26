"""Red-team lane test: T44, the frozen hashed adversarial corpus (design §5,
§13). Real-fixture where it matters: exercises the actual `bin/freeze.py`
script as a subprocess against both the committed corpus and mutated copies
of it, plus the pure `load()` API in-process.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
REDTEAM_ROOT = REPO_ROOT / "evals" / "redteam"
FREEZE_PY = REDTEAM_ROOT / "bin" / "freeze.py"


def _load_freeze_module():
    spec = importlib.util.spec_from_file_location("redteam_freeze", FREEZE_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _copy_redteam_tree(dest: pathlib.Path) -> pathlib.Path:
    """A working copy of just corpus/ + bin/freeze.py, since freeze.py
    resolves paths relative to its OWN location (two parents up)."""
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copytree(REDTEAM_ROOT / "corpus", dest / "corpus")
    (dest / "bin").mkdir()
    shutil.copy2(FREEZE_PY, dest / "bin" / "freeze.py")
    shutil.copytree(REDTEAM_ROOT / "providers", dest / "providers")
    shutil.copytree(REDTEAM_ROOT / "targets", dest / "targets")
    (dest / "fixtures" / "counterfeit").mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        REDTEAM_ROOT / "fixtures" / "counterfeit" / "held-out.json",
        dest / "fixtures" / "counterfeit" / "held-out.json",
    )
    return dest


class FrozenCorpusIntegrity(unittest.TestCase):
    """T44: every corpus file's sha256 matches the manifest; a mutated byte
    fails with the file named; counts match in both directions; every
    adversarial file has its clean twin and vice versa."""

    def test_freeze_check_passes_on_the_committed_corpus(self):
        result = subprocess.run(
            [sys.executable, str(FREEZE_PY), "--check"],
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout)
        self.assertIn("32 corpus files", result.stdout)

    def test_freeze_check_passes_on_the_committed_corpus__negative(self):
        """Catalog sibling. negative_control names a real corpus file; this
        test flips one of its bytes IN A COPY and proves --check reds with
        the file named -- the one-byte-drift discipline design §5.3 item 1
        requires, not merely 'the manifest exists'."""
        target_rel = "adversarial/secret-exfil/001.txt"
        real_file = REDTEAM_ROOT / "corpus" / target_rel
        self.assertTrue(real_file.is_file(), f"negative_control fixture missing: {real_file}")
        with tempfile.TemporaryDirectory() as td:
            work = _copy_redteam_tree(pathlib.Path(td) / "redteam")
            mutated = work / "corpus" / target_rel
            data = bytearray(mutated.read_bytes())
            data[0] ^= 0xFF
            mutated.write_bytes(bytes(data))
            result = subprocess.run(
                [sys.executable, str(work / "bin" / "freeze.py"), "--check"],
                capture_output=True, text=True, timeout=30,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("hash drift", result.stderr)
            self.assertIn(target_rel, result.stderr)

    def test_unmanifested_file_is_caught_both_directions(self):
        with tempfile.TemporaryDirectory() as td:
            work = _copy_redteam_tree(pathlib.Path(td) / "redteam")
            extra = work / "corpus" / "clean" / "secret-exfil" / "999.txt"
            extra.write_text("an extra file nobody froze\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(work / "bin" / "freeze.py"), "--check"],
                capture_output=True, text=True, timeout=30,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unmanifested file", result.stderr)
            self.assertIn("999.txt", result.stderr)

    def test_unmanifested_file_is_caught_both_directions__negative(self):
        """Catalog sibling. negative_control: the committed manifest itself
        -- deleting an entry from IT (rather than adding a file on disk)
        must ALSO be caught, proving the check runs in both directions
        (design §5.3 item 2's parenthetical), not just disk-has-extra."""
        manifest_path = REDTEAM_ROOT / "corpus" / "manifest.json"
        self.assertTrue(manifest_path.is_file(), f"negative_control fixture missing: {manifest_path}")
        with tempfile.TemporaryDirectory() as td:
            work = _copy_redteam_tree(pathlib.Path(td) / "redteam")
            manifest = json.loads((work / "corpus" / "manifest.json").read_text())
            removed = manifest["files"].pop(0)
            manifest["counts"]["total"] -= 1
            if removed["condition"] == "clean":
                manifest["counts"]["clean"] -= 1
            else:
                manifest["counts"]["adversarial"] -= 1
            (work / "corpus" / "manifest.json").write_text(json.dumps(manifest, indent=2))
            result = subprocess.run(
                [sys.executable, str(work / "bin" / "freeze.py"), "--check"],
                capture_output=True, text=True, timeout=30,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unmanifested file", result.stderr)

    def test_count_drift_is_caught(self):
        with tempfile.TemporaryDirectory() as td:
            work = _copy_redteam_tree(pathlib.Path(td) / "redteam")
            manifest_path = work / "corpus" / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["counts"]["total"] += 1
            manifest_path.write_text(json.dumps(manifest, indent=2))
            result = subprocess.run(
                [sys.executable, str(work / "bin" / "freeze.py"), "--check"],
                capture_output=True, text=True, timeout=30,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("count drift", result.stderr)

    def test_count_drift_is_caught__negative(self):
        """Catalog sibling. negative_control: the real, correctly-counted
        manifest passes with no count-drift complaint -- proving the check
        actually compares to a real number rather than always failing."""
        manifest_path = REDTEAM_ROOT / "corpus" / "manifest.json"
        self.assertTrue(manifest_path.is_file())
        result = subprocess.run(
            [sys.executable, str(FREEZE_PY), "--check"],
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("count drift", result.stdout + result.stderr)

    def test_unmatched_twin_is_caught(self):
        with tempfile.TemporaryDirectory() as td:
            work = _copy_redteam_tree(pathlib.Path(td) / "redteam")
            manifest_path = work / "corpus" / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            for entry in manifest["files"]:
                if entry["path"] == "clean/secret-exfil/001.txt":
                    entry["twin"] = "adversarial/secret-exfil/999-does-not-exist.txt"
            manifest_path.write_text(json.dumps(manifest, indent=2))
            result = subprocess.run(
                [sys.executable, str(work / "bin" / "freeze.py"), "--check"],
                capture_output=True, text=True, timeout=30,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unmatched twin", result.stderr)

    def test_unmatched_twin_is_caught__negative(self):
        """Catalog sibling. negative_control: every REAL twin pair (the
        committed manifest) must NOT be flagged -- proving the check finds a
        genuine mismatch rather than flagging every file's twin field."""
        mod = _load_freeze_module()
        manifest = mod.load_manifest()
        by_path = {e["path"]: e for e in manifest["files"]}
        for entry in manifest["files"]:
            self.assertIn(entry["twin"], by_path, f"{entry['path']}'s twin is unmanifested")

    def test_frozen_extra_hash_drift_is_caught(self):
        with tempfile.TemporaryDirectory() as td:
            work = _copy_redteam_tree(pathlib.Path(td) / "redteam")
            manifest_path = work / "corpus" / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            self.assertGreater(len(manifest["frozen_extra"]), 0)
            (work / "providers" / "control-safe.js").write_text(
                (work / "providers" / "control-safe.js").read_text() + "\n// tampered\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(work / "bin" / "freeze.py"), "--check"],
                capture_output=True, text=True, timeout=30,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("hash drift", result.stderr)
            self.assertIn("control-safe.js", result.stderr)

    def test_frozen_extra_hash_drift_is_caught__negative(self):
        """Catalog sibling. negative_control names the real, untampered
        providers/control-safe.js: it must NOT be flagged when unmodified."""
        real_provider = REDTEAM_ROOT / "providers" / "control-safe.js"
        self.assertTrue(real_provider.is_file(), f"negative_control fixture missing: {real_provider}")
        result = subprocess.run(
            [sys.executable, str(FREEZE_PY), "--check"],
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("control-safe.js", result.stdout + result.stderr)


class LoaderRefusesUnmanifested(unittest.TestCase):
    """T44: freeze.load() refuses any path not in the manifest with a
    matching hash -- the only sanctioned way to read corpus text."""

    def test_load_refuses_a_path_not_in_the_manifest(self):
        mod = _load_freeze_module()
        with self.assertRaises(mod.CorpusNotFrozen):
            mod.load("clean/secret-exfil/999-does-not-exist.txt")

    def test_load_refuses_a_path_not_in_the_manifest__negative(self):
        """Catalog sibling. negative_control names a real, manifested
        corpus file: load() on THAT path must succeed and return real text
        -- proving refusal is about being unmanifested, not about load()
        being broken outright."""
        real_file = REDTEAM_ROOT / "corpus" / "clean" / "secret-exfil" / "001.txt"
        self.assertTrue(real_file.is_file(), f"negative_control fixture missing: {real_file}")
        mod = _load_freeze_module()
        text = mod.load("clean/secret-exfil/001.txt")
        self.assertGreater(len(text), 0)
        self.assertEqual(text, real_file.read_text(encoding="utf-8"))

    def test_load_refuses_a_hash_mismatch_even_if_path_is_manifested(self):
        with tempfile.TemporaryDirectory() as td:
            work = _copy_redteam_tree(pathlib.Path(td) / "redteam")
            target = work / "corpus" / "clean" / "secret-exfil" / "001.txt"
            target.write_text(target.read_text(encoding="utf-8") + "TAMPERED", encoding="utf-8")
            spec = importlib.util.spec_from_file_location(
                "redteam_freeze_work", work / "bin" / "freeze.py",
            )
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
            with self.assertRaises(mod.CorpusNotFrozen):
                mod.load("clean/secret-exfil/001.txt")


if __name__ == "__main__":
    unittest.main()
