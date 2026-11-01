"""Offline recovery preserves provenance and excludes retired identities."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ci.host_tools import select_bash
import copy

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("recovery", ROOT / "evals/paid/recover_examples.py")
recovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recovery)


class Recovery(unittest.TestCase):
    def test_recovery_provenance_requires_actual_field_formats(self):
        data = json.loads((ROOT / "docs/examples/data/stop-rule.json").read_text(encoding="utf-8"))["provenance"]
        self.assertEqual(recovery.validate_recovered(data), [])
        for key, value in (("commit", "wrong"), ("results_sha256", True), ("source_config_sha256", "short"), ("artifact_id", 42), ("recovered_at", "2026-11-01"), ("artifact_path", "../outside"), ("source_rows", {"with_skill": {"index": True, "id": []}, "without_skill": {"index": -1, "id": None}})):
            changed = copy.deepcopy(data)
            changed[key] = value
            with self.subTest(field=key):
                self.assertTrue(recovery.validate_recovered(changed))

    def test_recovered_passes_refer_to_distinct_rubrics_and_inputs(self):
        for name in ("agent-compiler", "find-before-build", "semver-gate", "stop-rule", "wayfinder"):
            with self.subTest(plugin=name):
                data = json.loads((ROOT / "docs/examples/data" / (name + ".json")).read_text(encoding="utf-8"))
                self.assertTrue(data["with_skill"]["graded"]["pass"])
                self.assertTrue(data["without_skill"]["graded"]["pass"])
                self.assertTrue(data["with_skill"]["criteria"])
                self.assertTrue(data["without_skill"]["criteria"])
                self.assertNotEqual(data["with_skill"]["criteria"], data["without_skill"]["criteria"])
                self.assertIn("2ff596caf3be9fd59ebfe42d17b05ccab1f1da1d", data["provenance"]["source_config_url"])
        stop = json.loads((ROOT / "docs/examples/data/stop-rule.json").read_text(encoding="utf-8"))
        self.assertNotEqual(stop["with_skill"]["comparison_inputs"], stop["without_skill"]["comparison_inputs"])
        page = (ROOT / "docs/examples/index.html").read_text(encoding="utf-8")
        self.assertIn("grades use different rubrics", page)
        self.assertIn("not a common quality scale", page)
        self.assertNotIn("those tests do not discriminate improvement", page)

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
            receipt = recovery.recover(repo, inputs, output, sha, "1", "2", "2026-11-01T00:00:00Z", select_bash())
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
            self.assertEqual(receipt["status"], "complete")
            self.assertEqual(next(item for item in receipt["items"] if item["plugin"] == "jori")["status"], "skipped")
            self.assertEqual(json.loads((output / "recovery-receipt.json").read_text(encoding="utf-8")), receipt)
            with self.assertRaisesRegex(ValueError, "empty"):
                recovery.recover(repo, inputs, output, sha, "1", "2", "2026-11-01T00:00:00Z")
            # A second active input with no historical config must not discard
            # the valid pair or disappear from the machine-readable receipt.
            marketplace = repo / ".claude-plugin/marketplace.json"
            marketplace.write_text(json.dumps({"plugins": [{"name": "scope-fence"}, {"name": "broken"}, {"name": "missing"}]}), encoding="utf-8")
            broken = inputs / "broken/evals/promptfoo/results.json"
            broken.parent.mkdir(parents=True)
            broken.write_text("invalid JSON", encoding="utf-8")
            partial = recovery.recover(repo, inputs, root / "partial", sha, "1", "2", "2026-11-01T00:00:00Z", select_bash())
            self.assertEqual(partial["status"], "partial_failure")
            self.assertEqual(partial["captured"], ["scope-fence"])
            self.assertEqual({item["plugin"]: item["status"] for item in partial["items"]}, {"broken": "failed", "jori": "skipped", "missing": "skipped", "scope-fence": "captured"})


if __name__ == "__main__":
    unittest.main()
