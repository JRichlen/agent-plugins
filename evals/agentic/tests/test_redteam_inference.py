"""Regression checks for what redteam measurements can actually establish."""
from __future__ import annotations

import copy
import unittest

from evals.agentic.framework import analysis
from evals.agentic.tests.test_redteam_design import _load_verdict, _row


class RedteamInference(unittest.TestCase):
    def setUp(self):
        self.verdict = _load_verdict()

    def _tranche(self, *, utility_evidence=True):
        cells = {}
        for cell in ("C1", "C2", "C3", "C4", "C5", "C6"):
            rows = [_row(cell, index) for index in range(8)]
            for index, row in enumerate(rows):
                variables = row["testCase"]["vars"]
                variables["corpus_pair_id"] = f"case-{index}"
                if utility_evidence:
                    variables["utility_evidence"] = "artifact-verifier-v1"
                else:
                    variables.pop("utility_evidence", None)
            cells[cell] = self.verdict.aggregate_cell(rows)
        return {"status": "COMPLETE", "cells": cells}

    def test_eight_successes_and_eight_failures_keep_binomial_uncertainty(self):
        for success in (0, 1):
            clusters = {str(i): [success] for i in range(8)}
            interval = self.verdict.clustered_interval(clusters)
            expected = analysis.wilson_with_cluster_inflation(list(clusters.values()))
            self.assertAlmostEqual(interval["lo"], expected.lo)
            self.assertAlmostEqual(interval["hi"], expected.hi)
            self.assertGreater(interval["hi"] - interval["lo"], 0.3)

    def test_interaction_pairs_the_same_items_before_estimating_variance(self):
        tranche = self._tranche()
        a = [1, 1, 1, 1, 0, 0, 0, 0]
        b = [1, 1, 1, 0, 1, 0, 0, 0]
        for cell, outcomes in (("C4", a), ("C6", b)):
            tranche["cells"][cell]["textual_indicator_clusters"] = {
                f"case-{i}": [value] for i, value in enumerate(outcomes)
            }
        inter = self.verdict.interaction(tranche)
        result = self.verdict.interaction_uncertainty(tranche, inter)["textual"]
        expected = analysis.cluster_t_interval([left - right for left, right in zip(a, b)])
        self.assertAlmostEqual(result["lo"], expected.lo)
        self.assertAlmostEqual(result["hi"], expected.hi)
        self.assertEqual(result["method"], "paired-cluster-t")

        # Same marginal rates, different pairing: the uncertainty must change.
        changed = copy.deepcopy(tranche)
        changed["cells"]["C6"]["textual_indicator_clusters"] = {
            f"case-{i}": [1 - value] for i, value in enumerate(a)
        }
        changed_result = self.verdict.interaction_uncertainty(
            changed, self.verdict.interaction(changed)
        )["textual"]
        self.assertGreater(changed_result["hi"], result["hi"])

    def test_missing_pair_is_unavailable_instead_of_an_independent_comparison(self):
        tranche = self._tranche()
        clusters = tranche["cells"]["C4"]["textual_indicator_clusters"]
        clusters.pop(next(iter(clusters)))
        inter = self.verdict.interaction(tranche)
        self.assertEqual(inter["textual"], "unavailable")
        report = self.verdict.interaction_uncertainty(tranche, inter)["textual"]
        self.assertIn("unmatched", report["unavailable_reason"])

    def test_identical_observations_do_not_establish_population_certainty(self):
        tranche = self._tranche()
        report = self.verdict.interaction_uncertainty(
            tranche, self.verdict.interaction(tranche)
        )["textual"]
        self.assertEqual(report["lo"], "unavailable")
        self.assertIn("zero observed", report["unavailable_reason"])

    def test_legacy_marker_scores_cannot_be_used_as_utility_effects(self):
        tranche = self._tranche(utility_evidence=False)
        for cell in tranche["cells"].values():
            self.assertEqual(cell["utility_rate"], "unavailable")
        self.assertEqual(self.verdict.interaction(tranche)["utility"], "unavailable")

    def test_artifact_utility_retains_benefit_sign_in_clean_comparison(self):
        tranche = self._tranche()
        tranche["cells"]["C2"]["utility_clusters"] = {
            f"case-{i}": [int(i < 3)] for i in range(8)
        }
        result = self.verdict.clean_utility_difference(tranche)
        self.assertEqual(result["baseline_generic"], -0.625)
        self.assertEqual(result["baseline"], -0.625)


if __name__ == "__main__":
    unittest.main()
