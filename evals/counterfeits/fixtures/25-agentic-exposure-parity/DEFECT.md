# Counterfeit: unmatched-widening baseline arm (exposure parity)

**Gate exercised:** the agentic suite's own exposure-parity guard,
`evals.agentic.framework.pairing.assert_exposure_parity` (registry lane,
T16 / contract §3.11 clause (c)), reached via `evals/agentic/run.sh`
(offline/`--gate`) once the integration lane wires cheap-tier section 22
(`evals/cheap/run.sh`) and the corresponding entry in
`evals/counterfeits/run.sh`'s `build_root()`/gate-coverage loop.

**Defect:** `mutate.sh` appends the literal tool name `"AdminOverride"` to
`baseline_arm.allowed_tools` in the staged copy of
`evals/agentic/manifests/arms/graveyard.json`. `"AdminOverride"` is neither
one of the shared generic tools both arms already carry, nor the declared
`generic_equivalent` of any capability in the SAME file's
`full_package_arm.capabilities` -- it is exactly the "unmatched widening"
contract §3.11 clause (c) forbids: *"Unmatched widening on either side
remains a violation -- that is what counterfeit fixture 25 exercises."*

This is deliberately NOT the same shape as a legitimate baseline
capability substitution. `graveyard.json`'s real `baseline_arm` already
carries `"bash+gh manual guarded-delete checklist"`, the matched,
one-for-one `generic_equivalent` of `full_package_arm`'s
`generate-delete-script.sh` capability -- a fixture that flagged THAT
entry would be testing the wrong rule (matched substitution is the allowed
baseline itself, benchmark-spec §4.1). `mutate.sh` leaves that legitimate
substitution untouched and adds a second, extraneous tool instead, so the
gate this fixture exercises is unmatched widening specifically, not
widening as such.

Nothing about the file's structure breaks: the JSON still parses, both
`full_package_arm` and `baseline_arm` still carry every other required key,
and `full_package_arm` is completely untouched -- so any gate that only
checks "does the manifest parse / does the schema validate" stays green.
The only thing that must go red is
`pairing.assert_exposure_parity(Arm.from_dict(full_package_arm),
Arm.from_dict(mutated_baseline_arm))`, which
`evals.agentic.tests.test_pairing.ExposureParity`'s
`__negative` method already exercises directly (not through this staged
file) as part of T16's acceptance.

**Status: INERT until the integration lane wires this in.** As of this
change, `evals/agentic/run.sh` does not exist (it is an integration-owned
deliverable, contract §1/§6), `evals/cheap/run.sh` section 22 has not been
added, and `evals/counterfeits/run.sh`'s `build_root()` does not yet stage
`evals/agentic/**` into the synthetic root. Until all three land, this
fixture cannot actually run inside the counterfeit tier's gate-coverage
loop -- the check below documents what a lane-local run of
`pairing.assert_exposure_parity` against the mutated manifest reports (via
`Arm.from_dict`), not a result from `evals/counterfeits/run.sh` itself.
Once section 22 is wired, this fixture's `EXPECT_FAIL_SUBSTRING` is what
`evals/agentic/run.sh`'s own exposure-parity check must echo (four-space
indented, per contract §8.8) through `evals/cheap/run.sh`'s section 22 and
`evals/counterfeits/run.sh`'s grep.

**Verified lane-locally** (offline, no model call) with:

```
python3 -c "
import json
from evals.agentic.framework import pairing
doc = json.load(open('<staged-root>/evals/agentic/manifests/arms/graveyard.json'))
full = pairing.Arm.from_dict(doc['full_package_arm'])
base = pairing.Arm.from_dict(doc['baseline_arm'])
pairing.assert_exposure_parity(full, base)
"
```

which raises `ExposureParityViolation: 1 impermissible divergence(s):
allowed_tools:AdminOverride: treatment='<absent>' baseline='AdminOverride'
(baseline-only tool that is not the declared generic_equivalent of any
treatment capability (unmatched widening))` -- the substring
`agentic FAIL registry: exposure parity` below is the frozen output
contract `evals/agentic/run.sh` (integration-owned) must produce when it
wraps this same check.

EXPECT_FAIL_SUBSTRING=agentic FAIL registry: exposure parity
