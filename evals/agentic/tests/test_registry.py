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
    AdapterClass,
    ApprovalGate,
    ArmRole,
    Attempt,
    Card,
    CardKind,
    CatalogUnresolvable,
    ContractError,
    CoverageGap,
    EvidenceClass,
    LeakageDetected,
    Manifest,
    Stratum,
    TerminalState,
    Usage,
    VacuousVerifier,
    Verdict,
    now_rfc3339,
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

        self.assertEqual(len(roster), len(marketplace["plugins"]))
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

    def test_no_catalog_mapped_test_contains_a_constant_vs_constant_assertion(self):
        """F2: run_entry's '>=1 assertion' floor cannot tell assertTrue(True)
        from a real assertion -- it counts calls, not what they prove.
        Sweeps every one of the real, live catalog's resolvable entries and
        lints the mapped test method's own source for that specific shape."""
        catalog = registry.load_catalog(REPO_ROOT)
        checked = 0
        for entry in catalog.entries.values():
            try:
                cls, method_name = registry.resolve_test(entry)
            except CatalogUnresolvable:
                continue  # a blocked/unresolvable entry has no source to lint
            checked += 1
            with self.subTest(entry=entry.id):
                findings = registry.scan_vacuous_assertions(cls, method_name)
                self.assertEqual(
                    findings, (),
                    f"{entry.id} ({cls.__name__}.{method_name}) contains a vacuous assertion: {findings}",
                )
        self.assertGreater(checked, 0, "no catalog entries were resolvable -- nothing was actually linted")

    def test_no_catalog_mapped_test_contains_a_constant_vs_constant_assertion__negative(self):
        """Negative control: the scanner must actually fire on the exact
        vacuous shapes it claims to catch -- a scanner that always returns
        () would let the positive sweep above pass vacuously too."""
        class _DeliberatelyVacuous(unittest.TestCase):
            def test_true_is_true(self):
                self.assertTrue(True)

            def test_one_equals_one(self):
                self.assertEqual(1, 1)

            def test_a_real_assertion(self):
                x = 2 + 2
                self.assertEqual(x, 4)  # one side is a variable, not a bare literal -- not this pattern

        findings_true = registry.scan_vacuous_assertions(_DeliberatelyVacuous, "test_true_is_true")
        self.assertEqual(len(findings_true), 1)
        self.assertIn("assertTrue(True)", findings_true[0])

        findings_eq = registry.scan_vacuous_assertions(_DeliberatelyVacuous, "test_one_equals_one")
        self.assertEqual(len(findings_eq), 1)
        self.assertIn("assertEqual(1, 1)", findings_eq[0])

        findings_real = registry.scan_vacuous_assertions(_DeliberatelyVacuous, "test_a_real_assertion")
        self.assertEqual(findings_real, (), "a variable-vs-literal comparison must not be flagged")

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


class FixtureLeakageBinding(unittest.TestCase):
    """CV-07: a card's real, task-specific oracle lives in its FIXTURES
    (`fixtures/pass/guard.sh` and any sibling fixture file, not the two
    shared card-independent verifier scripts), so a leakage scan that never
    reads fixtures cannot notice a surface publishing the verbatim grading
    command and a full copy of a passing artifact."""

    def test_surface_publishing_the_real_guard_check_and_a_passing_artifact_is_caught(self):
        """CV-07's exact reproduction, run against a temp copy of the real
        surface (never mutating the committed plugin file): appending
        stop-rule-pos-01's own fixtures/pass/guard.sh check line and its
        fixtures/pass/stop-report.md verbatim to the plugin's real SKILL.md
        must now be flagged."""
        cards = validate.load_cards(REPO_ROOT)
        card = next(c for c in cards if c.card_id == "stop-rule-pos-01")
        guard = (REPO_ROOT / card.pass_fixture / "guard.sh").read_text()
        report = (REPO_ROOT / card.pass_fixture / "stop-report.md").read_text()
        real_skill = REPO_ROOT / "plugins" / "stop-rule" / "skills" / "stop-rule" / "SKILL.md"
        with tempfile.TemporaryDirectory() as tmp:
            leaked = pathlib.Path(tmp) / "SKILL.md"
            leaked.write_text(
                real_skill.read_text() + "\n\n## How you will be graded\n\n" + guard
                + "\nExample of a passing stop-report.md:\n\n" + report
            )
            overlaps = validate.scan_leakage([card], [leaked])
            self.assertGreater(len(overlaps), 0)
            self.assertTrue(all(o.card_id == "stop-rule-pos-01" for o in overlaps))

    def test_surface_publishing_the_real_guard_check_and_a_passing_artifact_is_caught__negative(self):
        """Negative control: the REAL, unmodified SKILL.md (never leaked)
        must report zero overlaps -- proving the positive case above is
        about the appended secret content, not that this check now flags
        every plugin's real, legitimate documentation."""
        cards = validate.load_cards(REPO_ROOT)
        card = next(c for c in cards if c.card_id == "stop-rule-pos-01")
        real_skill = REPO_ROOT / "plugins" / "stop-rule" / "skills" / "stop-rule" / "SKILL.md"
        overlaps = validate.scan_leakage([card], [real_skill])
        self.assertEqual(overlaps, ())

    def test_plugins_own_generated_scaffolding_is_not_a_false_positive(self):
        """Negative control for the fixture-inclusive scan itself: redgate's
        `scaffold-run.sh` generates the same exit-code-convention comment
        into every `check.sh` it scaffolds, and redgate's own SKILL.md
        legitimately documents that same real, public behavior. Since that
        comment is independently already public via the plugin's own real
        script (not fixture-exclusive), it must not be reported as a T18(b)
        leak -- caught during this repair as a false positive introduced by
        naively scanning every fixture byte with no exemption at all."""
        cards = validate.load_cards(REPO_ROOT)
        redgate_cards = [c for c in cards if c.plugin == "redgate"]
        self.assertGreater(len(redgate_cards), 0)
        real_skill = REPO_ROOT / "plugins" / "redgate" / "skills" / "criteria-contract" / "SKILL.md"
        overlaps = validate.scan_leakage(redgate_cards, [real_skill])
        self.assertEqual(overlaps, ())


class ParaphraseCoverage(unittest.TestCase):
    """CV-12: paraphrase variants and baseline-framing commentary must live
    in card.json (registry-internal), not in the agent-visible
    task/README.md -- and every holdout card needs at least two, so the
    (not-yet-wired, integration-lane) runner has something to select
    between per attempt."""

    def test_every_holdout_card_carries_at_least_two_paraphrases(self):
        cards = validate.load_cards(REPO_ROOT)
        holdout = [c for c in cards if c.holdout]
        self.assertGreater(len(holdout), 0)
        for card in holdout:
            with self.subTest(card=card.card_id):
                paras = validate.card_paraphrases(card, REPO_ROOT)
                self.assertGreaterEqual(
                    len(paras), 2,
                    f"{card.card_id}: holdout card must carry >=2 paraphrases in card.json",
                )

    def test_every_holdout_card_carries_at_least_two_paraphrases__negative(self):
        """Negative control: a non-holdout card is not held to this bar --
        proving the assertion above is specifically about holdout cards,
        not a blanket 'every card needs paraphrases' rule this corpus does
        not actually try to satisfy for its dev-loop-visible cards."""
        cards = validate.load_cards(REPO_ROOT)
        non_holdout_without_paraphrases = [
            c for c in cards if not c.holdout and not validate.card_paraphrases(c, REPO_ROOT)
        ]
        self.assertGreater(
            len(non_holdout_without_paraphrases), 0,
            "sanity: at least one non-holdout card has no paraphrases and that is fine",
        )

    def test_no_task_readme_discloses_paraphrase_or_baseline_framing_sections(self):
        """The concrete leak CV-12 named: 'Baseline framing' prose sitting
        in the agent-visible task/README.md named the treatment's own skill
        by what it withholds from the baseline. Neither section may appear
        in any task/README.md again."""
        tasks_dir = REPO_ROOT / "evals" / "agentic" / "tasks"
        offenders = []
        for readme in sorted(tasks_dir.rglob("task/README.md")):
            text = readme.read_text()
            if "Paraphrase variants" in text or "Baseline framing" in text:
                offenders.append(str(readme.relative_to(REPO_ROOT)))
        self.assertEqual(offenders, [])


def _attempt_doc(*, model_id: str, stratum_model: str, adapter_class: AdapterClass = AdapterClass.NATIVE) -> dict:
    strat = Stratum(provider="anthropic", model=stratum_model, revision="r1", effort="high", harness="claude-code/1.0")
    usage = Usage(
        model_id=model_id, reported_by="claude-cli/1.0",
        input_tokens=1, output_tokens=1, cache_read_input_tokens=0,
        cache_creation_input_tokens=0, reasoning_tokens=0, total_tokens=2,
        wall_clock_ms=100, cost_usd=0.01,
    )
    verdict = Verdict(passed=True, verifier_id="v1", reason="ok", hack_class=None, evidence_digest=None)
    attempt = Attempt(
        attempt_id="at-1", run_id="run-1", card_id="c1", arm_id="arm-1",
        role=ArmRole.TREATMENT, control_kind=None, parent_attempt_id=None,
        terminal_state=TerminalState.DELIVERED,
        evidence_class=EvidenceClass.FRAMEWORK, adapter_class=AdapterClass.STUB,
        requested=strat, realized=strat, fallback_flags=(), usage=usage,
        outcome=verdict, adoption=verdict,
        started_at=now_rfc3339(), ended_at=now_rfc3339(),
        session_id=None, event_ids=(), arrived_after_terminal=False,
    )
    doc = attempt.to_dict()
    # to_dict() encodes enums as their .value strings (contract §2.3
    # convention); override adapter_class's encoded value directly so this
    # helper can exercise validate_attempt with either scoping.
    doc["adapter_class"] = adapter_class.value
    return doc


class AttemptModelStratumCrossCheck(unittest.TestCase):
    """S-08 residual: validate.validate_attempt schema-validates a
    serialized attempt record and cross-checks usage.model_id against the
    stratum it is realized on, for every AdapterClass (unlike
    contract.Attempt.__post_init__'s NATIVE-only in-memory check -- see
    that method's docstring comment for why it is scoped narrower)."""

    def test_matching_model_id_and_stratum_passes(self):
        doc = _attempt_doc(model_id="claude-sonnet-5", stratum_model="claude-sonnet-5")
        attempt = validate.validate_attempt(doc)
        self.assertEqual(attempt.usage.model_id, "claude-sonnet-5")

    def test_mismatched_model_id_and_stratum_is_rejected(self):
        """S-08's exact shape: usage says one model, realized says another."""
        doc = _attempt_doc(model_id="claude-sonnet-5", stratum_model="claude-opus-5")
        with self.assertRaises(ContractError):
            validate.validate_attempt(doc)

    def test_mismatched_model_id_and_stratum_is_rejected__negative(self):
        """Sibling: the same mismatch, but wired through a STUB adapter_class
        (where contract.Attempt's own in-memory constructor does NOT check
        this) still gets caught at validate.validate_attempt -- proving this
        is a real independent check, not a passthrough to the narrower one."""
        doc = _attempt_doc(model_id="claude-sonnet-5", stratum_model="claude-opus-5", adapter_class=AdapterClass.STUB)
        # contract.Attempt itself must accept this (STUB is out of scope for
        # its own check) ...
        attempt = Attempt.from_dict(doc)
        self.assertEqual(attempt.usage.model_id, "claude-sonnet-5")
        # ... but validate.validate_attempt must still refuse it.
        with self.assertRaises(ContractError):
            validate.validate_attempt(doc)

    def test_native_adapter_mismatch_is_already_rejected_by_attempt_itself(self):
        """contract.Attempt.__post_init__'s narrower, NATIVE-only check
        fires first for a NATIVE-adapter attempt -- validate_attempt need
        not do any extra work to catch this case, but must not let it
        through either."""
        doc = _attempt_doc(model_id="claude-sonnet-5", stratum_model="claude-opus-5", adapter_class=AdapterClass.NATIVE)
        with self.assertRaises(ContractError):
            Attempt.from_dict(doc)
        with self.assertRaises(ContractError):
            validate.validate_attempt(doc)


if __name__ == "__main__":
    unittest.main()
