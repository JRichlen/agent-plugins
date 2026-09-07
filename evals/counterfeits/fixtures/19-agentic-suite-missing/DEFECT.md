# Counterfeit: the agentic suite runner is missing entirely

**Gate exercised:** `evals/cheap/run.sh` section 22's fail-closed discovery
of `evals/agentic/run.sh` (contract §9.1, integration lane). Ground rule 4:
"a missing lane, missing runner ... is a failure, never a skip." A cheap
tier that silently skipped the whole agentic suite because its entry point
vanished would defeat the entire always-on gate this backlog exists to add.

**Defect:** `mutate.sh` deletes the staged `evals/agentic/run.sh` from the
synthetic root. Nothing else about `evals/agentic/**` is touched — every
framework module, every test, every fixture is still present and would
still pass if invoked directly. The ONLY thing broken is the entry point
`evals/cheap/run.sh` section 22 is wired to call.

A cheap tier that used `set -e`-style silent tolerance, or that guarded the
whole agentic block behind a soft `[ -f ... ] && ...` with no `else`, would
report green here — exactly the "missing pack = silent skip" failure mode
section 10 already forbids for per-plugin packs, extended to the two new
eval directories this backlog adds.

EXPECT_FAIL_SUBSTRING=agentic suite gate: evals/agentic/run.sh is missing
