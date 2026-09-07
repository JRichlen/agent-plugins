# Redteam: npx invocation inserted

Inserts an actual `npx promptfoo@latest` invocation SHAPE into the staged copy
of `evals/redteam/run.sh` (real invocation shape, not the bare word — this
lane's own diagnostic strings legitimately name "npx" without being one),
wrapped in a shell function that is never called so it can never execute.
`evals/redteam/run.sh`'s own npx gate (`bin/npxcheck.py`) must catch it and
red the run before any config is validated or any test executes.

The first version of this fixture inserted a bare statement; running the
staged copy executed it before the gate and reached the network, upgrading the
host's shared npx cache in place (2026-09-06). A counterfeit mutation must be
detectable, never executable, and the counterfeit runner now also shims
`npx`/`npm` out of PATH so an executable mutation fails loudly (exit 99)
instead of reaching the network.

**WIRED AND LIVE (verified 2026-09-07).** The staging dependency this
paragraph used to be blocked on has landed: `evals/counterfeits/run.sh`'s
`build_root()` copies `evals/redteam/**` into the synthetic root
(`run.sh:67`) and the "redteam suite (offline)" gate-coverage entry
(`run.sh:146`) asserts that gate actually fires there. Measured with
`COUNTERFEIT_ONLY=26-redteam-npx evals/counterfeits/run.sh`:
`PASS 26-redteam-npx rejected by the expected gate`, 8 passed / 0 failed.

EXPECT_FAIL_SUBSTRING=redteam FAIL offline: npx reference in evals/redteam
