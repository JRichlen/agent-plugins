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
            # Uses the FULL discovered capability set (skill/command/script),
            # not just graveyard-pos-01's single card-curated script
            # capability: a script-kind capability never gets a
            # realized_tree footprint by design (see
            # _materialize_capability), so a version comparison built from
            # ONLY a script capability is structurally vacuous regardless of
            # revisions -- exactly what pairing.version_arms now correctly
            # refuses to build (CV-06). The root commit vs HEAD guarantees a
            # real difference (the skill/command files did not exist yet at
            # the root commit) without depending on recent, arbitrary commit
            # history actually having touched graveyard.
            rev_b = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, check=True,
            ).stdout.strip()
            rev_a = subprocess.run(
                ["git", "rev-list", "--max-parents=0", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, check=True,
            ).stdout.strip().splitlines()[-1]
            full_caps_card = dataclasses.replace(card, capabilities=pairing.discover_plugin_capabilities(ref, REPO_ROOT))
            arm_a, arm_b = pairing.version_arms(ref, rev_a, rev_b, full_caps_card, workspace)
            self.assertEqual(arm_a.revisions, {"graveyard": rev_a})
            self.assertEqual(arm_b.revisions, {"graveyard": rev_b})
            self.assertNotEqual(arm_a.config_hash(), arm_b.config_hash())
            self.assertNotEqual(dict(arm_a.realized_tree), dict(arm_b.realized_tree))

            # All arms constructed above must be pairwise config-hash distinct
            # -- EXCEPT `full` and `p_only`, which are the exact same
            # configuration (graveyard alone, FULL_PACKAGE role) built two
            # different ways (build_arm directly vs. composition_arms) and
            # are legitimately expected to collide now that config_hash no
            # longer includes the nondeterministic arm_id (CV-06); `p_only`
            # is already exercised for distinctness against its composition
            # siblings above.
            self.assertEqual(full.config_hash(), p_only.config_hash())
            all_arms = [full, guidance, empty, q_only, p_and_q, arm_a, arm_b]
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


# ---------------------------------------------------------------------------
# CV-05: a capability that names a non-existent plugin surface
# ---------------------------------------------------------------------------

class CapabilityMustResolveOnDisk(unittest.TestCase):
    def test_materializing_a_bogus_skill_capability_raises(self):
        """A card capability's `name` is a REAL surface name, not free-text
        prose about the capability -- prose belongs in `generic_equivalent`.
        Silently writing nothing (the old behavior) let 69 of 75 corpus
        cards carry a capability that materialized zero files with no
        error anywhere."""
        from evals.agentic.framework.contract import Capability
        ref = _ref("voice")
        bogus = Capability(
            name="this skill does not exist on disk", kind="skill",
            source_plugin="voice", generic_equivalent="some prose",
        )
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ContractError):
                pairing._materialize_capability(bogus, REPO_ROOT, pathlib.Path(tmp), {})

    def test_materializing_a_bogus_skill_capability_raises__negative(self):
        """Negative control: the REAL skill name for the same plugin
        materializes without error and produces real file content --
        proving the rejection above is about the bogus name, not that
        materialization has been made unconditionally strict."""
        from evals.agentic.framework.contract import Capability
        real = Capability(name="human-voice", kind="skill", source_plugin="voice", generic_equivalent=None)
        with tempfile.TemporaryDirectory() as tmp:
            written: dict[str, str] = {}
            pairing._materialize_capability(real, REPO_ROOT, pathlib.Path(tmp), written)
            self.assertGreater(len(written), 0)

    def test_every_corpus_cards_curated_capability_resolves_on_disk(self):
        """Sweeps the full corpus: no card may declare a capability whose
        (kind, name) does not resolve to a real surface under its own
        plugin's directory. This is exactly the 69/75 defect CV-05 found,
        made permanent so it cannot silently regress card-by-card."""
        for card in CARDS:
            with self.subTest(card=card.card_id):
                ref = _ref(card.plugin)
                for cap in card.capabilities:
                    if cap.kind not in ("skill", "command", "hook", "mcp", "script", "tool"):
                        continue
                    with tempfile.TemporaryDirectory() as tmp:
                        try:
                            pairing._materialize_capability(cap, REPO_ROOT, pathlib.Path(tmp), {})
                        except ContractError as exc:
                            self.fail(f"{card.card_id}: capability {cap.name!r} ({cap.kind}) does not resolve: {exc}")


class ArmNonVacuity(unittest.TestCase):
    def test_treatment_with_no_files_and_no_divergence_is_rejected(self):
        """CV-05: a treatment arm that materializes nothing and diverges
        from its baseline nowhere is indistinguishable from that baseline
        by construction -- exactly the state all 25 FULL_PACKAGE arms were
        in before this repair (every card's capability silently failed to
        materialize)."""
        # A treatment arm with the SAME shape as its own baseline (no
        # capabilities, no tools beyond the shared generic set, no tree) is
        # vacuous by definition.
        with tempfile.TemporaryDirectory() as tmp:
            ws = pathlib.Path(tmp)
            baseline = pairing.build_arm(_card("graveyard-pos-01"), Estimand.BASELINE, (), workspace=ws)
            vacuous_treatment = dataclasses.replace(baseline, arm_id=pairing.new_id("arm-vacuous-test"))
            with self.assertRaises(ContractError):
                pairing.assert_arm_is_nonvacuous(vacuous_treatment, baseline)

    def test_treatment_with_no_files_and_no_divergence_is_rejected__negative(self):
        """Negative control: graveyard's REAL full-package arm has zero
        realized_tree footprint too (its only capability is script-kind,
        which never materializes files by design), but it DOES diverge from
        baseline via the matched allowed_tools substitution -- so it must
        NOT be rejected as vacuous. A check that rejects any empty
        realized_tree outright, with no OR-exposure-diff escape hatch,
        would wrongly reject every script-dominant plugin's real, valid
        treatment arm."""
        card = _card("graveyard-pos-01")
        ref = _ref("graveyard")
        with tempfile.TemporaryDirectory() as tmp:
            ws = pathlib.Path(tmp)
            treatment = pairing.build_arm(card, Estimand.FULL_PACKAGE, (ref,), workspace=ws)
            baseline = pairing.build_arm(card, Estimand.BASELINE, (), workspace=ws)
            self.assertEqual(treatment.realized_tree, {})
            pairing.assert_arm_is_nonvacuous(treatment, baseline)  # must not raise


# ---------------------------------------------------------------------------
# CV-06: config_hash must not be inflated by the nondeterministic arm_id
# ---------------------------------------------------------------------------

class ConfigHashExcludesArmId(unittest.TestCase):
    def test_two_arms_differing_only_in_arm_id_hash_equal(self):
        card = _card("graveyard-pos-01")
        with tempfile.TemporaryDirectory() as tmp:
            ws = pathlib.Path(tmp)
            a = pairing.build_arm(card, Estimand.BASELINE, (), workspace=ws)
            b = dataclasses.replace(a, arm_id=pairing.new_id("arm-baseline"))
            self.assertNotEqual(a.arm_id, b.arm_id)
            self.assertEqual(a.config_hash(), b.config_hash())

    def test_two_arms_differing_only_in_arm_id_hash_equal__negative(self):
        """Negative control: a REAL configuration difference (different
        allowed_tools) still changes config_hash -- proving the equality
        above is specifically about arm_id, not that config_hash has been
        made to ignore everything."""
        card = _card("graveyard-pos-01")
        with tempfile.TemporaryDirectory() as tmp:
            ws = pathlib.Path(tmp)
            a = pairing.build_arm(card, Estimand.BASELINE, (), workspace=ws)
            b = dataclasses.replace(a, allowed_tools=a.allowed_tools + ("SomeExtraTool",))
            self.assertNotEqual(a.config_hash(), b.config_hash())

    def test_version_arms_raises_when_both_revisions_materialize_the_same_tree(self):
        """CV-06's exact reproduction: the SAME revision on both sides of a
        version comparison must not silently produce 'two distinct arms'
        (previously guaranteed only by the nondeterministic arm_id)."""
        ref = _ref("jori")
        card = _card("jori-pos-01")
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ContractError):
                pairing.version_arms(ref, head, head, card, pathlib.Path(tmp))

    def test_version_arms_raises_when_both_revisions_materialize_the_same_tree__negative(self):
        """Negative control: two revisions that genuinely differ (the root
        commit, before the plugin's skill file existed, vs HEAD) build
        distinct, non-raising arms -- proving the rejection above is about
        the revisions being identical, not that version_arms has been made
        to always refuse."""
        ref = _ref("jori")
        full_caps_card = dataclasses.replace(_card("jori-pos-01"), capabilities=pairing.discover_plugin_capabilities(ref, REPO_ROOT))
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
        root_commit = subprocess.run(
            ["git", "rev-list", "--max-parents=0", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip().splitlines()[-1]
        with tempfile.TemporaryDirectory() as tmp:
            arm_a, arm_b = pairing.version_arms(ref, root_commit, head, full_caps_card, pathlib.Path(tmp))
            self.assertNotEqual(dict(arm_a.realized_tree), dict(arm_b.realized_tree))


# ---------------------------------------------------------------------------
# CV-16: arm_id must be reproducible from configuration, not a fresh uuid4
# ---------------------------------------------------------------------------

ARMS_DIR = REPO_ROOT / "evals" / "agentic" / "manifests" / "arms"


class CommittedManifestsAreReproducible(unittest.TestCase):
    """CV-16: `manifests/arms/graveyard.json` is a DERIVED artifact
    (`manifests/arms/README.md`); nothing previously checked that
    re-deriving it from the exact same configuration reproduces the
    committed file. `pairing.deterministic_arm_id` makes `arm_id` a pure
    function of configuration (see its docstring for why `realized_tree`
    cannot be part of that digest), so rebuilding a committed manifest's
    two arms from the same card must now reproduce both `arm_id`s AND both
    `config_hash()`es exactly."""

    def test_rebuilding_graveyard_reproduces_the_committed_arm_ids(self):
        committed = json.loads((ARMS_DIR / "graveyard.json").read_text())
        card = _card("graveyard-pos-01")
        ref = _ref("graveyard")
        with tempfile.TemporaryDirectory() as tmp:
            ws = pathlib.Path(tmp)
            full = pairing.build_arm(card, Estimand.FULL_PACKAGE, (ref,), workspace=ws)
            base = pairing.build_arm(card, Estimand.BASELINE, (), workspace=ws)
        self.assertEqual(full.arm_id, committed["full_package_arm"]["arm_id"])
        self.assertEqual(base.arm_id, committed["baseline_arm"]["arm_id"])
        # config_hash is independently deterministic too (CV-06 + CV-16
        # together): rebuilding twice must agree with itself as well as
        # with the committed arm_id.
        self.assertEqual(
            full.config_hash(),
            dataclasses.replace(full, arm_id=pairing.new_id("arm-full-graveyard")).config_hash(),
        )

    def test_rebuilding_graveyard_reproduces_the_committed_arm_ids__negative(self):
        """Negative control: this is not a vacuous always-equal check --
        mutating the configuration (one extra allowed_tool) before minting
        the id changes it, so a REAL drift between the committed manifest
        and what the code would build today is exactly what this class
        would catch."""
        committed = json.loads((ARMS_DIR / "graveyard.json").read_text())
        card = _card("graveyard-pos-01")
        ref = _ref("graveyard")
        with tempfile.TemporaryDirectory() as tmp:
            ws = pathlib.Path(tmp)
            full = pairing.build_arm(card, Estimand.FULL_PACKAGE, (ref,), workspace=ws)
        mutated_id = pairing.deterministic_arm_id(
            "arm-full-graveyard", estimand=full.estimand, role=full.role,
            plugins=full.plugins, revisions=full.revisions,
            capabilities=full.capabilities,
            allowed_tools=full.allowed_tools + ("SomeExtraTool",),
            extra_dirs=full.extra_dirs, system_prompt_append=full.system_prompt_append,
        )
        self.assertNotEqual(mutated_id, committed["full_package_arm"]["arm_id"])

    def test_arm_id_is_stable_across_repeated_builds(self):
        """The primitive CV-16 actually requires: two independent calls to
        build_arm with the SAME configuration must mint the SAME arm_id --
        the exact property `new_id`'s uuid4 could never have satisfied."""
        card = _card("jori-pos-01")
        ref = _ref("jori")
        with tempfile.TemporaryDirectory() as tmp1, tempfile.TemporaryDirectory() as tmp2:
            a = pairing.build_arm(card, Estimand.FULL_PACKAGE, (ref,), workspace=pathlib.Path(tmp1))
            b = pairing.build_arm(card, Estimand.FULL_PACKAGE, (ref,), workspace=pathlib.Path(tmp2))
        self.assertEqual(a.arm_id, b.arm_id)

    def test_arm_id_is_stable_across_repeated_builds__negative(self):
        """Negative control: two DIFFERENT plugins' full-package arms must
        not collide -- proving stability isn't from collapsing every
        arm_id to one constant."""
        with tempfile.TemporaryDirectory() as tmp:
            ws = pathlib.Path(tmp)
            a = pairing.build_arm(_card("jori-pos-01"), Estimand.FULL_PACKAGE, (_ref("jori"),), workspace=ws)
            b = pairing.build_arm(_card("graveyard-pos-01"), Estimand.FULL_PACKAGE, (_ref("graveyard"),), workspace=ws)
        self.assertNotEqual(a.arm_id, b.arm_id)


# ---------------------------------------------------------------------------
# CV-10: exposure parity, gated over the FULL roster, not just graveyard
# ---------------------------------------------------------------------------

class ExposureParityFullRoster(unittest.TestCase):
    """run.py's own --gate probe only checks manifests/arms/graveyard.json
    (integration lane, cross-lane fix requested separately) -- this
    registry-owned test sweeps every roster plugin so the corpus itself
    cannot regress into an unmatched baseline widening or a vacuous
    treatment arm undetected."""

    def test_every_roster_plugin_has_permitted_exposure_and_a_nonvacuous_arm(self):
        cards_by_plugin = {c.plugin: c for c in CARDS if c.card_id.endswith("-pos-01")}
        for ref in ROSTER:
            with self.subTest(plugin=ref.name):
                card = cards_by_plugin.get(ref.name)
                with tempfile.TemporaryDirectory() as tmp:
                    ws = pathlib.Path(tmp)
                    if card is None:
                        from evals.agentic.framework.contract import Card, CardKind
                        caps = pairing.discover_plugin_capabilities(ref, REPO_ROOT)
                        card = Card(
                            card_id=f"{ref.name}-survey-00", plugin=ref.name, kind=CardKind.POSITIVE,
                            task_path="", outcome_verifier="", adoption_verifier="", pass_fixture="",
                            fail_fixture="", expected_boundary_verdict="", capabilities=caps,
                            mutations=("survey-placeholder",), holdout=False,
                        )
                    treatment = pairing.build_arm(card, Estimand.FULL_PACKAGE, (ref,), workspace=ws)
                    baseline = pairing.build_arm(card, Estimand.BASELINE, (), workspace=ws)
                    pairing.assert_exposure_parity(treatment, baseline)
                    pairing.assert_arm_is_nonvacuous(treatment, baseline)

    def test_every_roster_plugin_has_permitted_exposure_and_a_nonvacuous_arm__negative(self):
        """Negative control: an unmatched-widening baseline (T16's own
        counterfeit-25 shape) fails this same sweep for a real roster
        plugin -- proving the sweep actually exercises assert_exposure_parity
        rather than vacuously passing every plugin."""
        ref = _ref("jori")
        card = _card("jori-pos-01")
        with tempfile.TemporaryDirectory() as tmp:
            ws = pathlib.Path(tmp)
            treatment = pairing.build_arm(card, Estimand.FULL_PACKAGE, (ref,), workspace=ws)
            baseline = pairing.build_arm(card, Estimand.BASELINE, (), workspace=ws)
            contaminated = dataclasses.replace(baseline, allowed_tools=baseline.allowed_tools + ("AdminOverride",))
            with self.assertRaises(ExposureParityViolation):
                pairing.assert_exposure_parity(treatment, contaminated)


# ---------------------------------------------------------------------------
# CV-11: a skill/command/hook capability's generic_equivalent must not be
# silently discarded -- it becomes the baseline's compensating prose.
# ---------------------------------------------------------------------------

class ProseSubstituteForNonToolCapabilities(unittest.TestCase):
    def test_skill_generic_equivalent_lands_in_baseline_system_prompt_append(self):
        card = _card("voice-pos-01")
        self.assertEqual(card.capabilities[0].kind, "skill")
        self.assertTrue(card.capabilities[0].generic_equivalent)
        with tempfile.TemporaryDirectory() as tmp:
            ws = pathlib.Path(tmp)
            baseline = pairing.build_arm(card, Estimand.BASELINE, (), workspace=ws)
            self.assertEqual(baseline.system_prompt_append, card.capabilities[0].generic_equivalent)
            ref = _ref("voice")
            treatment = pairing.build_arm(card, Estimand.FULL_PACKAGE, (ref,), workspace=ws)
            self.assertEqual(treatment.system_prompt_append, "")
            # The whole point: exposure parity must still hold, because this
            # divergence is the PERMITTED prose substitute, not free widening.
            pairing.assert_exposure_parity(treatment, baseline)

    def test_skill_generic_equivalent_lands_in_baseline_system_prompt_append__negative(self):
        """Negative control: a baseline carrying prose that does NOT match
        the treatment's declared generic_equivalent (unmatched prompt-level
        widening) must still be rejected -- proving CV-11's fix permits
        only the exact compensating text, not any system_prompt_append."""
        card = _card("voice-pos-01")
        ref = _ref("voice")
        with tempfile.TemporaryDirectory() as tmp:
            ws = pathlib.Path(tmp)
            treatment = pairing.build_arm(card, Estimand.FULL_PACKAGE, (ref,), workspace=ws)
            baseline = pairing.build_arm(card, Estimand.BASELINE, (), workspace=ws)
            contaminated = dataclasses.replace(baseline, system_prompt_append="some unrelated prompt injection")
            with self.assertRaises(ExposureParityViolation):
                pairing.assert_exposure_parity(treatment, contaminated)


# ---------------------------------------------------------------------------
# CV-13: a plugin's own skills/commands/agents markdown IS behavior
# ---------------------------------------------------------------------------

class DiffTouchesBehaviorIncludesOwnMarkdown(unittest.TestCase):
    def test_a_skill_md_only_diff_counts_as_behavior(self):
        diff_text = (
            "diff --git a/plugins/demo/skills/demo/SKILL.md b/plugins/demo/skills/demo/SKILL.md\n"
            "index 111..222 100644\n--- a/plugins/demo/skills/demo/SKILL.md\n"
            "+++ b/plugins/demo/skills/demo/SKILL.md\n@@ -1 +1 @@\n-old\n+new\n"
        )
        self.assertTrue(pairing._diff_touches_behavior(diff_text, "plugins/demo"))

    def test_a_skill_md_only_diff_counts_as_behavior__negative(self):
        """Negative control: the plugin's own top-level README.md/AGENTS.md
        is still exempted -- proving the fix narrowed the exclusion rather
        than removing it (a diff touching ONLY those must still read as
        'not behavior')."""
        diff_text = (
            "diff --git a/plugins/demo/README.md b/plugins/demo/README.md\n"
            "index 111..222 100644\n--- a/plugins/demo/README.md\n"
            "+++ b/plugins/demo/README.md\n@@ -1 +1 @@\n-old\n+new\n"
        )
        self.assertFalse(pairing._diff_touches_behavior(diff_text, "plugins/demo"))

    def test_plugin_factory_real_md_only_bump_is_now_a_behavior_changing_target(self):
        """The concrete regression CV-13 cited: plugin-factory's
        de039a6..d02c66c (1.0.0 -> 1.1.0) touches only SKILL.md/
        authoring-checklist.md and was wrongly rejected as 'not behavior'
        under the old blanket .md exclusion."""
        diff = subprocess.run(
            ["git", "diff", "de039a6", "d02c66c", "--", "plugins/plugin-factory"],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        if diff.returncode != 0 or not diff.stdout.strip():
            self.skipTest("reference revisions not present in this checkout's git history")
        self.assertTrue(pairing._diff_touches_behavior(diff.stdout, "plugins/plugin-factory"))


if __name__ == "__main__":
    unittest.main()
