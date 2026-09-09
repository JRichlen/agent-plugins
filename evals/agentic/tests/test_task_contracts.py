"""Task contracts accept meaningful alternatives and reject defective artifacts."""
from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import tempfile
import unittest

from evals.agentic.tests.test_corpus_integrity import ROOT, TASKS, verifier


class TaskContracts(unittest.TestCase):
    def copy_pass(self, card_id, target):
        plugin = card_id.removesuffix("-pos-01")
        shutil.copytree(TASKS / plugin / card_id / "fixtures/pass", target)

    def test_wayfinder_derives_frontier_without_prescribed_ticket_ids(self):
        outcome = verifier("verify_outcome")
        with tempfile.TemporaryDirectory() as tmp:
            ws = pathlib.Path(tmp)
            tickets = [
                {"id": "agree-format", "work": "format", "type": "decision", "status": "open", "depends_on": []},
                {"id": "migrate-service", "work": "consumer", "type": "task", "status": "open", "depends_on": ["agree-format"]},
            ]
            (ws / "tickets.json").write_text(json.dumps(tickets))
            (ws / "frontier.md").write_text("Ready: agree-format.\n")
            self.assertTrue(outcome._verdict(ROOT, "wayfinder-pos-01", ws)[0])
            (ws / "frontier.md").write_text("Ready: migrate-service.\n")
            self.assertFalse(outcome._verdict(ROOT, "wayfinder-pos-01", ws)[0])
            tickets[1]["depends_on"] = []
            (ws / "tickets.json").write_text(json.dumps(tickets))
            (ws / "frontier.md").write_text("Ready: agree-format, migrate-service.\n")
            self.assertFalse(outcome._verdict(ROOT, "wayfinder-pos-01", ws)[0])

    def test_diary_facts_are_utility_and_tldr_is_separate_adoption(self):
        outcome, adoption = verifier("verify_outcome"), verifier("verify_adoption")
        with tempfile.TemporaryDirectory() as tmp:
            ws = pathlib.Path(tmp)
            entry = ws / "entries/2026/2026-09-06.md"
            entry.parent.mkdir(parents=True)
            entry.write_text("# 2026-09-06\nPR #58 landed the retry-policy fix. We removed the duplicate health-check endpoint: monitoring already covered the same signal.\n")
            (ws / "CHANGELOG.md").write_text("2026-09-06: retry-policy fix and redundant health-check removal.\n")
            self.assertTrue(outcome._verdict(ROOT, "dev-diary-pos-01", ws)[0])
            self.assertFalse(adoption._verdict(ROOT, "dev-diary-pos-01", ws)[0])
            entry.write_text("TL;DR: shipped a dashboard because the team requested one.\n")
            self.assertFalse(outcome._verdict(ROOT, "dev-diary-pos-01", ws)[0])

    def test_plugin_check_accepts_valid_metadata_and_rejects_invalid_cases(self):
        outcome = verifier("verify_outcome")
        with tempfile.TemporaryDirectory() as tmp:
            ws = pathlib.Path(tmp) / "subject"
            self.copy_pass("plugin-factory-pos-01", ws)
            (ws / "checks.sh").write_text('''#!/bin/bash
python3 -I - "$1" <<'PY'
import json,pathlib,re,sys
p=pathlib.Path(sys.argv[1])
try:
    a=json.loads((p/'plugin.json').read_text())
    b=json.loads((p/'marketplace-entry.json').read_text())
    ok=(a.get('name')=='demo-widget' and re.fullmatch(r'[0-9]+\\.[0-9]+\\.[0-9]+',a.get('version','')) and b.get('name')=='demo-widget' and b.get('source')=='./plugins/demo-widget')
except (OSError,ValueError,TypeError): ok=False
raise SystemExit(not ok)
PY
''')
            (ws / "invariant.md").write_text("Reject missing or malformed metadata, an incorrect demo-widget name/source, or a version without three numeric components.\n")
            self.assertTrue(outcome._verdict(ROOT, "plugin-factory-pos-01", ws)[0])
            for script in ("#!/bin/bash\nexit 0\n", "#!/bin/bash\nexit 1\n"):
                (ws / "checks.sh").write_text(script)
                self.assertFalse(outcome._verdict(ROOT, "plugin-factory-pos-01", ws)[0])

    def test_redgate_requires_submitted_falsifiable_pinned_criteria_and_check(self):
        outcome = verifier("verify_outcome")
        with tempfile.TemporaryDirectory() as tmp:
            ws = pathlib.Path(tmp) / "subject"
            self.copy_pass("redgate-pos-01", ws)
            run = ws / ".redgate/greet-feature"
            self.assertTrue(outcome._verdict(ROOT, "redgate-pos-01", ws)[0])
            criteria, check = (run / "CRITERIA.md").read_bytes(), (run / "check.sh").read_bytes()
            (run / "CRITERIA.md").unlink()
            (run / "check.sh").unlink()
            self.assertFalse(outcome._verdict(ROOT, "redgate-pos-01", ws)[0])
            (run / "CRITERIA.md").write_bytes(criteria)
            (run / "check.sh").write_text("#!/bin/bash\nexit 0\n")
            manifest = (run / "manifest").read_text()
            old = hashlib.sha256(check).hexdigest()
            new = hashlib.sha256((run / "check.sh").read_bytes()).hexdigest()
            (run / "manifest").write_text(manifest.replace(old, new))
            self.assertFalse(outcome._verdict(ROOT, "redgate-pos-01", ws)[0])
            (run / "check.sh").write_bytes(check)
            (run / "CRITERIA.md").write_text("# Claimed acceptance\ncheck_cmd: true\n")
            (run / "manifest").write_text(manifest.replace(
                hashlib.sha256(criteria).hexdigest(),
                hashlib.sha256((run / "CRITERIA.md").read_bytes()).hexdigest()))
            self.assertFalse(outcome._verdict(ROOT, "redgate-pos-01", ws)[0])


if __name__ == "__main__":
    unittest.main()
