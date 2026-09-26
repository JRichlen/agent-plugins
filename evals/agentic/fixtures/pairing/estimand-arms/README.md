# T17 fixture: estimand-arms

`pairing.py` (part 2 of the registry lane) implements `build_arm`,
`composition_arms`, `version_arms`, and `guidance_only_tree`/
`assert_guidance_only_tree_is_pure` per contract §3.11.

`contaminated-guidance/hooks/hooks.json` is T17's own stated negative
control (contract's exact wording): "a guidance-only arm that still loads
`plugins/agent-compiler/hooks/hooks.json`" -- here as a portable, plugin-
agnostic stand-in `hooks/hooks.json` file. `test_pairing.EstimandArms`'s
`__negative` method copies this file into an otherwise-legitimate
guidance-only tree (produced by `pairing.guidance_only_tree`) and asserts
`pairing.assert_guidance_only_tree_is_pure` now raises
`ExposureParityViolation` -- proving the guidance-only purity check is not
vacuous: it actually rejects contamination when contamination is present,
not just when it happens to be absent.

Catalog entry `T17` in `manifests/catalog/registry.json` points at
`evals.agentic.tests.test_pairing.EstimandArms
.test_four_estimands_are_distinct_and_correctly_shaped` (plus its required
`__negative` sibling).
