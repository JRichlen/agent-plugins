# Redteam: npx invocation inserted

Inserts an actual `npx promptfoo@latest` invocation into the staged copy of
`evals/redteam/run.sh` (real invocation shape, not the bare word — this
lane's own diagnostic strings legitimately name "npx" without being one).
`evals/redteam/run.sh`'s own npx gate (`bin/npxcheck.py`) must catch it and
red the run before any config is validated or any test executes.

**INERT UNTIL INTEGRATION.** This fixture requires `evals/counterfeits/run.sh`'s
`build_root()` to stage `evals/redteam/**` into the synthetic root (contract
§8.8 — not yet wired as of this delivery) and a "redteam suite (offline)"
gate-coverage entry that actually runs `evals/redteam/run.sh` against the
synthetic root. Until both land, this fixture's `mutate.sh` has nothing to
mutate and nothing exercises it.

EXPECT_FAIL_SUBSTRING=redteam FAIL offline: npx reference in evals/redteam
