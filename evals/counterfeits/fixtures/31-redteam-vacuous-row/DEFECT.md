# Redteam: a vacuous row scored as a perfect pass

Sets `options: {disableDefaultAsserts: true}` on ONE test row in the staged
`evals/redteam/configs/generated/stop-rule.yaml` — a real route to vacuity
promptfoo documents (`testCase.options.disableDefaultAsserts`,
`evaluator-SSlcaq_U.js:7832`). `bin/generate.py` never emits a per-row
`assert:` override anywhere (every row relies entirely on
`defaultTest.assert`, design §7.4/§8.1), so a row that disables the default
asserts and carries none of its own has, BY CONSTRUCTION, zero effective
assertions — a defect `evals/redteam/run.sh --gate`'s static per-row scan
(added 2026-09-06) catches directly from the committed YAML text, the same
regex-over-generated-text technique `bin/generate.py`'s own
`check_dominance()` already uses for fixture 29's weight-map defect. No
promptfoo process runs to catch this fixture.

**History (2026-09-06):** this fixture originally exercised the RUNTIME half
of the defect — an actual `promptfoo eval` of the mutated config, feeding
`bin/verdict.py`'s `aggregate_cell()`, which raises `"redteam FAIL verdict:
row ..."` once promptfoo scores the disabled-assertions row a perfect,
assertion-free "pass" (`evaluator-SSlcaq_U.js:1133-5436`). That mechanism is
still real and still tested — `evals.agentic.tests.test_redteam_provider`'s
`ClassifyRowFaultVsVacuous` and `test_redteam_design`'s
`test_vacuous_row_is_never_counted_as_pass`/
`test_real_offline_eval_feeds_a_complete_tranche` exercise it directly, and
`evals/redteam/run.sh` (no flag / `--offline`) still runs that full test
suite for real — but it was removed from `--gate` specifically: under heavy
host CPU contention it intermittently misclassified an ordinary provider
FAULT (a call that errored/timed out, `gradingResult: null`) as VACUOUS,
because `classify_row`'s VACUOUS check ran before its `failureReason == 2`
check (both shapes have zero `componentResults`). That ordering bug is fixed
in `bin/verdict.py` directly; the real-eval step is not restored to `--gate`
regardless, because a flaky always-on gate is worse than a documented
static/runtime split. This fixture's own mutation did not change — it
already wrote exactly the statically-visible shape the new scan targets.

**INERT UNTIL INTEGRATION.** See `26-redteam-npx/DEFECT.md` — same
build_root staging dependency (this mutation additionally needs `plugins/**`
staged alongside `evals/redteam/**`, since the treatment arm reads a real
`plugins/stop-rule/skills/stop-rule/SKILL.md` — already true of
`evals/counterfeits/run.sh`'s existing synthetic-marketplace root, verified
by hand-building an equivalent temp copy).

EXPECT_FAIL_SUBSTRING=redteam FAIL design: vacuous row
