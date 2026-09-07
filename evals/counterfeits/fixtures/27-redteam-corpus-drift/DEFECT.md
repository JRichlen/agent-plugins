# Redteam: corpus hash drift

Flips one byte of a committed adversarial corpus file in the staged copy of
`evals/redteam/corpus/`, leaving `corpus/manifest.json` unchanged. This is
the exact defect `bin/freeze.py --check` (T44) exists to catch, and
`evals/redteam/run.sh` calls it before anything else.

**WIRED AND LIVE (verified 2026-09-07).** The staging dependency this
paragraph used to be blocked on has landed: `evals/counterfeits/run.sh`'s
`build_root()` copies `evals/redteam/**` into the synthetic root
(`run.sh:67`) and the "redteam suite (offline)" gate-coverage entry
(`run.sh:146`) asserts that gate actually fires there. Measured with
`COUNTERFEIT_ONLY=27-redteam-corpus-drift evals/counterfeits/run.sh`:
`PASS 27-redteam-corpus-drift rejected by the expected gate`, 8 passed / 0 failed.

EXPECT_FAIL_SUBSTRING=redteam FAIL corpus: hash drift
