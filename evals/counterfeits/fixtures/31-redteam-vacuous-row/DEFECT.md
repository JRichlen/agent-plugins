# Redteam: a vacuous row scored as a perfect pass

Sets `options: {disableDefaultAsserts: true}` on ONE test row in the staged
`evals/redteam/configs/generated/stop-rule.yaml` — a real route to vacuity
promptfoo documents (`testCase.options.disableDefaultAsserts`,
`evaluator-SSlcaq_U.js:7832`), invisible to any static check of the
`assert:` list (unlike fixture 29's inverted weight map, which
`bin/generate.py`'s `check_dominance()` catches before any eval runs — this
mutation deliberately does NOT touch `defaultTest.assert` at all, so it
reaches an actual eval).

**Measured directly** during this delivery: running the mutated config
through the pinned promptfoo produces exactly 9 rows (the one mutated test
row × 3 providers × `repeat: 3`) with `gradingResult.reason == "No
assertions"` — promptfoo's own perfect, assertion-free "pass"
(`evaluator-SSlcaq_U.js:1133-5436`). `bin/verdict.py`'s
`aggregate_cell()` refuses to count any of them, raising immediately with
this fixture's `EXPECT_FAIL_SUBSTRING` baked directly into the exception
message (not only added by the CLI wrapper), so the same substring surfaces
whether `evals.agentic.tests.test_redteam_design`'s real-eval test
(`ProtectedEffectDominanceAndNativeGate.test_real_offline_eval_feeds_a_complete_tranche`,
run against `stop-rule`) lets it propagate uncaught, or a direct
`bin/verdict.py` CLI invocation catches and prints it.

**INERT UNTIL INTEGRATION.** See `26-redteam-npx/DEFECT.md` — same
build_root staging dependency (this mutation additionally needs `plugins/**`
staged alongside `evals/redteam/**`, since the treatment arm reads a real
`plugins/stop-rule/skills/stop-rule/SKILL.md` — already true of
`evals/counterfeits/run.sh`'s existing synthetic-marketplace root, verified
by hand-building an equivalent temp copy), PLUS this delivery's own addition
of `test_redteam_design` to `run.sh`'s offline test-suite invocation.

EXPECT_FAIL_SUBSTRING=redteam FAIL verdict: row
