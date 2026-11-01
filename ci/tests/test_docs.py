import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("docs", ROOT / "ci/check_docs.py")
docs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(docs)


class GuidedDocs(unittest.TestCase):
    def test_real_guided_path_resolves(self):
        self.assertEqual(docs.check(), [])

    def test_missing_target_anchor_and_escape_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            source = root / "source.md"
            source.write_text("# Current source\n", encoding="utf-8")
            self.assertIsNone(docs.check_link(root, source, "#current-source"))
            for target in ("missing.md", "#deleted-heading", "../outside.md"):
                self.assertIsNotNone(docs.check_link(root, source, target))


if __name__ == "__main__":
    unittest.main()
