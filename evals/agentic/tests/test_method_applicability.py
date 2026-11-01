"""Task-selected guidance applicability, without grading fixture evidence."""
import dataclasses
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from evals.agentic.framework import pairing, registry
from evals.agentic.framework.contract import Card, Capability, ContractError, Estimand

ROOT = Path(__file__).resolve().parents[3]

def card(card_id):
    path = next((ROOT / "evals/agentic/tasks").glob(f"*/{card_id}/card.json"))
    doc = json.loads(path.read_text(encoding="utf-8"))
    return Card.from_dict({f.name: doc[f.name] for f in dataclasses.fields(Card) if f.name in doc})

class SelectedMethodApplicability(unittest.TestCase):
    def classify(self, value, estimand=Estimand.GUIDANCE_ONLY):
        ref = next(r for r in registry.derive_roster(ROOT) if r.name == value.plugin)
        with tempfile.TemporaryDirectory() as tmp:
            arm = pairing.build_arm(value, estimand, (ref,), workspace=Path(tmp))
            return pairing.is_degenerate(arm, value)

    def test_claim_only_methods_do_not_inherit_sibling_script_degeneracy(self):
        for name in ("verify-before-claim-pos-01", "verify-before-claim-near-01", "verify-before-claim-neg-01"):
            with self.subTest(card=name):
                self.assertFalse(self.classify(card(name)))

    def test_package_survey_keeps_full_inventory_outside_claim_task(self):
        value = card("verify-before-claim-pos-01")
        self.assertEqual([(c.kind, c.name) for c in value.capabilities], [("skill", "verify-before-claim")])
        manifest = json.loads((ROOT / "evals/agentic/manifests/arms/verify-before-claim.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["arm_source_survey"], "verify-before-claim-survey-00")
        ref = next(r for r in registry.derive_roster(ROOT) if r.name == value.plugin)
        keys = lambda items: {(c.kind, c.name, c.source_plugin) for c in items}
        actual = tuple(Capability.from_dict(c) for c in manifest["full_package_arm"]["capabilities"])
        self.assertEqual(keys(actual), keys(pairing.discover_plugin_capabilities(ref, ROOT)))

    def test_selected_acceptance_script_is_withheld_from_guidance(self):
        self.assertTrue(self.classify(card("redgate-pos-01")))

    def test_full_package_is_not_a_withheld_guidance_arm(self):
        self.assertFalse(self.classify(card("redgate-pos-01"), Estimand.FULL_PACKAGE))

    def test_mixed_package_survey_is_explicitly_task_dependent(self):
        self.assertNotIn("verify-before-claim", pairing.SCRIPT_DOMINANT_PLUGINS)
        with patch.object(pairing, "survey_version_estimand_targets", return_value=[]):
            summary = pairing.estimand_availability(ROOT)
        self.assertTrue(summary["verify-before-claim"]["guidance-only"].startswith("task-dependent"))

    def test_nonexistent_selected_procedure_fails_instead_of_claiming_degeneracy(self):
        value = card("redgate-pos-01")
        with tempfile.TemporaryDirectory() as tmp:
            ref = next(r for r in registry.derive_roster(ROOT) if r.name == value.plugin)
            arm = pairing.build_arm(value, Estimand.GUIDANCE_ONLY, (ref,), workspace=Path(tmp))
            fake = dataclasses.replace(value, capabilities=(Capability(name="absent.sh", kind="script", source_plugin=value.plugin, generic_equivalent="manual"),))
            with self.assertRaises(ContractError):
                pairing.is_degenerate(arm, fake)

if __name__ == "__main__": unittest.main()
