"""Free comparison planning tests. Rates below are synthetic arithmetic fixtures."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("comparison", ROOT / "evals/experiments/plan.py")
comparison = importlib.util.module_from_spec(spec)
spec.loader.exec_module(comparison)


class ComparisonPlan(unittest.TestCase):
    def setUp(self):
        self.models = json.loads((ROOT / "evals/experiments/models.json").read_text(encoding="utf-8"))
        self.suites = {"schema_version": 1, "suites": {"fixture-v1": {"source_commit": "a" * 40,
            "kind": "synthetic arithmetic only", "files": {"task.txt": comparison.hashlib.sha256(b"fixture").hexdigest()},
            "cases": {"first": {}, "second": {}}, "arms": ["skill", "no_skill"]}}}
        self.experiment = {"schema_version": 1, "limits": {"subject_attempts": 100, "judge_attempts": 100, "estimated_usd": "10"}, "cells": [{
            "id": "explicit-cell", "suite": "fixture-v1", "subject": "qwen-configured", "judge": "haiku45-configured",
            "cases": ["first"], "arms": ["skill", "no_skill"], "repeats": 3, "max_attempts": 2,
            "execution_mode": "sync", "token_bounds": {"subject_input": 1000, "subject_output": 1000, "judge_input": 1000, "judge_output": 1000}}]}

    def run_plan(self, source=b"fixture"):
        return comparison.plan(self.models, self.suites, self.experiment, lambda _commit, _path: source)

    def test_explicit_cells_repeats_and_retry_bound_without_cross_product(self):
        result = self.run_plan()
        self.assertEqual(result["attempt_bounds"], {"subject": 12, "judge": 12})
        self.assertEqual(len(result["cells"]), 1)
        self.assertIsNone(result["estimated_usd"])
        self.assertFalse(result["execution_enabled"])

    def test_synthetic_cost_math_and_spend_cap(self):
        for model in self.models["models"].values():
            model["pricing"] = {"input_per_million": "1", "output_per_million": "2", "evidence": "synthetic fixture; not a market rate"}
        self.assertEqual(self.run_plan()["estimated_usd"], "0.072")
        self.experiment["limits"]["estimated_usd"] = "0.071"
        with self.assertRaisesRegex(ValueError, "cost exceeds"):
            self.run_plan()

    def test_caps_same_family_drift_and_typo_fail_closed(self):
        original = copy.deepcopy(self.experiment)
        self.experiment["limits"]["subject_attempts"] = 11
        with self.assertRaisesRegex(ValueError, "attempt cap"):
            self.run_plan()
        self.experiment = original
        with self.assertRaisesRegex(ValueError, "frozen suite drift"):
            self.run_plan(source=b"edited fixture")
        self.models["models"]["haiku45-configured"]["family"] = "qwen"
        with self.assertRaisesRegex(ValueError, "same-family"):
            self.run_plan()
        self.models["models"]["haiku45-configured"]["family"] = "anthropic"
        self.experiment["cells"][0]["repeat"] = 3
        with self.assertRaisesRegex(ValueError, "unknown fields"):
            self.run_plan()

    def test_batch_has_no_silent_sync_fallback(self):
        self.experiment["cells"][0]["execution_mode"] = "provider_batch"
        with self.assertRaisesRegex(ValueError, "unsupported.*no sync fallback"):
            self.run_plan()

    def test_replay_has_no_new_subject_attempts_and_needs_identity(self):
        self.experiment["cells"][0].update(execution_mode="replay", saved_outputs={"path": "saved.json", "sha256": "b" * 64})
        self.assertEqual(self.run_plan()["attempt_bounds"], {"subject": 0, "judge": 12})
        self.experiment["cells"][0]["saved_outputs"]["sha256"] = "unknown"
        with self.assertRaisesRegex(ValueError, "exact file identity"):
            self.run_plan()


if __name__ == "__main__":
    unittest.main()
