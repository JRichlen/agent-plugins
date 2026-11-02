"""Static install-unit checks; never install a host/plugin or call a model."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("installation", ROOT / "ci/check_installation.py")
installation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installation)


class Installation(unittest.TestCase):
    def test_advertised_resources_and_generated_table_match(self):
        inventory = json.loads((ROOT / "docs/installation-routes.json").read_text(encoding="utf-8"))
        self.assertEqual(installation.check(ROOT, inventory), [])
        page = (ROOT / "docs/installation.md").read_text(encoding="utf-8")
        block = page.split(installation.BEGIN)[1].split(installation.END)[0].strip()
        self.assertEqual(block, installation.table(inventory))

    def test_skill_copy_does_not_preserve_package_relative_resources(self):
        # A named related method is an advisory reference, not an installed
        # dependency. This explicit Core file, however, is a required resource.
        skill = ROOT / "plugins/delegated-intelligence/skills/delegated-intelligence"
        with self.assertRaisesRegex(ValueError, "escaping required resource"):
            installation.contained_file(skill, "../../context/OPERATING.md")
        self.assertTrue((skill / "../../context/OPERATING.md").is_file())
        starter = ROOT / "plugins/find-before-build/skills/find-before-build"
        self.assertEqual(installation.contained_file(starter, "SKILL.md"), starter / "SKILL.md")

    def test_structure_cannot_be_promoted_to_native_qualification(self):
        inventory = json.loads((ROOT / "docs/installation-routes.json").read_text(encoding="utf-8"))
        changed = copy.deepcopy(inventory)
        changed["routes"][1]["qualified_os"] = ["Windows"]
        self.assertTrue(any("cannot qualify" in error for error in installation.check(ROOT, changed)))

    def test_starter_effects_change_requires_review(self):
        inventory = json.loads((ROOT / "docs/installation-routes.json").read_text(encoding="utf-8"))
        original = next(route for route in inventory["routes"] if route["id"] == "claude-session")
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            route = copy.deepcopy(original)
            route["unit"] = "."
            route["required"] = [".claude-plugin/plugin.json"]
            manifest = root / ".claude-plugin/plugin.json"
            manifest.parent.mkdir()
            manifest.write_text('{"hooks": "./run.json"}', encoding="utf-8")
            changed = {**inventory, "routes": [route]}
            self.assertTrue(any("effects" in error for error in installation.check(root, changed)))


if __name__ == "__main__":
    unittest.main()
