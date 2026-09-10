# Zero denominator rendered as a number

Patches `evals/agentic/framework/analysis.py`'s `Rate.render` so that a
zero-denominator rate (no valid samples, an all-fault card, an empty matched
stratum) prints `0%` instead of `unavailable (<reason>)`. `0%` reads as "the
plugin failed" when the truth is "nothing was measured" -- exactly the banned
rendering benchmark-spec §7 and backlog item T38 name, and the same failure
mode T38's own negative-control test in `test_analysis.py`
(`ZeroDenominatorUnavailable.test_naive_zero_over_max_valid_one_reads_as_the_plugin_failed`)
exercises directly against the unmutated source.

Inert until the integration lane wires `evals/agentic/run.sh` and
`build_root()`'s staging of `evals/agentic/**` (contract §8.8): this fixture's
`mutate.sh` only performs the source patch; the FAIL substring below is
produced once `evals/agentic/run.sh` runs the measurement suite (or an
equivalent zero-denominator check) against the mutated copy and observes a
`0%` rendering where `unavailable (...)` was required. Until that wiring
lands, running this fixture through `evals/counterfeits/run.sh` has nothing
that consumes the mutation and it will not yet fail closed -- reported here
explicitly, per the task brief's instruction, rather than silently.

EXPECT_FAIL_SUBSTRING=agentic FAIL measurement: zero denominator rendered as a number
