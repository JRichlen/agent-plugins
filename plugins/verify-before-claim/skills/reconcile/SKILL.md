---
name: reconcile
description: Independently run an agreed pinned acceptance checker, reject changed criteria or stale/missing evidence, and return the observed verdict to the task owner.
license: MIT
---

# Reconcile an acceptance result

Enter for a selected [verify-work](../verify-work/SKILL.md) case, from an actual
reviewer/context that did not produce the work. Read the pinned criteria,
checker, relevant source and change. Preserve reviewer provenance in the existing
task record; the script cannot mechanically establish reviewer independence.

Run `scripts/reconcile.sh --slug <slug> --root <workspace>`.

- Unpinned or missing case: refused, exit 2.
- Changed criteria/checker: drift, exit 1.
- Harness fault: no valid verdict, exit 1; do not count it as negative proof.
- Unmet criterion or missing/stale evidence: not accepted, exit 1.
- Green executable criteria with evidence from this execution: exit 0, subject
  to criterion quality, required human observations and independent provenance.

Use an applicable mutation/counterexample control to establish that a check
rejects the wrong state. A check that remains green when its relevant change
is removed is not proof of that behavior. Preserve WITNESS observations as
unproven until the required human observation occurs.

Return the verdict, actual evidence and remaining limits to the task owner.
Do not prescribe another delivery round or grant release/action authority.
