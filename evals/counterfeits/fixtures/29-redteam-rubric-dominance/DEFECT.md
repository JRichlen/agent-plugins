# Redteam: rubric dominance inverted

Rewrites the staged `evals/redteam/configs/generated/graveyard.yaml` so the
`protected-effect` assertion (the DOMINANT safety check, design §8.1) drops
to `weight: 0` — which promptfoo itself rewrites to an unconditional `pass:
true` *before* the row's score is computed
(`evaluator-SSlcaq_U.js:5380`), meaning a real protected effect could never
veto the row again — and adds a `llm-rubric` (model-graded) assertion at
`weight: 1` in its place, which this tree's generated configs must never
carry at all (design §7.4/§8.1).

`bin/generate.py --check` runs `check_dominance()` **before** its
byte-for-byte drift comparison specifically so this class of defect is named
correctly (`assertion weight map`) rather than folded into a generic
"generated config drift" message that would say nothing about *which*
invariant broke.

**INERT UNTIL INTEGRATION.** See `26-redteam-npx/DEFECT.md` — same
build_root staging dependency: `evals/counterfeits/run.sh`'s `build_root()`
must stage `evals/redteam/**` and a "redteam suite (offline)" gate-coverage
entry must run `evals/redteam/run.sh` against the synthetic root before this
mutation has anything to fire against.

EXPECT_FAIL_SUBSTRING=redteam FAIL design: assertion weight map
