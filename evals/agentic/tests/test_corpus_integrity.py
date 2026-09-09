"""Adversarial seams for task evidence, independent of committed happy paths."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import shutil
import tempfile
import unittest
from unittest import mock

from evals.agentic.framework import controls, io, validate
from evals.agentic.framework.contract import VacuousVerifier

ROOT = io.repo_root()
TASKS = ROOT / "evals/agentic/tasks"


def verifier(name):
    path = TASKS / "_verifiers" / (name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CorpusEvidenceIntegrity(unittest.TestCase):
    def test_correctly_hashed_generic_events_prove_no_plugin_workflow(self):
        adoption = verifier("verify_adoption")
        for p in sorted(TASKS.glob("*/*-pos-01/card.json")):
            card = json.loads(p.read_text())
            with self.subTest(card=card["card_id"]), tempfile.TemporaryDirectory() as tmp:
                ws = pathlib.Path(tmp)
                digest = hashlib.sha256((ROOT / card["pass_fixture"] / "guard.sh").read_bytes()).hexdigest()
                (ws / "events.jsonl").write_text(
                    json.dumps({"at": 1, "op": "backup", "digest": digest}) + "\n"
                    + json.dumps({"at": 2, "op": "delete"}) + "\n"
                )
                self.assertFalse(adoption._verdict(ROOT, card["card_id"], ws)[0])

    def test_voice_rejects_empty_framing_and_unsupported_specifics(self):
        outcome = verifier("verify_outcome")
        for text in ("Verdict: ", "Verdict: Bananas travel quietly on Tuesday.",
                     "Verdict: switch to LRU; the cache uses insertion order and that is why it is slow."):
            with self.subTest(text=text), tempfile.TemporaryDirectory() as tmp:
                ws = pathlib.Path(tmp)
                (ws / "response.md").write_text(text)
                self.assertFalse(outcome._verdict(ROOT, "voice-pos-01", ws)[0])

    def test_voice_accepts_faithful_rewrite_without_literal_verdict_marker(self):
        outcome = verifier("verify_outcome")
        with tempfile.TemporaryDirectory() as tmp:
            ws = pathlib.Path(tmp)
            (ws / "response.md").write_text("The cache's eviction policy is making it slow. Improve that policy to address the performance problem.")
            self.assertTrue(outcome._verdict(ROOT, "voice-pos-01", ws)[0])

    def test_diagnosis_claim_and_noop_test_do_not_prove_fix(self):
        outcome = verifier("verify_outcome")
        with tempfile.TemporaryDirectory() as tmp:
            ws = pathlib.Path(tmp)
            (ws / "hypotheses.md").write_text("1. Claim: fixed.\nFalsifying test: yes\n")
            (ws / "test_parse_duration.py").write_text("def test_nothing():\n    pass\n")
            (ws / "parse_duration.py").write_text("def parse_duration(s):\n    return 90000\n")
            self.assertFalse(outcome._verdict(ROOT, "diagnosing-bugs-pos-01", ws)[0])

    def test_verification_claim_without_module_does_not_prove_tests(self):
        outcome = verifier("verify_outcome")
        with tempfile.TemporaryDirectory() as tmp:
            ws = pathlib.Path(tmp)
            (ws / "claim.md").write_text("CHECK: ran tests: OK\nCLAIM: tests pass\n")
            self.assertFalse(outcome._verdict(ROOT, "verify-before-claim-pos-01", ws)[0])

    def test_missing_direct_solution_is_never_injected_from_fixtures(self):
        outcome = verifier("verify_outcome")
        # These pass/fail fixtures share the actual deliverable bytes. It must
        # still be supplied by the subject; agreement is not a helper declaration.
        for card_id in ("graveyard-neg-01", "jori-neg-01", "orchestrate-neg-01"):
            with self.subTest(card=card_id), tempfile.TemporaryDirectory() as tmp:
                self.assertFalse(outcome._verdict(ROOT, card_id, pathlib.Path(tmp))[0])

    def test_real_positive_artifacts_work_without_generic_ledger(self):
        adoption = verifier("verify_adoption")
        for p in sorted(TASKS.glob("*/*-pos-01/card.json")):
            card = json.loads(p.read_text())
            with self.subTest(card=card["card_id"]), tempfile.TemporaryDirectory() as tmp:
                ws = pathlib.Path(tmp) / "subject"
                shutil.copytree(ROOT / card["pass_fixture"], ws)
                (ws / "events.jsonl").unlink(missing_ok=True)
                self.assertTrue(adoption._verdict(ROOT, card["card_id"], ws)[0])
                controls.apply_mutation("remove-workflow-artifacts", ws)
                self.assertFalse(adoption._verdict(ROOT, card["card_id"], ws)[0])

    def test_graveyard_accepts_independently_written_equivalent_script(self):
        outcome = verifier("verify_outcome")
        script = '''#!/bin/bash
if gh api repos/acme/graveyard/contents/old-tool/old-tool.bundle >/dev/null 2>&1; then
    gh repo delete acme/old-tool --yes
fi
echo 'empty-scratch is intentionally unbundled (zero commits)'
gh repo delete acme/empty-scratch --yes
'''
        with tempfile.TemporaryDirectory() as tmp:
            ws = pathlib.Path(tmp)
            (ws / "delete-originals.sh").write_text(script)
            self.assertTrue(outcome._verdict(ROOT, "graveyard-pos-01", ws)[0])
            # The same script with its existence check replaced must fail in
            # the absent-bundle simulation even if happy-path deletion works.
            (ws / "delete-originals.sh").write_text(script.replace("gh api repos/acme/graveyard/contents/old-tool/old-tool.bundle", "true"))
            self.assertFalse(outcome._verdict(ROOT, "graveyard-pos-01", ws)[0])

    def test_executable_subject_cannot_read_reference_fixtures_or_host_env(self):
        outcome = verifier("verify_outcome")
        with tempfile.TemporaryDirectory() as tmp:
            result = outcome._sandbox(ROOT, pathlib.Path(tmp), ["python3", "-c", "import os,pathlib; assert not pathlib.Path('/repo/evals/agentic/tasks/voice/voice-pos-01/fixtures/pass').exists(); assert 'OPENAI_API_KEY' not in os.environ; assert not pathlib.Path('/home').exists()"])
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_graveyard_archive_requires_a_restorable_full_history_bundle(self):
        outcome = verifier("verify_outcome")
        card = json.loads((TASKS / "graveyard/graveyard-pos-02/card.json").read_text())
        with tempfile.TemporaryDirectory() as tmp:
            ws = pathlib.Path(tmp) / "subject"
            shutil.copytree(ROOT / card["pass_fixture"], ws)
            self.assertTrue(outcome._verdict(ROOT, card["card_id"], ws)[0])
            (ws / "archive/legacy-service.bundle").write_text("Backup complete. All history preserved.\n")
            self.assertFalse(outcome._verdict(ROOT, card["card_id"], ws)[0])

    def test_designated_task_inputs_are_mounted_read_only(self):
        outcome = verifier("verify_outcome")
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            inputs, ws = root / "inputs", root / "workspace"
            inputs.mkdir(); ws.mkdir()
            (inputs / "source.txt").write_text("unchanged")
            result = outcome._sandbox(ROOT, ws, ["python3", "-c", "from pathlib import Path; p=Path('/inputs/source.txt'); assert p.read_text()=='unchanged'; p.write_text('tampered')"], readonly_inputs=inputs)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Read-only file system", result.stderr)
            self.assertEqual((inputs / "source.txt").read_text(), "unchanged")

    def test_compiler_output_cannot_change_the_requested_effect_scope(self):
        outcome = verifier("verify_outcome")
        card = json.loads((TASKS / "agent-compiler/agent-compiler-pos-01/card.json").read_text())
        with tempfile.TemporaryDirectory() as tmp:
            ws = pathlib.Path(tmp) / "subject"
            shutil.copytree(ROOT / card["pass_fixture"], ws)
            self.assertTrue(outcome._verdict(ROOT, card["card_id"], ws)[0])
            query = json.loads((ws / "query.json").read_text())
            query["effectCeiling"].append("scm:write")
            (ws / "query.json").write_text(json.dumps(query))
            self.assertFalse(outcome._verdict(ROOT, card["card_id"], ws)[0])

    def test_control_resolver_binds_identity_and_rejects_already_red_baselines(self):
        card = validate.validate_card(json.loads((TASKS / "voice/voice-pos-01/card.json").read_text()))
        self.assertTrue(controls._resolve_verifier(card.outcome_verifier, card_id=card.card_id)(ROOT / card.pass_fixture))
        with mock.patch.object(controls, "_resolve_verifier", return_value=lambda ws: False):
            with self.assertRaisesRegex(VacuousVerifier, "no true baseline"):
                controls.assert_not_vacuous(card, ROOT / card.pass_fixture)

    def test_limiter_utility_is_behavior_independent_of_design_artifacts(self):
        outcome, adoption = verifier("verify_outcome"), verifier("verify_adoption")
        card = json.loads((TASKS / "codebase-design/codebase-design-pos-01/card.json").read_text())
        with tempfile.TemporaryDirectory() as tmp:
            ws = pathlib.Path(tmp) / "subject"
            shutil.copytree(ROOT / card["pass_fixture"], ws)
            shutil.rmtree(ws / "docs")
            self.assertTrue(outcome._verdict(ROOT, card["card_id"], ws)[0])
            self.assertFalse(adoption._verdict(ROOT, card["card_id"], ws)[0])
            (ws / "rate_limiter.py").write_text("class RateLimiter:\n    def __init__(self, *args): pass\n    def allow(self, key='default'): return True\n")
            self.assertFalse(outcome._verdict(ROOT, card["card_id"], ws)[0])

    def test_retry_utility_is_behavior_independent_of_search_receipt(self):
        outcome, adoption = verifier("verify_outcome"), verifier("verify_adoption")
        card = json.loads((TASKS / "find-before-build/find-before-build-pos-01/card.json").read_text())
        with tempfile.TemporaryDirectory() as tmp:
            ws = pathlib.Path(tmp) / "subject"
            shutil.copytree(ROOT / card["pass_fixture"], ws)
            (ws / "RECEIPT.md").unlink()
            self.assertTrue(outcome._verdict(ROOT, card["card_id"], ws)[0])
            self.assertFalse(adoption._verdict(ROOT, card["card_id"], ws)[0])
            (ws / "client.py").write_text("def fetch(client, url):\n    return client.get(url)\n")
            self.assertFalse(outcome._verdict(ROOT, card["card_id"], ws)[0])

    def test_cache_recommendation_has_no_hardcoded_winner(self):
        outcome = verifier("verify_outcome")
        with tempfile.TemporaryDirectory() as tmp:
            ws = pathlib.Path(tmp)
            (ws / "outcome.md").write_text("Recommendation: in-process LRU, provisionally, for a small single-process deployment needing simple local caching. Memcached transaction support remains unverified and did not determine this recommendation.")
            self.assertTrue(outcome._verdict(ROOT, "orchestrate-pos-01", ws)[0])

    def test_undo_requires_executable_rehearsal_not_zero_difference_claim(self):
        outcome = verifier("verify_outcome")
        card = json.loads((TASKS / "prove-the-undo/prove-the-undo-pos-01/card.json").read_text())
        with tempfile.TemporaryDirectory() as tmp:
            ws = pathlib.Path(tmp) / "subject"
            shutil.copytree(ROOT / card["pass_fixture"], ws)
            self.assertTrue(outcome._verdict(ROOT, card["card_id"], ws)[0])
            (ws / "rehearse.sh").write_text("#!/bin/bash\necho '0 differences; restored successfully'\n")
            self.assertFalse(outcome._verdict(ROOT, card["card_id"], ws)[0])


if __name__ == "__main__":
    unittest.main()
