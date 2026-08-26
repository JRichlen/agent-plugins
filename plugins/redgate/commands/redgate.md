---
description: >-
  Run any idea through Red Gate: human-gated rounds, each a BEGIN/MIDDLE/END process whose BEGIN emits a verifier proven able to fail before work starts, and whose END is that pinned verifier run by a party that did not do the work. Use on /redgate "<idea>", or whenever a task needs its done-criteria proven falsifiable before building.
---

Invoke the `redgate` skill and follow `skills/redgate/SKILL.md`.

Take the idea given as the argument. Apply the round-zero rule to pick the
round type (orientation / plan / build / consolidation), then drive one
round: BEGIN via the `criteria-contract` skill (interview ≤5 questions,
scaffold `.redgate/<slug>/` with `skills/criteria-contract/scripts/scaffold-run.sh`,
write 3–7 criteria, prove the gate red, ratify, pin), MIDDLE as one
tracer-bullet slice with a single writer, END by running the pinned
`check.sh` from a context that did not do the work. Stop at the round gate:
accept / again / split is the human's call, as is funding the next round
against the manifest's round budget.
