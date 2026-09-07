# Counterfeit: a positive card's outcome verifier degenerates to `return True`

**Gate exercised:** the agentic suite's own vacuousness guard over
`evals/agentic/framework/controls.py`'s hidden verifiers (core lane, T10 /
`assert_not_vacuous`), reached via `evals/agentic/run.sh` (offline/`--gate`)
once the integration lane wires cheap-tier section 22
(`evals/cheap/run.sh`) and the corresponding entry in
`evals/counterfeits/run.sh`'s `build_root()`/gate-coverage loop.

**Defect:** `mutate.sh` rewrites the body of
`verify_guarded_delete_outcome` in the staged copy of
`evals/agentic/framework/controls.py` to a single `return True` — the exact
shape T10's negative control names verbatim: "a verifier asserting only
`exit_code == 0` of a script that always exits 0" (here: a verifier that
always reports pass, regardless of the workspace it is handed). Nothing
about the file's *structure* breaks: `controls.py` still imports, still
parses, `MUTATIONS` is untouched, and every OTHER verifier in the module is
unaffected — so any gate that only checks "does controls.py import / does
the test suite still discover tests" stays green. The only thing that must
go red is `assert_not_vacuous(core-guarded-delete-01, ...)`, because no
mutation in `MUTATIONS` can ever flip an unconditional `return True` back to
red, which is precisely the property `test_controls.py`'s
`VacuousVerifierDetection` (and `MutationControl`'s catalog `__negative`
sibling) exist to catch for the corpus's own toy cards.

**Status: WIRED and firing (CV-15).** `evals/agentic/run.sh` exists,
`evals/cheap/run.sh` section 22 stages `evals/agentic/**` into the synthetic
root, and `evals/counterfeits/run.sh`'s gate-coverage loop drives it.
Verified live: `COUNTERFEIT_ONLY=21-agentic-vacuous-verifier bash
evals/counterfeits/run.sh` reports `PASS 21-agentic-vacuous-verifier
rejected by the expected gate ('agentic FAIL core: vacuous verifier')`
alongside the baseline-green calibration step and all six repo-level gates.
The tail below is what `assert_not_vacuous` reports against the mutated
file; `evals/agentic/run.sh`'s own vacuousness check echoes this same
substring (four-space indented, per contract §8.8) through
`evals/cheap/run.sh`'s section 22 and `evals/counterfeits/run.sh`'s grep.

EXPECT_FAIL_SUBSTRING=agentic FAIL core: vacuous verifier
