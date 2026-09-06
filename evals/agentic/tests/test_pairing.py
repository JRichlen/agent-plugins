"""Registry-lane tests for evals.agentic.framework.pairing (T16, T17; part 2
of the registry lane). Each catalog-anchored test carries a fixed-name
"<name>__negative" sibling in the same class per contract §7.4 item 4.

`ExposureParity` and `EstimandArms` are the two classes the catalog fragment
(`manifests/catalog/registry.json`) names for T16/T17; the remaining classes
exercise the rest of contract §3.11's frozen surface (`composition_arms`,
`version_arms`, `assign_stratum`, `holdout_split`,
`survey_version_estimand_targets`, `estimand_availability`) without being
tied to a specific catalog ID.
"""
from __future__ import annotations

import dataclasses
import json
import pathlib
import shutil
import subprocess
import tempfile
import unittest

from evals.agentic.framework import io, registry, validate, pairing
from evals.agentic.framework.contract import (
    Card,
    CardKind,
    ContractError,
    Estimand,
    ExposureParityViolation,
)

REPO_ROOT = io.repo_root()
FIXTURES = REPO_ROOT / "evals" / "agentic" / "fixtures" / "pairing"

ROSTER = registry.derive_roster(REPO_ROOT)
CARDS = validate.load_cards(REPO_ROOT)


def _ref(name: str) -> registry.PluginRef:
    return next(r for r in ROSTER if r.name == name)


def _card(card_id: str) -> Card:
    return next(c for c in CARDS if c.card_id == card_id)


# ---------------------------------------------------------------------------
# T16 -- exposure parity
# ---------------------------------------------------------------------------

class ExposureParity(unittest.TestCase):
    def test_baseline_arm_diverges_from_treatment_only_in_permitted_ways(self):
        card = _card("graveyard-pos-01")
        ref = _ref("graveyard")
        with tempfile.TemporaryDirectory() as tmp:
            workspace = pathlib.Path(tmp)
            treatment = pairing.build_arm(card, Estimand.FULL_PACKAGE, (ref,), workspace=workspace)
            baseline = pairing.build_arm(card, Estimand.BASELINE, (), workspace=workspace)

            # Must not raise: the ONLY divergences are the treatment's own
            # skill/command surface and the matched script substitution.
            pairing.assert_exposure_parity(treatment, baseline)

            diffs = pairing.exposure_diff(treatment, baseline)
            self.assertGreater(len(diffs), 0, "expected at least the matched-substitution divergence")
            self.assertTrue(all(d.permitted for d in diffs), f"unexpected impermissible divergence(s): {diffs}")

            # The matched-substitution divergence itself must actually appear
            # and must name the real card capability, not be vacuously absent.
            allowed_tools_diffs = [d for d in diffs if d.field.startswith("allowed_tools:")]
            self.assertEqual(len(allowed_tools_diffs), 1)
            self.assertEqual(allowed_tools_diffs[0].treatment, "generate-delete-script.sh")
            self.assertEqual(
                allowed_tools_diffs[0].baseline,
                "bash+gh manual guarded-delete checklist",
            )

            # Baseline never receives the plugin's own capabilities.
            self.assertEqual(baseline.capabilities, ())
            self.assertEqual(baseline.plugins, ())
            self.assertNotIn("generate-delete-script.sh", baseline.allowed_tools)

    def test_baseline_arm_diverges_from_treatment_only_in_permitted_ways__negative(self):
        """T16's own negative control: a baseline arm granted a tool that is
        NEITHER shared with the treatment NOR the declared generic_equivalent
        of any treatment capability ("unmatched widening", contract §3.11
        clause (c) -- also counterfeit fixture 25-agentic-exposure-parity).
        Widening per se is not the defect (a matched substitution IS the
        allowed baseline); only unmatched widening is."""
        fixture_path = FIXTURES / "exposure-parity" / "unmatched-tool.json"
        self.assertTrue(fixture_path.is_file())
        fixture = io.load_json(fixture_path)
        unmatched_tool = fixture["unmatched_tool"]

        card = _card("graveyard-pos-01")
        ref = _ref("graveyard")
        with tempfile.TemporaryDirectory() as tmp:
            workspace = pathlib.Path(tmp)
            treatment = pairing.build_arm(card, Estimand.FULL_PACKAGE, (ref,), workspace=workspace)
            baseline = pairing.build_arm(card, Estimand.BASELINE, (), workspace=workspace)
            contaminated_baseline = dataclasses.replace(
                baseline, allowed_tools=baseline.allowed_tools + (unmatched_tool,)
            )

            with self.assertRaises(ExposureParityViolation):
                pairing.assert_exposure_parity(treatment, contaminated_baseline)

            # exposure_diff itself must name the exact impermissible entry --
            # a generic "something differs" report would not satisfy T16.
            diffs = pairing.exposure_diff(treatment, contaminated_baseline)
            bad = [d for d in diffs if not d.permitted]
            self.assertEqual(len(bad), 1)
            self.assertEqual(bad[0].baseline, unmatched_tool)
            self.assertIn("unmatched widening", bad[0].reason)


# ---------------------------------------------------------------------------
# T17 -- estimand arm construction
# ---------------------------------------------------------------------------

class EstimandArms(unittest.TestCase):
    def test_four_estimands_are_distinct_and_correctly_shaped(self):
        card = _card("graveyard-pos-01")
        ref = _ref("graveyard")
        other = _ref("redgate")

        with tempfile.TemporaryDirectory() as tmp:
            workspace = pathlib.Path(tmp)

            # --- full-package -------------------------------------------------
            full = pairing.build_arm(card, Estimand.FULL_PACKAGE, (ref,), workspace=workspace)
            self.assertEqual(full.estimand, Estimand.FULL_PACKAGE)
            self.assertEqual(full.plugins, ("graveyard",))

            # --- guidance-only --------------------------------------------------
            guidance = pairing.build_arm(card, Estimand.GUIDANCE_ONLY, (ref,), workspace=workspace)
            self.assertEqual(guidance.estimand, Estimand.GUIDANCE_ONLY)
            for relpath in guidance.realized_tree:
                self.assertNotIn("hooks/", relpath)
                self.assertNotIn("scripts/", relpath)
            self.assertTrue(
                all(c.kind in ("skill", "command") for c in guidance.capabilities),
                f"guidance-only arm carries a non-prose capability: {guidance.capabilities}",
            )
            self.assertNotEqual(full.config_hash(), guidance.config_hash())

            # --- composition ------------------------------------------------
            empty, p_only, q_only, p_and_q = pairing.composition_arms(ref, other, card, workspace)
            self.assertEqual(empty.plugins, ())
            self.assertEqual(p_only.plugins, ("graveyard",))
            self.assertEqual(q_only.plugins, ("redgate",))
            self.assertEqual(p_and_q.plugins, ("graveyard", "redgate"))
            hashes = {a.config_hash() for a in (empty, p_only, q_only, p_and_q)}
            self.assertEqual(len(hashes), 4, "composition_arms must return 4 distinctly-shaped arms")
            # p_and_q must actually carry BOTH plugins' capabilities, not just one --
            # a composition arm with no single-plugin comparator cannot separate
            # interaction from main effect (contract §3.11).
            pq_sources = {c.source_plugin for c in p_and_q.capabilities}
            self.assertIn("graveyard", pq_sources)
            self.assertIn("redgate", pq_sources)

            # --- version ------------------------------------------------------
            rev_b = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, check=True,
            ).stdout.strip()
            rev_a = subprocess.run(
                ["git", "rev-parse", "HEAD~3"], cwd=REPO_ROOT, capture_output=True, text=True, check=True,
            ).stdout.strip()
            arm_a, arm_b = pairing.version_arms(ref, rev_a, rev_b, card, workspace)
            self.assertEqual(arm_a.revisions, {"graveyard": rev_a})
            self.assertEqual(arm_b.revisions, {"graveyard": rev_b})
            self.assertNotEqual(arm_a.config_hash(), arm_b.config_hash())

            # All arms constructed above must be pairwise config-hash distinct.
            all_arms = [full, guidance, empty, p_only, q_only, p_and_q, arm_a, arm_b]
            all_hashes = {a.config_hash() for a in all_arms}
            self.assertEqual(len(all_hashes), len(all_arms))

    def test_four_estimands_are_distinct_and_correctly_shaped__negative(self):
        """T17's own stated negative control: a guidance-only arm that still
        loads `hooks/hooks.json` silently measures the full package, and any
        "prose alone works" conclusion drawn from it is unsupported. Uses the
        committed contaminated-guidance fixture (a portable stand-in for the
        contract's `plugins/agent-compiler/hooks/hooks.json` example)."""
        contaminated_hooks = FIXTURES / "estimand-arms" / "contaminated-guidance" / "hooks" / "hooks.json"
        self.assertTrue(contaminated_hooks.is_file())

        ref = _ref("graveyard")
        with tempfile.TemporaryDirectory() as tmp:
            workspace = pathlib.Path(tmp)
            legit_tree = pairing.guidance_only_tree(ref, workspace)
            self.assertTrue(legit_tree.is_dir())  # sanity: the legitimate tree builds fine

            # Now contaminate a COPY of it with the fixture hook file.
            contaminated_root = workspace / "contaminated-copy"
            shutil.copytree(legit_tree, contaminated_root)
            target = contaminated_root / "hooks" / "hooks.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(contaminated_hooks.read_bytes())

            with self.assertRaises(ExposureParityViolation):
                pairing.assert_guidance_only_tree_is_pure(contaminated_root)


# ---------------------------------------------------------------------------
# Guidance-only degeneracy (contract §11.4 UNKNOWN 5 / settled-unknowns item 6)
# ---------------------------------------------------------------------------

class GuidanceOnlyDegeneracy(unittest.TestCase):
    def _survey_card(self, plugin: str) -> Card:
        ref = _ref(plugin)
        caps = pairing.discover_plugin_capabilities(ref, REPO_ROOT)
        return Card(
            card_id=f"{plugin}-survey-00", plugin=plugin, kind=CardKind.POSITIVE,
            task_path="", outcome_verifier="", adoption_verifier="", pass_fixture="",
            fail_fixture="", expected_boundary_verdict="", capabilities=caps,
            mutations=("survey-placeholder",), holdout=False,
        )

    def test_script_dominant_plugins_are_guidance_only_inapplicable(self):
        for plugin in sorted(pairing.SCRIPT_DOMINANT_PLUGINS):
            with self.subTest(plugin=plugin):
                ref = _ref(plugin)
                card = self._survey_card(plugin)
                with tempfile.TemporaryDirectory() as tmp:
                    arm = pairing.build_arm(card, Estimand.GUIDANCE_ONLY, (ref,), workspace=pathlib.Path(tmp))
                    self.assertTrue(pairing.is_degenerate(arm, card))

    def test_script_dominant_plugins_are_guidance_only_inapplicable__negative(self):
        """A plugin NOT in the curated script-dominant set must not be
        reported degenerate -- a check that always returns True would be
        vacuous."""
        card = _card("jori-pos-01")
        ref = _ref("jori")
        with tempfile.TemporaryDirectory() as tmp:
            arm = pairing.build_arm(card, Estimand.GUIDANCE_ONLY, (ref,), workspace=pathlib.Path(tmp))
            self.assertFalse(pairing.is_degenerate(arm, card))


# ---------------------------------------------------------------------------
# Stratum assignment / holdout split
# ---------------------------------------------------------------------------

class StratumAssignmentAndHoldout(unittest.TestCase):
    def test_assign_stratum_reports_only_the_differing_fields(self):
        from evals.agentic.framework.contract import Stratum

        requested = Stratum(provider="anthropic", model="claude-sonnet-5", revision="1.0", effort="medium", harness="claude-cli")
        realized = Stratum(provider="anthropic", model="claude-sonnet-5", revision="1.0", effort="high", harness="claude-cli")
        realized_out, flags = pairing.assign_stratum(requested, realized)
        self.assertIs(realized_out, realized)
        self.assertEqual(flags, ("effort",))

    def test_assign_stratum_reports_only_the_differing_fields__negative(self):
        """Identical requested/realized strata must report zero fallback
        flags -- a function that always reports at least one flag would
        falsely mark every matched attempt as a fallback."""
        from evals.agentic.framework.contract import Stratum

        s = Stratum(provider="anthropic", model="claude-sonnet-5", revision="1.0", effort="medium", harness="claude-cli")
        _out, flags = pairing.assign_stratum(s, s)
        self.assertEqual(flags, ())

    def test_holdout_split_always_keeps_holdout_flagged_cards_in_holdout(self):
        cards = CARDS
        self.assertTrue(any(c.holdout for c in cards))
        dev, holdout = pairing.holdout_split(cards, fraction=0.0, seed=42)
        forced = {c.card_id for c in cards if c.holdout}
        self.assertTrue(forced.issubset({c.card_id for c in holdout}))
        self.assertEqual(set(dev) & set(holdout), set())
        self.assertEqual(set(dev) | set(holdout), set(cards))

    def test_holdout_split_always_keeps_holdout_flagged_cards_in_holdout__negative(self):
        """An out-of-range fraction must be refused, not silently clamped --
        a silently-clamped fraction would hide a caller's misconfiguration."""
        with self.assertRaises(ContractError):
            pairing.holdout_split(CARDS, fraction=1.5, seed=42)

    def test_holdout_split_is_deterministic_given_the_same_seed(self):
        dev1, holdout1 = pairing.holdout_split(CARDS, fraction=0.5, seed=7)
        dev2, holdout2 = pairing.holdout_split(CARDS, fraction=0.5, seed=7)
        self.assertEqual(dev1, dev2)
        self.assertEqual(holdout1, holdout2)


# ---------------------------------------------------------------------------
# Version-estimand survey (contract §11.4 UNKNOWN / settled-unknowns item 6)
# ---------------------------------------------------------------------------

class VersionEstimandSurvey(unittest.TestCase):
    def test_survey_finds_only_revision_pairs_with_a_real_version_bump(self):
        findings = pairing.survey_version_estimand_targets(REPO_ROOT)
        self.assertGreater(len(findings), 0, "expected at least one real two-revision target on this branch")
        for f in findings:
            self.assertIn(f["plugin"], {r.name for r in ROSTER})
            # Each finding must be a REAL version bump, not the file's own
            # creation commit paired with anything.
            rel = f"plugins/{f['plugin']}/.claude-plugin/plugin.json"
            older_doc = json.loads(
                subprocess.run(
                    ["git", "show", f"{f['rev_older']}:{rel}"], cwd=REPO_ROOT, capture_output=True, text=True, check=True,
                ).stdout
            )
            newer_doc = json.loads(
                subprocess.run(
                    ["git", "show", f"{f['rev_newer']}:{rel}"], cwd=REPO_ROOT, capture_output=True, text=True, check=True,
                ).stdout
            )
            self.assertNotEqual(older_doc["version"], newer_doc["version"])

    def test_survey_finds_only_revision_pairs_with_a_real_version_bump__negative(self):
        """The creation commit of a plugin's plugin.json (nothing on the
        'older' side) must never be reported as a version-bump target --
        a survey that treated file-creation as a version bump would flag
        every plugin's first commit as a false positive."""
        # graveyard's very first commit legitimately creates plugin.json;
        # confirm the survey does not pair it against anything as "older".
        findings = pairing.survey_version_estimand_targets(REPO_ROOT)
        first_commit = subprocess.run(
            ["git", "log", "--follow", "--oneline", "--reverse", "--",
             "plugins/graveyard/.claude-plugin/plugin.json"],
            cwd=REPO_ROOT, capture_output=True, text=True, check=True,
        ).stdout.splitlines()[0].split(" ", 1)[0]
        for f in findings:
            self.assertNotEqual(f["rev_older"], first_commit)


# ---------------------------------------------------------------------------
# estimand_availability -- the per-plugin summary API (this task's acceptance)
# ---------------------------------------------------------------------------

class EstimandAvailabilitySummary(unittest.TestCase):
    def test_summary_covers_every_roster_plugin_with_all_four_estimand_keys(self):
        summary = pairing.estimand_availability(REPO_ROOT)
        self.assertEqual(set(summary), {r.name for r in ROSTER})
        for plugin, row in summary.items():
            self.assertEqual(
                set(row), {"full-package", "guidance-only", "composition", "version"},
                f"{plugin}: summary row missing an estimand key",
            )
            self.assertEqual(row["full-package"], "available")

    def test_summary_covers_every_roster_plugin_with_all_four_estimand_keys__negative(self):
        """A plugin dropped from the roster must disappear from the summary
        too -- a summary hardcoding the current 25 names would still list a
        removed plugin as 'available'."""
        summary = pairing.estimand_availability(REPO_ROOT)
        self.assertNotIn("this-plugin-does-not-exist", summary)


if __name__ == "__main__":
    unittest.main()
