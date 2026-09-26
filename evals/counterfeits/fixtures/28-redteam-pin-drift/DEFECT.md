# Redteam: pin.json version drift

Rewrites the staged `evals/redteam/pin.json`'s declared `promptfoo.version`
to `0.123.0` — a version this host's actual pinned install (0.122.0) does
not match. `bin/promptfoo.sh` reads `pin.json` as the authority for the
expected version (not a hardcoded literal), so this mutation makes every
invocation of the pinned entrypoint refuse before it ever execs, including
`run.sh`'s own first pin-check step.

**WIRED AND LIVE (verified 2026-09-07).** The staging dependency this
paragraph used to be blocked on has landed: `evals/counterfeits/run.sh`'s
`build_root()` copies `evals/redteam/**` into the synthetic root
(`run.sh:67`) and the "redteam suite (offline)" gate-coverage entry
(`run.sh:146`) asserts that gate actually fires there. Measured with
`COUNTERFEIT_ONLY=28-redteam-pin-drift evals/counterfeits/run.sh`:
`PASS 28-redteam-pin-drift rejected by the expected gate`, 8 passed / 0 failed.

EXPECT_FAIL_SUBSTRING=redteam FAIL pin: version drift
