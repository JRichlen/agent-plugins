import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("docs", ROOT / "ci/check_docs.py")
docs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(docs)


class GuidedDocs(unittest.TestCase):
    def test_markdown_anchor_and_link_forms(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "source.md"
            path.write_text('# Same `code` [link](else.md) ###\n# Same `code` [link](else.md)\n<a name="manual"></a>\n~~~md\n# Ignored\n~~~\n', encoding="utf-8")
            self.assertEqual(docs.anchors(path), {"same-code-link", "same-code-link-1", "manual"})
        links = docs.markdown_links('[title](<target.md#head> "Title")\n[full][id]\n[id][]\n[id]\n[id]: target.md#head "Title"\n~~~\n[ignored](bad.md)\n~~~\n<a href="html.md">HTML</a>')
        self.assertEqual(links.count("target.md#head"), 4)
        self.assertIn("html.md", links)
        self.assertNotIn("bad.md", links)

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
