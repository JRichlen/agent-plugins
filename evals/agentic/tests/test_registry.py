"""Registry-lane tests for evals.agentic.framework.registry and .validate
(T11, T12, T18). Each catalog-anchored test carries a fixed-name
"<name>__negative" sibling in the same class per contract §7.4 item 4.

test_corpus.py (T13, T14, T15) runs against every card actually present under
tasks/**, so cards added later are automatically covered; this module covers
roster derivation, the suite-catalog merge/resolve machinery, coverage
reporting, and sampling integrity (holdout + leakage), none of which depend
on how many cards exist yet.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import tempfile
import unittest

from evals.agentic.framework import io, registry, validate
from evals.agentic.framework.contract import (
    ApprovalGate,
    Card,
    CardKind,
    CatalogUnresolvable,
    ContractError,
    CoverageGap,
    EvidenceClass,
    LeakageDetected,
    Manifest,
    VacuousVerifier,
)

REPO_ROOT = io.repo_root()
FIXTURES = REPO_ROOT / "evals" / "agentic" / "fixtures" / "pairing"

REFERENCE_PLUGINS = ("graveyard", "redgate", "voice", "jori")


# ---------------------------------------------------------------------------
# T11 -- roster derivation
# ---------------------------------------------------------------------------

class RosterDerivation(unittest.TestCase):
    def test_roster_length_and_names_are_derived_from_marketplace(self):
        roster = registry.derive_roster(REPO_ROOT)
        marketplace = io.load_json(REPO_ROOT / ".claude-plugin" / "marketplace.json")
        expected_names = {p["name"] for p in marketplace["plugins"]}

        self.assertEqual(len(roster), 25)
        self.assertEqual({r.name for r in roster}, expected_names)
        for ref in roster:
            plugin_dir = REPO_ROOT / ref.directory
            self.assertTrue(plugin_dir.is_dir(), f"{ref.name}: {plugin_dir} does not exist")
            manifest = io.load_json(plugin_dir / ".claude-plugin" / "plugin.json")
            self.assertEqual(manifest["name"], ref.name)

    def test_roster_length_and_names_are_derived_from_marketplace__negative(self):
        """T11's own negative control (contract's exact wording): add a 26th
        plugin to a fixture marketplace and the roster must grow to 26 -- a
        test asserting len(roster) == 25 against a frozen constant would pass
        forever and is exactly the metadata check T11 forbids."""
        fixture_root = FIXTURES / "roster" / "26-plugins"
        roster = registry.derive_roster(fixture_root)
        self.assertEqual(len(roster), 26)
        self.assertIn("fixture-plugin-00", {r.name for r in roster})
        self.assertIn("fixture-plugin-25", {r.name for r in roster})

    def test_no_hardcoded_plugin_name_list_in_registry_source(self):
        """A grep-shaped check: registry.py's source must not contain a
        literal roster (a comma/list-joined enumeration of the 25 real
        plugin names) anywhere. A single incidental mention (e.g. in a
        docstring example) is fine; all 25 appearing together would mean
        someone pasted in a frozen roster."""
        roster = registry.derive_roster(REPO_ROOT)
        names = [r.name for r in roster]
        source = (REPO_ROOT / "evals" / "agentic" / "framework" / "registry.py").read_text()
        hits = sum(1 for name in names if name in source)
        self.assertLess(
            hits, len(names),
            "registry.py's source mentions every roster plugin name -- looks hardcoded",
        )


# ---------------------------------------------------------------------------
# Suite-catalog merge/resolve machinery (§7), tested against a SYNTHETIC
# repo_root since manifests/catalog/index.json is integration-owned and has
# not landed yet in this worktree -- see this module's docstring / the final
# report's deviation note.
# ---------------------------------------------------------------------------

def _write_json(path: pathlib.Path, doc) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2))


def _dummy_entry(entry_id: str, lane: str) -> dict:
    return {
        "id": entry_id, "lane": lane,
        "module": "evals.agentic.tests.test_registry", "test_class": "RosterDerivation",
        "test_name": "test_roster_length_and_names_are_derived_from_marketplace",
        "evidence_class": "framework", "approval_gate": "none",
        "negative_control": "evals/agentic/fixtures/pairing/roster/26-plugins",
        "requires_real_marketplace": False, "reentrant_unsafe": False,
    }


def _synthetic_catalog_root(tmp: pathlib.Path, *, duplicate: bool = False, wrong_lane: bool = False) -> pathlib.Path:
    """A full, valid (all 52 IDs, no gaps) synthetic catalog, split T01-T11
    into "core" and T12-T52 into "registry" -- content is irrelevant (every
    entry points at the same real, resolvable test method); only the
    index/fragment BOOKKEEPING is under test here, not per-ID semantics."""
    from evals.agentic.framework.contract import ALL_IDS

    root = tmp / "repo"
    (root / ".claude-plugin").mkdir(parents=True)
    _write_json(root / ".claude-plugin" / "marketplace.json", {"name": "x", "plugins": []})
    catalog_dir = root / registry.CATALOG_DIR

    core_ids = [i for i in ALL_IDS if i <= "T11"]
    registry_ids = [i for i in ALL_IDS if i > "T11"]
    index = {"ids": {"core": core_ids, "registry": registry_ids}}
    _write_json(catalog_dir / "index.json", index)

    core_entries = [_dummy_entry(i, "core") for i in core_ids]
    _write_json(catalog_dir / "core.json", {"lane": "core", "entries": core_entries})

    t11_lane = "core" if wrong_lane else "registry"
    registry_entries = [_dummy_entry(i, "registry") for i in registry_ids]
    if wrong_lane:
        # T11 is allocated to "registry" by index.json but the fragment
        # entry claims lane "core" -- must be refused, not silently merged.
        registry_entries[0] = _dummy_entry(registry_ids[0], "core")
    if duplicate:
        registry_entries.append(_dummy_entry(core_ids[0], "registry"))  # collides with a core id
    _write_json(catalog_dir / "registry.json", {"lane": "registry", "entries": registry_entries})
    return root


class CatalogMergeAndResolve(unittest.TestCase):
    def test_load_catalog_merges_two_lane_fragments(self):
        from evals.agentic.framework.contract import ALL_IDS

        with tempfile.TemporaryDirectory() as tmp:
            root = _synthetic_catalog_root(pathlib.Path(tmp))
            catalog = registry.load_catalog(root)
            self.assertEqual(set(catalog.entries), set(ALL_IDS))
            self.assertEqual(catalog.entries["T12"].lane, "registry")
            self.assertEqual(catalog.entries["T01"].lane, "core")
            self.assertEqual(len(catalog.digest), 64)
            self.assertEqual(catalog.missing_ids(), ())
            self.assertEqual(len(catalog.by_lane("core")), 11)
            self.assertEqual(len(catalog.by_lane("registry")), 41)
            self.assertEqual(catalog.gated(), ())

    def test_load_catalog_merges_two_lane_fragments__negative(self):
        """Negative control: a fragment that claims an ID allocated to a
        DIFFERENT lane in index.json must be refused, not silently merged."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _synthetic_catalog_root(pathlib.Path(tmp), wrong_lane=True)
            with self.assertRaises(CatalogUnresolvable):
                registry.load_catalog(root)

    def test_load_catalog_rejects_duplicate_ids_across_fragments(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _synthetic_catalog_root(pathlib.Path(tmp), duplicate=True)
            with self.assertRaises(CatalogUnresolvable):
                registry.load_catalog(root)

    def test_resolve_test_and_run_entry_execute_a_real_passing_entry(self):
        entry = registry.CatalogEntry(
            id="T11", lane="registry",
            module="evals.agentic.tests.test_registry", test_class="RosterDerivation",
            test_name="test_roster_length_and_names_are_derived_from_marketplace",
            evidence_class=EvidenceClass.FRAMEWORK, approval_gate=ApprovalGate.NONE,
            negative_control=str((FIXTURES / "roster" / "26-plugins").relative_to(REPO_ROOT)),
            requires_real_marketplace=False, reentrant_unsafe=False,
        )
        cls, name = registry.resolve_test(entry)
        self.assertIs(cls, RosterDerivation)
        run = registry.run_entry(entry)
        self.assertTrue(run.executed)
        self.assertEqual(run.outcome, "pass")
        self.assertGreaterEqual(run.assertions, 1)

    def test_resolve_test_and_run_entry_execute_a_real_passing_entry__negative(self):
        """An entry naming a test method that does not exist must not
        resolve -- CatalogUnresolvable, never a silent pass."""
        entry = registry.CatalogEntry(
            id="T11", lane="registry",
            module="evals.agentic.tests.test_registry", test_class="RosterDerivation",
            test_name="test_this_method_does_not_exist",
            evidence_class=EvidenceClass.FRAMEWORK, approval_gate=ApprovalGate.NONE,
            negative_control=str((FIXTURES / "roster" / "26-plugins").relative_to(REPO_ROOT)),
            requires_real_marketplace=False, reentrant_unsafe=False,
        )
        with self.assertRaises(CatalogUnresolvable):
            registry.resolve_test(entry)
        run = registry.run_entry(entry)
        self.assertFalse(run.executed)
        self.assertEqual(run.outcome, "error")


# ---------------------------------------------------------------------------
# T12 -- card triplet completeness and card-schema validity
# ---------------------------------------------------------------------------

class TripletCompleteness(unittest.TestCase):
    def test_reference_plugins_have_all_three_card_kinds(self):
        """Named for T12's frozen catalog test_name, but -- registry lane
        part 3 -- now checks the whole 25-plugin roster, not just the four
        reference plugins: the corpus is complete, and a test that only
        ever looked at graveyard/redgate/voice/jori would keep passing
        forever even if every other plugin silently lost a card kind."""
        cards = validate.load_cards(REPO_ROOT)
        roster = registry.derive_roster(REPO_ROOT)
        coverage = validate.coverage_report(cards, roster)

        self.assertGreaterEqual(coverage.total_cards, len(roster) * 3)
        for ref in roster:
            self.assertIn(ref.name, coverage.per_plugin)
            counts = coverage.per_plugin[ref.name]
            for kind in CardKind:
                self.assertGreaterEqual(
                    counts[kind], 1,
                    f"{ref.name} is missing a {kind.value} card",
                )
        self.assertEqual(coverage.missing, ())

        # the four reference plugins remain covered too (kept as a named
        # subset check since REFERENCE_PLUGINS anchors other tests in this
        # module).
        for plugin in REFERENCE_PLUGINS:
            self.assertIn(plugin, coverage.per_plugin)

    def test_reference_plugins_have_all_three_card_kinds__negative(self):
        """Contract's own T12 negative control: 'a plugin with a positive
        card and two stub cards whose verifiers are return True' must not
        count as complete -- completeness by file existence alone is a
        metadata check, caught jointly with T15's vacuity rule. Uses the
        committed stub-identical-verifiers fixture (T12/T15 shared control)."""
        stub_path = FIXTURES / "vacuous-cards" / "stub-identical-verifiers" / "card.json"
        self.assertTrue(stub_path.is_file())
        doc = io.load_json(stub_path)
        with self.assertRaises(VacuousVerifier):
            validate.validate_card(doc)

    def test_assert_triplet_completeness_passes_for_the_now_complete_corpus(self):
        """Honest state check, updated for registry lane part 3: the corpus
        is now complete across all 25 plugins (>=75 cards, no missing
        plugin/kind cell), so the roster-wide gate must NOT raise. This
        replaces the interim assertion (kept as this method's ``__negative``
        sibling below) that covered the earlier 4/25 partial state -- it must
        never regress to reading complete only because a handful of
        reference plugins are done."""
        cards = validate.load_cards(REPO_ROOT)
        roster = registry.derive_roster(REPO_ROOT)
        coverage = validate.coverage_report(cards, roster)
        self.assertEqual(coverage.missing, ())
        self.assertTrue(coverage.is_complete())
        self.assertGreaterEqual(coverage.total_cards, len(roster) * 3)
        validate.assert_triplet_completeness(coverage)  # must not raise

    def test_assert_triplet_completeness_passes_for_the_now_complete_corpus__negative(self):
        """Negative control: a coverage report with a genuine missing
        plugin/kind cell (a roster plugin with zero cards, synthesized here
        so this control does not depend on the real corpus staying
        incomplete) MUST still raise CoverageGap -- the gate must not have
        been loosened into always passing along with the corpus becoming
        complete."""
        cards = validate.load_cards(REPO_ROOT)
        roster = registry.derive_roster(REPO_ROOT)
        fixture_roster = roster + (
            registry.PluginRef(
                name="fixture-uncarded-plugin", source="./plugins/fixture-uncarded-plugin",
                directory="plugins/fixture-uncarded-plugin", version="0.0.0",
                has_hooks=False, has_mcp=False, has_scripts=False,
                skills=(), commands=(),
            ),
        )
        coverage = validate.coverage_report(cards, fixture_roster)
        self.assertNotEqual(coverage.missing, ())
        with self.assertRaises(CoverageGap):
            validate.assert_triplet_completeness(coverage)


# ---------------------------------------------------------------------------
# T18 -- holdout / leakage / strata
# ---------------------------------------------------------------------------

class SamplingIntegrity(unittest.TestCase):
    def test_holdout_ids_are_the_reference_near_miss_cards(self):
        """The corpus is now complete across all 25 plugins (registry
        lane part 3): the holdout set is every plugin's near-miss card,
        not just the four reference plugins' -- updated from the interim
        4/25 assertion once the full triplet-per-plugin corpus landed."""
        cards = validate.load_cards(REPO_ROOT)
        roster = registry.derive_roster(REPO_ROOT)
        expected = {f"{p.name}-near-01" for p in roster}
        self.assertEqual(validate.holdout_ids(cards), frozenset(expected))

    def test_holdout_ids_are_the_reference_near_miss_cards__negative(self):
        """A manifest whose planned_n includes a holdout card id must be
        rejected -- the dev loop must never see holdout cards."""
        cards = validate.load_cards(REPO_ROOT)
        manifest = Manifest(
            run_id="r-neg", created_at="2026-09-06T00:00:00.000Z", git_commit="deadbeef",
            branch="main", offline=True, toolchain={"python": "3.12.3"}, lanes=("registry",),
            estimands=("full-package",), noninferiority_margin=0.1, min_valid=5, min_clusters=8,
            planned_n={c.card_id: 1 for c in cards},  # includes the holdout ids -- must fail
            holdout_seed=42, catalog_digest="0" * 64, skipped=(), approvals=(),
        )
        with self.assertRaises(LeakageDetected):
            validate.assert_holdout_unread(manifest, cards)

    def test_scan_leakage_finds_zero_overlaps_against_real_plugin_surfaces(self):
        """Scans EVERY roster plugin's real surface, not just the four
        reference plugins -- updated for registry lane part 3 now that all
        25 plugins carry cards. Restricting this to REFERENCE_PLUGINS would
        leave the other 21 plugins' cards structurally unscanned for
        leakage against the very surfaces their prompts and expected
        artifacts describe."""
        cards = validate.load_cards(REPO_ROOT)
        roster = registry.derive_roster(REPO_ROOT)
        surfaces: list[pathlib.Path] = []
        for ref in roster:
            plugin_dir = REPO_ROOT / ref.directory
            surfaces += sorted(plugin_dir.rglob("SKILL.md"))
            commands_dir = plugin_dir / "commands"
            if commands_dir.is_dir():
                surfaces += sorted(commands_dir.glob("*.md"))
        self.assertGreaterEqual(len(surfaces), len(roster))
        overlaps = validate.scan_leakage(cards, surfaces, min_tokens=8)
        self.assertEqual(overlaps, ())

    def test_scan_leakage_finds_zero_overlaps_against_real_plugin_surfaces__negative(self):
        """T18's own negative control: a card whose hidden verifier greps
        for a string the surface (a stand-in SKILL.md) instructs the model
        to emit. A scanner that misses this is vacuous."""
        leak_dir = FIXTURES / "leakage"
        surface = leak_dir / "surface.md"
        self.assertTrue(surface.is_file())
        leaky_card = Card(
            card_id="leaktest-pos-01", plugin="leaktest", kind=CardKind.POSITIVE,
            task_path=str((leak_dir / "task").relative_to(REPO_ROOT)),
            outcome_verifier=str((leak_dir / "leaky_verifier.py").relative_to(REPO_ROOT)),
            adoption_verifier=str((leak_dir / "clean_verifier.py").relative_to(REPO_ROOT)),
            pass_fixture=str((leak_dir / "task").relative_to(REPO_ROOT)),
            fail_fixture=str((leak_dir / "task").relative_to(REPO_ROOT)),
            expected_boundary_verdict="", capabilities=(), mutations=("delete-guard-line",),
            holdout=False,
        )
        overlaps = validate.scan_leakage([leaky_card], [surface], min_tokens=8)
        self.assertGreater(len(overlaps), 0)
        self.assertTrue(all(o.card_id == "leaktest-pos-01" for o in overlaps))


if __name__ == "__main__":
    unittest.main()
