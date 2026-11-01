"""Current package ownership must preserve legacy pinned-verification cases."""
import importlib.util
import json
import pathlib
import shutil
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
TASKS = ROOT / "evals/agentic/tasks"
spec = importlib.util.spec_from_file_location("consolidation_adoption", TASKS / "_verifiers/verify_adoption.py")
adoption = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adoption)


class ConsolidationOwnership(unittest.TestCase):
    def test_legacy_case_ids_resolve_to_current_owner(self):
        paths = sorted((TASKS / "redgate").glob("*/card.json"))
        self.assertEqual(len(paths), 8)
        for path in paths:
            card = json.loads(path.read_text(encoding="utf-8"))
            with self.subTest(card=card["card_id"]):
                self.assertEqual(card["plugin"], "verify-before-claim")
                self.assertTrue(card["card_id"].startswith("redgate-"))
                self.assertTrue(all(c["source_plugin"] == "verify-before-claim" for c in card["capabilities"]))
                self.assertEqual(adoption._find_card(ROOT, card["card_id"]), card)

    def test_legacy_pinned_work_uses_run_shape_not_claim_receipt(self):
        card_id = "redgate-pos-01"
        card = adoption._find_card(ROOT, card_id)
        with tempfile.TemporaryDirectory() as tmp:
            ws = pathlib.Path(tmp) / "subject"
            shutil.copytree(ROOT / card["pass_fixture"], ws)
            self.assertTrue(adoption._verdict(ROOT, card_id, ws)[0])
            shutil.rmtree(ws / ".redgate")
            (ws / "claim.md").write_text("CHECK: module_test.py; tests passed\n", encoding="utf-8")
            self.assertFalse(adoption._verdict(ROOT, card_id, ws)[0])

    def test_retired_products_have_no_active_cards_or_arms(self):
        for name in ("jori", "fleet-playbook-curator"):
            self.assertFalse((TASKS / name).exists())
            self.assertFalse((ROOT / "evals/agentic/manifests/arms" / (name + ".json")).exists())


if __name__ == "__main__":
    unittest.main()
