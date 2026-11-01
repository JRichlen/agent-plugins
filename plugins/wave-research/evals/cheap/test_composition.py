"""Operative research instructions compose with current shared owners.

These are source and mutation controls, not behavioral efficacy evidence.
"""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[4]
PLUGIN = Path(__file__).resolve().parents[2]
SKILL = PLUGIN / "skills/wave-research/SKILL.md"

def section(text, title):
    match = re.search(r"(?ms)^## " + re.escape(title) + r"[^\n]*\n(.*?)(?=^## |\Z)", text)
    return " ".join(match.group(1).split()) if match else ""

def violations(text):
    text = re.sub(r"(?s)<!--.*?-->", "", text)
    issues = []
    dependencies = section(text, "When to use this")
    convergence = section(text, "CP2. Converge")
    recovery = section(text, "Search and recovery rules")
    for owner in ("Core contract", "delegated-intelligence", "stop-rule"):
        if owner not in dependencies: issues.append("missing canonical owner: " + owner)
    if "offer-only activation, not merely installation" not in convergence:
        issues.append("optional review activated without offer-only boundary")
    if "do not simulate it or mark the thesis verified" not in convergence:
        issues.append("missing independent-review limitation")
    if "do not relaunch work until authorized again" not in recovery:
        issues.append("active stop does not block relaunch")
    if "availability alone is not permission" not in recovery or "Do not schedule automatically" not in recovery:
        issues.append("scheduler presence grants authority")
    if re.search(r"Haiku|Sonnet|Opus|two retries|Retries: 2|Automatic; no approval|Delegation minimum", text):
        issues.append("competing governance reintroduced")
    return issues

class ResearchComposition(unittest.TestCase):
    def test_operative_skill_composes_with_current_owners(self):
        self.assertEqual(violations(SKILL.read_text(encoding="utf-8")), [])
        owners = json.loads((ROOT / "core/ownership.json").read_text(encoding="utf-8"))
        self.assertEqual(owners["responsibilities"]["optional-second-opinion"]["activation"], ["offer-only"])
        for path in (ROOT / "core/OPERATING.md", ROOT / "plugins/delegated-intelligence/skills/delegated-intelligence/SKILL.md", ROOT / "plugins/stop-rule/skills/stop-rule/SKILL.md"):
            self.assertTrue(path.is_file())

    def test_each_missing_effect_boundary_is_rejected(self):
        source = SKILL.read_text(encoding="utf-8")
        for needle in ("offer-only activation, not merely installation", "do not simulate it or mark the thesis verified", "do not relaunch work until authorized again", "availability alone\n  is not permission"):
            with self.subTest(rule=needle):
                pattern = r"\s+".join(re.escape(word) for word in needle.split())
                self.assertRegex(source, pattern)
                self.assertTrue(violations(re.sub(pattern, "boundary omitted", source)))

    def test_obsolete_governance_is_rejected_in_operative_source(self):
        source = SKILL.read_text(encoding="utf-8")
        for mutation in ("Retries: 2 per task", "Haiku collects", "Automatic; no approval needed"):
            with self.subTest(mutation=mutation):
                self.assertTrue(violations(source + "\n" + mutation + "\n"))

    def test_comments_cannot_fake_an_operative_boundary(self):
        source = SKILL.read_text(encoding="utf-8")
        needle = "offer-only activation, not merely installation"
        self.assertTrue(violations(source.replace(needle, "<!-- " + needle + " -->")))

    def test_entrypoints_load_the_authoritative_method(self):
        for name in ("AGENTS.md", "commands/wave-research.md"):
            self.assertIn("skills/wave-research/SKILL.md", (PLUGIN / name).read_text(encoding="utf-8"))

if __name__ == "__main__": unittest.main()
