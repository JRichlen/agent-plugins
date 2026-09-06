"""Measurement-lane tests for evals.agentic.framework.analysis.

Covers T34 (no cross-model raw-token average), T35 (matched strata and
fallback flags), T36 (empirical any-pass / all-pass), T37 (clustered
uncertainty), T38 (zero denominator reports "unavailable"), and T39
(noninferiority lower-bound test). Every test asserts observable behavior and
is paired with a negative case (a foil computation or a mutated fixture) per
the task brief's instruction.
"""
from __future__ import annotations

import importlib.util
import math
import pathlib
import unittest

from evals.agentic.framework import io
from evals.agentic.framework.analysis import (
    Interval,
    Rate,
    all_pass,
    any_all_rates,
    any_pass,
    card_rate,
    cluster_bootstrap,
    cluster_t_interval,
    design_effect,
    difference_interval,
    group_by_stratum,
    icc,
    icc_raw,
    matched_pairs,
    noninferiority,
    pool_tokens,
    stratum_of,
    wilson_interval,
    wilson_with_cluster_inflation,
)
from evals.agentic.framework.contract import (
    ArmRole,
    ContractError,
    CrossModelPoolingRefused,
    MarginMissing,
    Stratum,
    TerminalState,
)

FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "measurement"


def _load_builders():
    spec = importlib.util.spec_from_file_location(
        "measurement_fixture_builders", FIXTURES / "builders.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builders = _load_builders()


# ---------------------------------------------------------------------------
# T34 -- no cross-model raw-token average
# ---------------------------------------------------------------------------

class NoCrossModelTokenAverage(unittest.TestCase):
    def _attempts_from_fixture(self):
        spec = io.load_json(FIXTURES / "tokens" / "two-models.json")
        attempts = []
        for group in spec["groups"]:
            stratum = Stratum(
                provider="anthropic", model=group["model_id"], revision="6d5342c",
                effort="high", harness="claude-code/2.1.263",
            )
            for _ in range(group["count"]):
                usage = builders.make_usage(
                    model_id=group["model_id"], output_tokens=group["output_tokens_each"],
                )
                attempts.append(builders.make_attempt(usage=usage, realized=stratum, requested=stratum))
        return attempts, spec

    def test_pool_without_by_raises_across_models(self):
        attempts, _ = self._attempts_from_fixture()
        with self.assertRaises(CrossModelPoolingRefused):
            pool_tokens(attempts, "output_tokens")

    def test_pool_by_model_returns_correct_per_model_sums(self):
        attempts, spec = self._attempts_from_fixture()
        by_model = pool_tokens(attempts, "output_tokens", by="model")
        for model_id, expected_sum in spec["expected"]["by_model"].items():
            self.assertIn(model_id, by_model)
            self.assertEqual(by_model[model_id].known, expected_sum)
            self.assertFalse(by_model[model_id].partial)

    def test_single_model_pool_without_by_succeeds(self):
        attempts, spec = self._attempts_from_fixture()
        one_model = [a for a in attempts if a.usage.model_id == "claude-opus-5"]
        result = pool_tokens(one_model, "output_tokens")
        self.assertEqual(set(result), {"claude-opus-5"})
        self.assertEqual(result["claude-opus-5"].known, spec["expected"]["by_model"]["claude-opus-5"])

    # -- negative control: the naive pooled mean --------------------------

    def test_naive_pooled_mean_describes_neither_model(self):
        """T34 negative control: 'mean tokens per task' computed over the
        mixed-model set. benchmark-spec §8: this number describes no model and
        moves with the arbitrary mix of attempts."""
        attempts, spec = self._attempts_from_fixture()
        naive_mean = sum(a.usage.output_tokens for a in attempts) / len(attempts)
        self.assertAlmostEqual(naive_mean, spec["expected"]["naive_pooled_mean"])
        # the correct, permitted figure is per-model and looks nothing like it
        by_model = pool_tokens(attempts, "output_tokens", by="model")
        for total in by_model.values():
            self.assertNotAlmostEqual(total.known / total.contributors, naive_mean, places=1)


# ---------------------------------------------------------------------------
# T35 -- matched strata and fallback flags
# ---------------------------------------------------------------------------

class MatchedStrataAndFallbacks(unittest.TestCase):
    def _build(self):
        spec = io.load_json(FIXTURES / "strata" / "fallback-40-cards.json")
        req = spec["requested"]
        requested = Stratum(**req)
        realized_fallback_model = Stratum(
            provider=req["provider"], model="claude-sonnet-5",
            revision=req["revision"], effort=req["effort"], harness=req["harness"],
        )
        realized_fallback_effort = Stratum(
            provider=req["provider"], model=req["model"],
            revision=req["revision"], effort="medium", harness=req["harness"],
        )
        treatment = []
        baseline = []
        model_fallback_cards = set(spec["treatment_model_fallback_cards"])
        effort_fallback_cards = set(spec["baseline_effort_fallback_cards"])
        for i in range(1, spec["n_cards"] + 1):
            card_id = f"card-{i:02d}"
            if card_id in model_fallback_cards:
                t_realized, t_flags = realized_fallback_model, ("model",)
            else:
                t_realized, t_flags = requested, ()
            treatment.append(
                builders.make_attempt(
                    card_id=card_id, arm_id="treatment", requested=requested,
                    realized=t_realized, fallback_flags=t_flags,
                )
            )
            if card_id in effort_fallback_cards:
                b_realized, b_flags = realized_fallback_effort, ("effort",)
            else:
                b_realized, b_flags = requested, ()
            baseline.append(
                builders.make_attempt(
                    card_id=card_id, arm_id="baseline", role=ArmRole.BASELINE,
                    requested=requested, realized=b_realized, fallback_flags=b_flags,
                )
            )
        return treatment, baseline, spec

    def test_matched_pairs_excludes_fallback_attempts(self):
        treatment, baseline, spec = self._build()
        pairs, unmatched = matched_pairs(treatment, baseline)
        self.assertEqual(len(pairs), spec["expected"]["matched_pairs"])
        treatment_unmatched = [u for u in unmatched if u.side == "treatment"]
        baseline_unmatched = [u for u in unmatched if u.side == "baseline"]
        self.assertEqual(len(treatment_unmatched), spec["expected"]["unmatched_treatment"])
        self.assertEqual(len(baseline_unmatched), spec["expected"]["unmatched_baseline"])
        # every matched pair really does carry empty fallback flags both sides
        for p in pairs:
            self.assertEqual(p.treatment.fallback_flags, ())
            self.assertEqual(p.baseline.fallback_flags, ())

    def test_group_by_stratum_and_stratum_of(self):
        treatment, baseline, _ = self._build()
        groups = group_by_stratum(treatment)
        self.assertEqual(len(groups), 2)  # requested stratum + fallback-model stratum
        for a in treatment:
            self.assertIn(stratum_of(a), groups)

    def test_difference_interval_rejects_mixed_strata(self):
        treatment, baseline, _ = self._build()
        pairs, _ = matched_pairs(treatment, baseline)
        # Deliberately corrupt one pair's stratum to a different value, as if
        # two Pairs from different realized models were merged into one Delta.
        import dataclasses as dc
        bad_pairs = list(pairs)
        other = Stratum(provider="openai", model="gpt-x", revision="z", effort="n/a", harness="codex-cli/0.153.4")
        bad_pairs[0] = dc.replace(bad_pairs[0], stratum=other)
        with self.assertRaises(ContractError):
            difference_interval(bad_pairs, seed=1, min_clusters=1)

    # -- negative control: silent fallback pooling -------------------------

    def test_pooling_fallback_attempt_with_on_request_attempt_is_wrong(self):
        """T35 negative control: comparing a treatment arm that ran on the
        requested model against a baseline arm that fell back makes the
        'skill effect' a model effect. matched_pairs is exactly the guard that
        excludes this from the effect estimate."""
        treatment, baseline, spec = self._build()
        pairs, unmatched = matched_pairs(treatment, baseline)
        fallback_card_ids = set(spec["treatment_model_fallback_cards"]) | set(
            spec["baseline_effort_fallback_cards"]
        )
        matched_card_ids = {p.card_id for p in pairs}
        # none of the fallback cards made it into the matched set
        self.assertEqual(matched_card_ids & fallback_card_ids, set())


# ---------------------------------------------------------------------------
# T36 -- empirical any-pass and all-pass
# ---------------------------------------------------------------------------

class AnyAllPass(unittest.TestCase):
    def test_five_trials_three_pass_one_fail_one_fault(self):
        spec = io.load_json(FIXTURES / "anyall" / "redgate-pos-01.json")
        trials = builders.attempts_for_card(spec["card_id"], spec["trials"])
        exp = spec["expected"]
        rate = card_rate(trials)
        self.assertEqual(rate.numerator, exp["passes"])
        self.assertEqual(rate.denominator, exp["valid"])
        self.assertAlmostEqual(rate.value, exp["rate"])
        self.assertIs(any_pass(trials), exp["any"])
        self.assertIs(all_pass(trials), exp["all"])
        n_faults = sum(1 for t in trials if t.terminal_state is TerminalState.FAULT)
        self.assertEqual(n_faults, exp["faults"])

    def test_any_all_rates_across_cards(self):
        c1 = builders.attempts_for_card("c1", ["pass", "fail"])
        c2 = builders.attempts_for_card("c2", ["pass", "pass"])
        c3 = builders.attempts_for_card("c3", ["fault", "fault"])  # no defined verdict
        any_rate, all_rate = any_all_rates({"c1": c1, "c2": c2, "c3": c3})
        # c3 has valid=0 -> excluded from the denominator entirely
        self.assertEqual(any_rate.denominator, 2)
        self.assertEqual(all_rate.denominator, 2)
        self.assertEqual(any_rate.numerator, 2)  # both c1 and c2 have >=1 pass
        self.assertEqual(all_rate.numerator, 1)  # only c2 passes every valid trial

    def test_adoption_score_is_independent_of_outcome_score(self):
        trials = builders.attempts_for_card(
            "c-mixed", ["pass", "pass"], adoption=[False, False],
        )
        self.assertTrue(any_pass(trials, score="outcome"))
        self.assertFalse(any_pass(trials, score="adoption"))

    # -- negative controls: any-only, all-only, and faults-as-failures ------

    def test_any_only_would_overclaim_the_skill_works(self):
        """T36 negative control: reporting only `any` turns one lucky trial
        into 'the skill works', hiding that `all` is False on the same data."""
        spec = io.load_json(FIXTURES / "anyall" / "redgate-pos-01.json")
        trials = builders.attempts_for_card(spec["card_id"], spec["trials"])
        self.assertTrue(any_pass(trials))
        self.assertFalse(all_pass(trials))  # any alone would have missed this

    def test_counting_faults_as_failures_corrupts_the_rate(self):
        """T36 negative control: treating FAULT as a fail (rather than
        excluding it) turns provider weather into a plugin verdict."""
        spec = io.load_json(FIXTURES / "anyall" / "redgate-pos-01.json")
        trials = builders.attempts_for_card(spec["card_id"], spec["trials"])
        correct_rate = card_rate(trials)
        wrong_denominator = len(trials)  # counting the fault as a valid, failed trial
        wrong_rate = correct_rate.numerator / wrong_denominator
        self.assertNotEqual(wrong_denominator, correct_rate.denominator)
        self.assertNotAlmostEqual(wrong_rate, correct_rate.value)


# ---------------------------------------------------------------------------
# T37 -- clustered uncertainty
# ---------------------------------------------------------------------------

class ClusteredUncertainty(unittest.TestCase):
    def test_icc_and_design_effect_worked_example(self):
        spec = io.load_json(FIXTURES / "clustered" / "icc-4x5.json")
        m = spec["cluster_size"]
        clusters = [[1.0] * count + [0.0] * (m - count) for count in spec["pass_counts"]]
        raw = icc_raw(clusters)
        deff = design_effect(clusters)
        exp = spec["expected"]
        self.assertAlmostEqual(raw, exp["icc_raw"], places=3)
        self.assertAlmostEqual(deff, exp["deff"], places=2)
        self.assertAlmostEqual(icc(clusters), max(raw, 0.0), places=6)

    def test_wilson_naive_worked_example(self):
        lo, hi = wilson_interval(57, 80)
        self.assertAlmostEqual(lo, 0.6054, places=3)
        self.assertAlmostEqual(hi, 0.8001, places=3)

    def test_wilson_with_cluster_inflation_widens_and_respects_band(self):
        spec = io.load_json(FIXTURES / "clustered" / "wilson-cluster-inflation-16x5.json")
        m = spec["cluster_size"]
        clusters = [[1.0] * count + [0.0] * (m - count) for count in spec["pass_counts"]]
        n = sum(len(c) for c in clusters)
        k = sum(sum(c) for c in clusters)
        self.assertEqual(n, spec["expected"]["n"])
        self.assertEqual(k, spec["expected"]["k"])

        naive_lo, naive_hi = wilson_interval(k, n)
        naive_width = naive_hi - naive_lo

        clustered = wilson_with_cluster_inflation(clusters, min_clusters=8)
        self.assertIsNone(clustered.unavailable_reason)
        clustered_width = clustered.hi - clustered.lo

        deff = clustered.deff
        self.assertIsNotNone(deff)
        self.assertGreater(deff, 1.0)  # real positive within-cluster correlation here
        ratio = clustered_width / naive_width
        # the frozen band invariant (benchmark-spec §6.3), never asserted as
        # an equality
        self.assertGreater(ratio, 1.0)
        self.assertLessEqual(ratio, math.sqrt(deff) * 1.02)
        self.assertGreaterEqual(ratio, math.sqrt(deff) * 0.90)

    def test_cluster_t_interval_worked_example_A_insufficient_clusters(self):
        spec = io.load_json(FIXTURES / "clustered" / "cluster-t-4-cards.json")
        means = spec["cluster_means"]
        exp = spec["expected"]

        # raw arithmetic check, gate disabled
        raw = cluster_t_interval(means, min_clusters=1)
        self.assertAlmostEqual(raw.point, exp["mean"], places=4)
        self.assertAlmostEqual(raw.lo, exp["lo"], places=3)
        self.assertAlmostEqual(raw.hi, exp["hi"], places=3)

        # default floor (8) refuses to report it
        gated = cluster_t_interval(means)
        self.assertIsNone(gated.lo)
        self.assertIsNone(gated.hi)
        self.assertEqual(gated.unavailable_reason, "insufficient clusters: 4 < 8")

    def test_cluster_t_interval_worked_example_B_reported(self):
        spec = io.load_json(FIXTURES / "clustered" / "cluster-t-12-cards.json")
        means = spec["cluster_means"]
        exp = spec["expected"]
        result = cluster_t_interval(means)
        self.assertIsNone(result.unavailable_reason)
        self.assertAlmostEqual(result.point, exp["mean"], places=4)
        self.assertAlmostEqual(result.lo, exp["lo"], places=3)
        self.assertAlmostEqual(result.hi, exp["hi"], places=3)
        self.assertGreater(result.lo, 0)  # positive AND noninferior for any margin > 0

    def test_cluster_bootstrap_is_reproducible_with_same_seed(self):
        clusters = [[1.0, 1.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 1.0], [0.0, 0.0, 0.0],
                    [1.0, 1.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 1.0], [0.0, 1.0, 0.0]]

        def mean_stat(cs):
            return sum(sum(c) / len(c) for c in cs) / len(cs)

        a = cluster_bootstrap(clusters, mean_stat, seed=42, iters=500, min_clusters=8)
        b = cluster_bootstrap(clusters, mean_stat, seed=42, iters=500, min_clusters=8)
        self.assertEqual(a.lo, b.lo)
        self.assertEqual(a.hi, b.hi)

    # -- negative control: naive i.i.d. binomial CI over trial rows --------

    def test_naive_iid_interval_is_narrower_than_clustered(self):
        """T37 negative control: an i.i.d. binomial CI over trial rows
        (ignoring clustering) understates the width by roughly DEFF and can
        turn noise into a significant result."""
        spec = io.load_json(FIXTURES / "clustered" / "wilson-cluster-inflation-16x5.json")
        m = spec["cluster_size"]
        clusters = [[1.0] * count + [0.0] * (m - count) for count in spec["pass_counts"]]
        n = sum(len(c) for c in clusters)
        k = sum(sum(c) for c in clusters)
        naive_lo, naive_hi = wilson_interval(k, n)
        clustered = wilson_with_cluster_inflation(clusters, min_clusters=8)
        self.assertLess(naive_hi - naive_lo, clustered.hi - clustered.lo)


# ---------------------------------------------------------------------------
# T38 -- zero denominator reports "unavailable"
# ---------------------------------------------------------------------------

class ZeroDenominatorUnavailable(unittest.TestCase):
    def test_all_fault_card_is_unavailable_with_reason(self):
        spec = io.load_json(FIXTURES / "zero_denom" / "voice-neg-02.json")
        trials = builders.attempts_for_card(spec["card_id"], spec["all_fault_trials"])
        rate = card_rate(trials)
        self.assertIsNone(rate.value)
        self.assertEqual(rate.denominator, 0)
        self.assertEqual(rate.unavailable_reason, spec["expected"]["all_fault_reason"])
        self.assertEqual(rate.render(), f"unavailable ({spec['expected']['all_fault_reason']})")
        self.assertIsNone(any_pass(trials))
        self.assertIsNone(all_pass(trials))

    def test_starved_card_below_min_valid(self):
        spec = io.load_json(FIXTURES / "zero_denom" / "voice-neg-02.json")
        trials = builders.attempts_for_card(spec["card_id"], spec["starved_trials"])
        min_valid = spec["expected"]["starved_min_valid"]
        rate = card_rate(trials, min_valid=min_valid)
        self.assertIsNone(rate.value)
        self.assertEqual(rate.unavailable_reason, spec["expected"]["starved_reason"])

    def test_insufficient_clusters_never_returns_a_narrow_interval(self):
        interval = wilson_with_cluster_inflation([[1.0, 1.0], [0.0, 1.0]], min_clusters=8)
        self.assertIsNone(interval.lo)
        self.assertIsNone(interval.hi)
        self.assertTrue(interval.unavailable_reason.startswith("insufficient clusters"))

    # -- negative controls: the four banned renderings ----------------------

    def test_naive_zero_over_max_valid_one_reads_as_the_plugin_failed(self):
        """T38 negative control: passes / max(valid, 1) on a zero-denominator
        card renders '0%', which reads as 'the plugin failed' when the truth
        is 'nothing was measured'."""
        spec = io.load_json(FIXTURES / "zero_denom" / "voice-neg-02.json")
        trials = builders.attempts_for_card(spec["card_id"], spec["all_fault_trials"])
        rate = card_rate(trials)
        valid = 0
        naive_pct = 0 / max(valid, 1) * 100
        self.assertEqual(naive_pct, 0.0)  # the banned rendering
        self.assertNotEqual(rate.render(), "0%")
        self.assertIn("unavailable", rate.render())

    def test_perfect_single_sample_stratum_is_not_100_percent(self):
        """The inverse banned rendering: a stratum whose only valid sample
        passed must not print 100% -- min_valid catches it."""
        trials = builders.attempts_for_card("c-lucky", ["pass"])
        rate = card_rate(trials, min_valid=3)
        self.assertIsNone(rate.value)
        self.assertIn("starved", rate.unavailable_reason)


# ---------------------------------------------------------------------------
# T39 -- noninferiority lower-bound test
# ---------------------------------------------------------------------------

class NoninferiorityLowerBound(unittest.TestCase):
    def test_established_when_lower_bound_clears_margin(self):
        spec = io.load_json(FIXTURES / "noninferiority" / "margins.json")
        lo, hi = spec["established_case"]["lo"], spec["established_case"]["hi"]
        interval = Interval(
            point=(lo + hi) / 2, lo=lo, hi=hi, method="cluster-t", n_clusters=12,
            cluster_variable="card", deff=None, deff_method=None, icc_raw=None,
            unavailable_reason=None,
        )
        result = noninferiority(interval, spec["margin"])
        self.assertTrue(result.established)
        self.assertEqual(result.lower_bound, lo)

    def test_not_established_when_lower_bound_misses_margin(self):
        spec = io.load_json(FIXTURES / "noninferiority" / "margins.json")
        lo, hi = spec["not_established_case"]["lo"], spec["not_established_case"]["hi"]
        interval = Interval(
            point=(lo + hi) / 2, lo=lo, hi=hi, method="cluster-t", n_clusters=4,
            cluster_variable="card", deff=None, deff_method=None, icc_raw=None,
            unavailable_reason=None,
        )
        result = noninferiority(interval, spec["margin"])
        self.assertFalse(result.established)

    def test_missing_margin_raises(self):
        interval = Interval(
            point=0.1, lo=0.05, hi=0.15, method="cluster-t", n_clusters=12,
            cluster_variable="card", deff=None, deff_method=None, icc_raw=None,
            unavailable_reason=None,
        )
        with self.assertRaises(MarginMissing):
            noninferiority(interval, None)

    def test_unavailable_interval_yields_none_established(self):
        interval = Interval(
            point=0.1, lo=None, hi=None, method="cluster-t", n_clusters=4,
            cluster_variable="card", deff=None, deff_method=None, icc_raw=None,
            unavailable_reason="insufficient clusters: 4 < 8",
        )
        result = noninferiority(interval, 0.05)
        self.assertIsNone(result.established)
        self.assertEqual(result.reason, "insufficient clusters: 4 < 8")

    def test_end_to_end_from_cluster_t_interval_worked_examples(self):
        margins = io.load_json(FIXTURES / "noninferiority" / "margins.json")
        established_spec = io.load_json(FIXTURES / "clustered" / "cluster-t-12-cards.json")
        interval = cluster_t_interval(established_spec["cluster_means"])
        result = noninferiority(interval, margins["margin"])
        self.assertTrue(result.established)

    # -- negative control: p > 0.05 "therefore equivalent" -----------------

    def test_underpowered_run_cannot_be_waved_through_as_equivalent(self):
        """T39 negative control: 'p > 0.05, therefore equivalent' is not a
        test -- an underpowered run (wide interval straddling both directions)
        must NOT be reported established just because it also isn't
        significantly negative."""
        wide_interval = Interval(
            point=0.05, lo=-0.40, hi=0.50, method="cluster-t", n_clusters=12,
            cluster_variable="card", deff=None, deff_method=None, icc_raw=None,
            unavailable_reason=None,
        )
        result = noninferiority(wide_interval, margin=0.05)
        self.assertFalse(result.established)  # lower bound -0.40 is well below -0.05

    def test_margin_chosen_after_the_fact_is_visible_not_hidden(self):
        """T39 negative control: choosing delta=0.30 after seeing a wide CI
        to force 'established' is possible mechanically, but the margin used
        is always the one recorded on the NoninferiorityResult, not silently
        substituted -- so the after-the-fact choice is visible in the result,
        not laundered away."""
        interval = Interval(
            point=0.1375, lo=-0.2596, hi=0.5346, method="cluster-t", n_clusters=4,
            cluster_variable="card", deff=None, deff_method=None, icc_raw=None,
            unavailable_reason=None,
        )
        result_honest = noninferiority(interval, margin=0.05)
        result_gamed = noninferiority(interval, margin=0.30)
        self.assertFalse(result_honest.established)
        self.assertTrue(result_gamed.established)
        # the two margins are recorded, not merged into one silent verdict
        self.assertNotEqual(result_honest.margin, result_gamed.margin)


if __name__ == "__main__":
    unittest.main()
