---
description: >-
  Rehearse the rollback before any irreversible action: name the specific restore path and demonstrate it works — never proceed on the strength of 'a backup exists'. Use before deletes, drops, force-pushes, migrations, or any action semver-gate classifies as MAJOR.
---

Invoke the `prove-the-undo` skill and follow `skills/prove-the-undo/SKILL.md`.

Take the irreversible action the user is about to perform (or the one just
described) and run the three-step rehearsal: name the specific restore path
as an executable statement, exercise it now (full scratch-restore + diff,
artifact verifier, or dry run — strongest form available), and attach the
literal verification output next to the go/no-go decision. If verification
cannot be run or fails, block the action and report exactly what could not
be proven. If the action is handed to the user as a script, gate the
destructive step on the verification inside the script itself.
