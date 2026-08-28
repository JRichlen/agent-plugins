---
description: >-
  Run any idea through Red Gate: rounds of BEGIN/MIDDLE/END with graduated autonomy — each round gate is classified PATCH/MINOR/MAJOR via semver-gate, so derived work auto-passes inside a human-approved plan envelope while orientation decisions, plan approval, and irreversible actions always block on the human. BEGIN emits a verifier proven able to fail; END is that pinned verifier run by a party that did not do the work. Use on /redgate "<idea>", or whenever done-criteria must be proven falsifiable before building.
---

Invoke the `redgate` skill and follow `skills/redgate/SKILL.md`.

Take the idea given as the argument. **Calibrate first** per
`skills/redgate/references/calibration.md`: set tier, domain, scope, taste,
and orchestration (infer, label stated/inferred, ask only load-bearing
unknowns). A T0 task is done directly with no run — say so and do it. For
T1+, apply the round-zero rule to pick the round type (orientation / plan /
build / consolidation), then drive one round: BEGIN via the
`criteria-contract` skill (interview ≤5 questions total including
calibration, calibration block written into the CRITERIA.md header,
scaffold `.redgate/<slug>/` with `skills/criteria-contract/scripts/scaffold-run.sh`,
write 3–7 criteria, prove the gate red, ratify, pin), MIDDLE as one
tracer-bullet slice with a single writer, END by running the pinned
`check.sh` from a context that did not do the work. At the round gate, classify with
semver-gate's four-property test: PATCH (strictly derived from an approved
plan slice, verifier green, no escalator) auto-passes and is logged to
gates.log; MINOR auto-passes with a prominent flag and standing veto; MAJOR —
orientation decisions, plan approval, first ratification, UNVERIFIABLE
countersignatures, fence/budget changes, anything irreversible — stops for a
structured human question. Funding rounds beyond the manifest budget is
always MAJOR.
