---
name: criteria-contract
description: Prepare and pin agreed executable acceptance criteria for a selected verify-work case. Observe negative controls before work and protect the pinned checker afterward.
license: MIT
---

# Prepare an acceptance contract

Dependency of [verify-work](../verify-work/SKILL.md), not an automatic prerequisite
for every task. The [core](../../context/OPERATING.md) owns authority and
scope; use the existing task record for required agreement and decisions.

1. Run `scripts/scaffold-run.sh --slug <slug> --root <workspace>` to create the
   compatibility-format case. Existing cases are never overwritten.
2. Replace template criteria with testable statements and `check_cmd` lines.
   Keep required human observations as WITNESS. Include at least two executable
   checks and more executable checks than human observations.
3. Run the generated checker and observe every executable criterion reject the
   applicable negative state/control. Exit 1 means criterion failure; exit 99
   means a broken harness and does not count as a negative proof.
4. After the required owner agreement, run `scripts/scaffold-run.sh --pin <slug>
   --root <workspace>`. This records hashes of criteria and checker. Pinning is
   an integrity operation; a hash alone is not evidence of human authorization.

The `.redgate/` path and ARM/TRACE manifest labels remain a compatibility data
format. No recursive round, budget or cadence policy follows from those labels.
After pinning, return the case path and negative-control evidence to the task
owner. Do not edit ratified artifacts during work. A requirement change needs
a new contract rather than a re-pin of the old one.

`scripts/criteria-index.sh` optionally indexes existing records as pointers.
It is not a required new record or proof that an old check is applicable now.
