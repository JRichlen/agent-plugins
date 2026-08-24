---
description: >-
  Keep every hunk of the diff traceable to the stated task: anything discovered outside scope is recorded as a finding (ticket, note, diary entry) — never fixed in the same change. Use when starting any bounded task, when tempted to 'fix it while I'm here', or when reviewing whether a diff crept beyond its mandate.
---

Invoke the `scope-fence` skill and follow `skills/scope-fence/SKILL.md`.

If a task is starting: state the fence (task in one sentence, plus what's
explicitly out when boundaries are fuzzy) before the first edit, route every
out-of-scope discovery to a recorded finding instead of fixing it, and audit
the final diff hunk-by-hunk against the fence before declaring done. If a
diff already exists: run the audit now — trace each hunk to the stated task,
revert hunks that trace only to discoveries, and convert them to findings.
The fence widens only on the user's explicit instruction, never on your own
judgment.
