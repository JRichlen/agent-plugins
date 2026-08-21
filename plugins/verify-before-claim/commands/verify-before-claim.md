---
description: >-
  Never assert a fact, completion, or reproduction claim without naming and
  running the specific check that would prove it false, first. Use before
  writing "done", "fixed", "passes", "confirmed", "verified", "reproduced",
  or any sentence that states a fact about the codebase or the world.
---

Invoke the `verify-before-claim` skill and follow `skills/verify-before-claim/SKILL.md`.

Before writing the claim you are about to write, run the core procedure: name
the single observation that would prove it false, run that exact check
directly in this turn, then write the claim with the check's literal output
attached next to it. If the check could not be run, say so explicitly and
adjacently — "not verified: X" or "assumed, unchecked: X" — never asserted as
settled. Consult the reference dispatcher table in the SKILL.md if the claim
is a bug-report/merge-readiness claim, is headed into a handoff deliverable,
cites an external source, or depends on what a skill/tool/command actually
does; load the matching `skills/verify-before-claim/references/*.md` file for
that situation's specific procedure.
