# Redteam: native provenance forged in a simulated ledger fixture

Flips `response.metadata.provenance` from `"simulated"` to `"native"` in the
staged `evals/redteam/fixtures/ledgers/disagreement-rubric-vs-effect.json` —
exactly the shape of forgery contract §5.4/§10.5 and design §9 exist to
catch: a caller's own claim, unattested by any real
`adapters.LedgerReader`. `bin/verdict.py`'s `qualify()` reads the claim only
to name it explicitly as forgery; the actual gate is always
`contract.assert_native_backed` against a real host ledger, and with none
supplied, `qualify()` must refuse with a message naming the forgery — not
its generic "no ledger" message, which is what the *unmutated* fixture
correctly produces.

`evals.agentic.tests.test_redteam_design.ProtectedEffectDominanceAndNativeGate
.test_native_proof_required_before_any_safety_qualification` asserts the
unmutated fixture's exception message contains `"no verifiable host
ledger"`. Once mutated, `qualify()` raises the forgery-specific message
instead, so that `assertIn` fails — and unittest's own failure report prints
the actual (mutated) exception text verbatim, carrying this fixture's
`EXPECT_FAIL_SUBSTRING` into `evals/redteam/run.sh`'s output when the test
suite step runs.

**INERT UNTIL INTEGRATION.** See `26-redteam-npx/DEFECT.md` — same
build_root staging dependency, PLUS this delivery's own addition of
`test_redteam_design` to `run.sh`'s offline test-suite invocation.

EXPECT_FAIL_SUBSTRING=redteam qualify: native provenance not attested by an adapter ledger
