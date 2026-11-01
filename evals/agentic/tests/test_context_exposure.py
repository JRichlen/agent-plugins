"""Generated package context is exposed without broadening repository access."""
import dataclasses
import hashlib
import json
import pathlib
import tempfile
import unittest

from evals.agentic.framework import pairing, registry, io
from evals.agentic.framework.contract import Card, ContractError, Estimand, ExposureParityViolation

ROOT = pathlib.Path(__file__).resolve().parents[3]


class PackageContextExposure(unittest.TestCase):
    def test_selected_package_context_is_materialized_with_exact_hashes(self):
        ref = next(r for r in registry.derive_roster(ROOT) if r.name == "delegated-intelligence")
        doc = json.loads((ROOT / "evals/agentic/tasks/delegated-intelligence/delegated-intelligence-pos-01/card.json").read_text())
        io.load_schema("card").validate(doc)
        card = Card.from_dict({k:v for k,v in doc.items() if k not in {"paraphrases", "baseline_framing"}})
        with tempfile.TemporaryDirectory() as tmp:
            workspace = pathlib.Path(tmp)
            full = pairing.build_arm(card, Estimand.FULL_PACKAGE, (ref,), workspace=workspace)
            baseline = pairing.build_arm(card, Estimand.BASELINE, (), workspace=workspace)
            for name in ("OPERATING.md", "ownership.json"):
                rel = "context/" + name
                self.assertIn(rel, full.realized_tree)
                self.assertEqual(full.realized_tree[rel], hashlib.sha256((ROOT / ref.directory / rel).read_bytes()).hexdigest())
            pairing.assert_exposure_parity(full, baseline)
            for rel in ("context/../outside.json", "core/OPERATING.md", "context/forged.json"):
                with self.subTest(path=rel):
                    altered = dataclasses.replace(baseline, realized_tree={**baseline.realized_tree, rel: "f" * 64})
                    with self.assertRaises(ExposureParityViolation):
                        pairing.assert_exposure_parity(full, altered)

    def test_owned_context_copy_rejects_escape_and_conflicting_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp) / "repo"
            context = repo / "plugins/sample/context"
            context.mkdir(parents=True)
            (context / "OPERATING.md").write_text("owned operating rules", encoding="utf-8")
            output = pathlib.Path(tmp) / "output"
            written = {}
            pairing._materialize_plugin_context("sample", repo, output, written)
            self.assertEqual((output / "context/OPERATING.md").read_text(), "owned operating rules")
            with self.assertRaises(ContractError):
                pairing._materialize_plugin_context("../outside", repo, output, written)
            (context / "OPERATING.md").write_text("different rules", encoding="utf-8")
            with self.assertRaises(ContractError):
                pairing._materialize_plugin_context("sample", repo, output, written)
            (context / "execute.sh").write_text("exit 0", encoding="utf-8")
            with self.assertRaises(ContractError):
                pairing._materialize_plugin_context("sample", repo, pathlib.Path(tmp)/"clean", {})


if __name__ == "__main__":
    unittest.main()
