# Redteam: corpus hash drift

Flips one byte of a committed adversarial corpus file in the staged copy of
`evals/redteam/corpus/`, leaving `corpus/manifest.json` unchanged. This is
the exact defect `bin/freeze.py --check` (T44) exists to catch, and
`evals/redteam/run.sh` calls it before anything else.

**INERT UNTIL INTEGRATION.** See `26-redteam-npx/DEFECT.md` — same
build_root staging dependency.

EXPECT_FAIL_SUBSTRING=redteam FAIL corpus: hash drift
