"""Offline recovery preserves provenance and excludes retired identities."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("recovery", ROOT / "evals/paid/recover_examples.py")
recovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recovery)


class Recovery(unittest.TestCase):
    def test_real_capture_preserves_unknown_time_and_source_rows(self):
        with tempfile.TemporaryDirectory(prefix="gallery-recovery-") as folder:
            root = Path(folder)
            repo = root / "repo"
            (repo / ".claude-plugin").mkdir(parents=True)
            (repo / ".claude-plugin/marketplace.json").write_text(json.dumps({"plugins": [{"name": "scope-fence"}]}), encoding="utf-8")
            destination = repo / "evals/paid/capture-example.sh"
            destination.parent.mkdir(parents=True)
            shutil.copyfile(ROOT / "evals/paid/capture-example.sh", destination)
            pack = repo / "plugins/scope-fence/evals/promptfoo"
            pack.mkdir(parents=True)
            (pack / "promptfooconfig.yaml").write_text("defaultTest:\n  options:\n    provider:\n      id: anthropic:messages:claude-test\n", encoding="utf-8")
            for args in (("init", "-q"), ("add", "."), ("-c", "user.name=Recovery test", "-c", "user.email=recovery@example.invalid", "commit", "-qm", "source")):
                subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)
            sha = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
            inputs = root / "inputs"
            for name in ("scope-fence", "jori"):
                result = inputs / name / "evals/promptfoo/results.json"
                result.parent.mkdir(parents=True)
                rows = [{"id": side, "vars": {"skill": skill, "question": "same"}, "provider": {"id": "openrouter:qwen/test"}, "response": {"output": side}, "success": True} for side, skill in (("real-id", "actual"), ("stub-id", "calibration"))]
                result.write_text(json.dumps({"results": {"results": rows}}), encoding="utf-8")
            output = root / "output"
            receipt = recovery.recover(repo, inputs, output, sha, "1", "2", "2026-11-01T00:00:00Z", os.environ.get("TEST_BASH", "bash"))
            self.assertEqual(receipt["captured"], ["scope-fence"])
            data = json.loads((output / "scope-fence.json").read_text(encoding="utf-8"))
            provenance = data["provenance"]
            self.assertEqual(provenance["source"], "promptfoo-recovered")
            self.assertEqual(provenance["captured_at"], "unknown")
            self.assertTrue(provenance["attestation"].startswith("none"))
            self.assertEqual(provenance["source_rows"]["without_skill"], {"index": 1, "id": "stub-id"})
            self.assertRegex(provenance["results_sha256"], r"^[0-9a-f]{64}$")
            self.assertRegex(provenance["source_config_sha256"], r"^[0-9a-f]{64}$")
            self.assertEqual(provenance["commit"], sha)
            self.assertFalse((output / "jori.json").exists())
            with self.assertRaisesRegex(ValueError, "empty"):
                recovery.recover(repo, inputs, output, sha, "1", "2", "2026-11-01T00:00:00Z")


if __name__ == "__main__":
    unittest.main()
