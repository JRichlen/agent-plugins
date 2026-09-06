# Counterfeit: forged native provenance

**Gate exercised:** the agentic suite's native-evidence gate — contract §5.4's
refusal rule and `contract.assert_native_backed` (T09), backed by the adapter
lane's structural rules in `framework/adapters.py` (T29, T31). Reached via
`evals/agentic/run.sh` (offline / `--gate`) once the integration lane wires
cheap-tier section 22 (`evals/cheap/run.sh`) and the corresponding entry in
`evals/counterfeits/run.sh`'s `build_root()` / gate-coverage loop.

**Defect:** `mutate.sh` applies **both** mutations §8.8 names for this fixture.
Either one alone must fire; applying both means a partial repair of one does not
turn the fixture green on the strength of the other.

**(a) An attempt that simply asserts its own provenance.** A copy of
`evals/agentic/fixtures/native/attempts/forged-native-proven.json` is dropped
into the staged `fixtures/native/attempts/` as a run-shaped attempt record
carrying `evidence_class: "native-proven"`, `adapter_class: "native"`, a
`session_id` no `SESSION_ACK` ever carried, and `event_ids` that exist in no
ledger. It is **schema-valid** — `schemas/attempt.schema.json` cannot see
provenance, which is the whole reason the ledger gate exists — so any check that
validates attempt JSON and stops there stays green. `assert_native_backed` must
raise `ForgedProvenance`.

**(b) A replay path that mints its own host-observed entries.** The staged
`framework/adapters.py` has `ReplaySession.__init__`'s witness guard removed, and
`fixtures/native/replay/forge.py` is dropped in to construct a
`HostLedger(witness=HOST_OBSERVED)` and drive a replay through it. That is the
API-level defeat of ground rule 3 the contract calls out by name: with the guard
gone, a replay holds a ledger that mints correctly-HMAC'd `host-observed`
entries which `verify_chain()` blesses, `host_observed_session_ids()` accepts,
and §5.4 clauses 2 and 4 then wave through — a recorded stream laundered into
`NATIVE_PROVEN` with no error anywhere. Nothing structural breaks: `adapters.py`
still imports, every other test in the module still passes, and
`evidence_class_for`'s mapping is untouched. The mutation is three lines and it
is invisible to any gate that is not specifically looking for it.

Note what is deliberately **not** mutated: `evidence_class_for` itself. Rewriting
it would be testing the wrong rule — it is a pure four-branch mapping over
`(adapter_class, chain)` whose correctness is already asserted directly, and a
forger with commit access to it has already won. The interesting forgeries are
the ones that leave the mapping honest and lie to it about its inputs.

**Status: INERT until the integration lane wires this in.** As of this change
`evals/agentic/run.sh` does not exist (integration-owned, contract §1/§6),
`evals/cheap/run.sh` section 22 has not been added, and
`evals/counterfeits/run.sh`'s `build_root()` does not yet stage
`evals/agentic/**` into the synthetic root. Until all three land this fixture
cannot run inside the counterfeit tier's gate-coverage loop. Once section 22 is
wired, the substring below is what `evals/agentic/run.sh`'s own provenance check
must echo (four-space indented, per contract §8.8) through `evals/cheap/run.sh`
section 22, where `evals/counterfeits/run.sh` greps for it.

EXPECT_FAIL_SUBSTRING=agentic FAIL adapter: forged_provenance
