---
name: prove-the-undo
description: >-
  Rehearse the rollback before any irreversible action: name the specific
  restore path and demonstrate it works — never proceed on the strength of
  'a backup exists'. Use before deletes, drops, force-pushes, migrations,
  or any action semver-gate classifies as MAJOR.
license: MIT
compatibility: >-
  PORTABILITY: pure procedural discipline — no hooks, no subagent-spawning
  tool, no Workflow tool, no harness-specific primitive. The rehearsal is
  ordinary commands (restore into a scratch path, diff, dry-run) that any
  harness with a shell can run. Ports anywhere the agent can execute a
  command and read its output before acting.
---

# prove-the-undo

## Invariant

An irreversible action is ALWAYS preceded by a named restore path that was
actually exercised (restored, diffed, or dry-run-verified) in this session —
and NEVER justified by the mere existence of an unverified backup.

## Not this

Two siblings in this marketplace sit adjacent. Neither is this skill:

- **semver-gate** (`plugins/semver-gate`) *classifies* an action's blast
  radius and decides whether to stop and ask a human. It answers "may I do
  this?". prove-the-undo answers the next question: "if I do this and it's
  wrong, can I actually get back?" — and demands the answer be a rehearsed
  demonstration, not an assumption. A MAJOR classification from semver-gate
  is a natural trigger for this skill, but human sign-off does not substitute
  for a rehearsed restore: sign-off authorizes the action, the rehearsal
  proves the exit. Run both.

- **graveyard** (`plugins/graveyard`) is one concrete instance of this
  discipline for one domain: it never deletes a GitHub repo until its bundle
  is confirmed present in the graveyard. prove-the-undo is the general form —
  the same archive-then-verify shape applied to any irreversible action:
  dropped tables, force-pushes, config overwrites, resource teardowns,
  destructive migrations.

## When to use this

Run the rehearsal immediately before any action where the undo is not a
cheap retry: deleting files or resources you didn't create, `git push
--force` or history rewrites, schema migrations, dropping data, overwriting
state that has no other copy, tearing down infrastructure, or anything
semver-gate would classify MAJOR on its reversibility property. Trigger
phrases: "before we delete", "is it safe to drop", "prove the rollback",
"rehearse the undo".

## The rehearsal

Before the irreversible action, produce all three, in order:

1. **Name the restore path.** One specific, executable statement: *"restore
   is `git bundle unbundle X`"*, *"restore is `terraform apply` from this
   committed state"*, *"restore is this pg_dump at this path"*. "We have
   backups" is not a restore path — it names no artifact, no command, no
   destination.

2. **Exercise it now, in this session.** Pick the strongest form the
   situation allows, in this preference order:
   - **Full rehearsal**: restore into a scratch location and diff against
     the original (`git clone bundle.git && git diff`, restore the dump into
     a scratch database and row-count it).
   - **Verified integrity**: run the artifact's own verifier
     (`git bundle verify`, `pg_restore --list`, checksum against a manifest).
   - **Dry run**: the tool's `--dry-run`/plan mode showing the restore would
     apply cleanly.
   A backup that was written but never read back is unverified; reading it
   back is the entire point of this skill.

3. **Attach the evidence.** The literal output of step 2 sits next to the
   go/no-go decision — same message, same script, same PR comment. If the
   action is delegated to the user (a generated script, a runbook), the
   script itself must gate the destructive step on the verification: check
   first, delete only on success, abort otherwise.

Only after all three does the irreversible action proceed. If step 2 fails
or can't be run, the action is blocked — report what could not be verified
instead of proceeding, and never downgrade to "the backup probably works."

## Failure modes this exists to stop

- "The backup exists" (never opened, never verified) as sole justification.
- Rehearsing the *backup* but not the *restore* — writing succeeded, reading
  was never attempted.
- Verifying once, days ago, in another session — state drifted since; the
  rehearsal is per-session, per-action.
- A generated cleanup script that deletes unconditionally, with the
  verification only in prose the user may not read.
