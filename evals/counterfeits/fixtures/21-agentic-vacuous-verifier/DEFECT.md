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

**Status: INERT until the integration lane wires this in.** As of this
change, `evals/agentic/run.sh` does not exist (it is an integration-owned
deliverable, contract §1/§6), `evals/cheap/run.sh` section 22 has not been
added, and `evals/counterfeits/run.sh`'s `build_root()` does not yet stage
`evals/agentic/**` into the synthetic root. Until all three land, this
fixture cannot actually run inside the counterfeit tier's gate-coverage
loop — the tail below documents what a lane-local run of
`assert_not_vacuous` against the mutated file reports, not a result from
`evals/counterfeits/run.sh` itself. Once section 22 is wired, this fixture's
`EXPECT_FAIL_SUBSTRING` is what `evals/agentic/run.sh`'s own vacuousness
check must echo (four-space indented, per contract §8.8) through
`evals/cheap/run.sh`'s section 22 and `evals/counterfeits/run.sh`'s grep.

EXPECT_FAIL_SUBSTRING=agentic FAIL core: vacuous verifier
