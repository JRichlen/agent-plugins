# T16 fixture: exposure-parity

`pairing.py` (part 2 of the registry lane) implements `Arm`, `exposure_diff`,
`assert_exposure_parity`, `guidance_only_tree`, `is_degenerate`,
`composition_arms`, `version_arms`, `assign_stratum`, `holdout_split` per
contract §3.11.

`unmatched-tool.json` names the literal control fixture for T16's own
negative control: a baseline arm granted a tool that is neither shared with
the treatment nor the declared `generic_equivalent` of any treatment
capability ("unmatched widening", contract §3.11 clause (c) / counterfeit
fixture `25-agentic-exposure-parity`). `test_pairing.ExposureParity`'s
`__negative` method loads it and asserts `pairing.assert_exposure_parity`
raises `ExposureParityViolation` once the named tool is injected into a real
baseline arm built from `evals/agentic/tasks/graveyard/graveyard-pos-01`.

Catalog entry `T16` points at `evals.agentic.tests.test_pairing.ExposureParity
.test_baseline_arm_diverges_from_treatment_only_in_permitted_ways` (plus its
required `__negative` sibling).
