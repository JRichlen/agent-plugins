# Redteam: pin.json version drift

Rewrites the staged `evals/redteam/pin.json`'s declared `promptfoo.version`
to `0.123.0` — a version this host's actual pinned install (0.122.0) does
not match. `bin/promptfoo.sh` reads `pin.json` as the authority for the
expected version (not a hardcoded literal), so this mutation makes every
invocation of the pinned entrypoint refuse before it ever execs, including
`run.sh`'s own first pin-check step.

**INERT UNTIL INTEGRATION.** See `26-redteam-npx/DEFECT.md` — same
build_root staging dependency.

EXPECT_FAIL_SUBSTRING=redteam FAIL pin: version drift
