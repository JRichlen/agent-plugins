---
name: semver-gate
description: >-
  Classify a candidate action as PATCH/MINOR/MAJOR (semver-style blast-radius test) before acting — act silently on PATCH, flag-and-stage MINOR, stop for explicit human sign-off on MAJOR. Use whenever you're mid-task and unsure how much autonomy to take on the next action: which of several implementation paths to pick, whether to overwrite unreviewed state, whether to disable a safety toggle, or any judgment call settings.json's autoMode patterns don't enumerate.
---

# semver-gate

## Invariant

A MAJOR-classified action must never be taken without explicit, specific prior
human sign-off on that exact action and mechanism — not inferred from a prior
adjacent confirmation, not assumed from a general instruction, not skipped
under time pressure or retry pressure, and never routed around when a
separate structural block (classifier, permission denial, API-level policy)
fires after sign-off was already given. Every eval for this skill exists to
defend this one rule; everything else in the design (PATCH silence, MINOR
flagging, staging behavior) is allowed to be approximate, but this rule is
never allowed to soften.

## What this is (and isn't)

semver-gate is a **mid-task judgment aid**, not a new policy layer. It gives
you a fast, named, three-way classification test to run on a candidate action
*before* taking it, the moment you notice you aren't sure which bucket it
falls in. It borrows a vocabulary you already have memorized cold — semver's
PATCH / MINOR / MAJOR — so classifying an action is a lookup against a table,
not a fresh vibe-check every time.

It sits strictly **below** two things that already exist and it never
overrides either of them:

1. **The system prompt's "Executing actions with care" section.** That prose
   already governs every action you take: *"Carefully consider the
   reversibility and blast radius of actions... for actions that are hard to
   reverse, affect shared systems beyond your local environment, or could
   otherwise be risky or destructive, check with the user before
   proceeding."* semver-gate adds **no new criteria** on top of this. It
   operationalizes the same two axes (reversibility, blast radius) into a
   checklist with a memorized vocabulary, and makes two sub-questions the
   prose leaves implicit into explicit checks: *does this change a contract
   someone else depends on*, and *what does it cost to undo*. If this skill's
   table and the system prompt's principle ever seem to disagree, the prose
   is the ground truth the table exists to serve — re-read the property
   definitions in the rubric rather than assume the table is wrong.

2. **settings.json's `autoMode` block** (`hard_deny` / `soft_deny` / `allow`
   pattern matches — e.g. `Bash(pnpm db:push:*)` in a repo where that bypasses
   the migration workflow, or protected-branch pushes). Where a coded rule
   already matches the candidate action, **it always wins, full stop**,
   regardless of what semver-gate concludes. semver-gate exists only for the
   much larger space a pattern list can't enumerate: "which of these three
   implementation approaches," "should I disable this repo-wide safety
   toggle," "should I overwrite this file that has unreviewed local
   changes."

Precedence, concretely:

```
1. autoMode hard_deny / soft_deny / allow pattern match  -> coded rule wins, always
2. "Executing actions with care" (system prompt)          -> the principle this table serves
3. semver-gate's classification table                     -> everything else: judgment calls no pattern enumerates
```

## When to use this

Reach for semver-gate mid-task, right before you act, whenever you notice
you're not sure how much autonomy to take on the next step:

- Picking between two or more reasonable implementation approaches.
- About to overwrite a file, config, or resource that has state you didn't
  create (unreviewed local changes, another process's output, prod config).
- About to touch anything that looks like a safety toggle, protection
  setting, or guardrail — even if the user just said something adjacent like
  "merge it" or "ship it."
- About to do something you *could* undo, but the undo isn't a cheap retry —
  it's a restore, a renegotiation, or a "sorry, please trust me again."

Do **not** use this as a separate planning phase run once at the start of a
session — it's a lookup you run in the moment, per action, not a report you
produce up front.

## The classification test

Ask these four questions, in order, about the specific candidate action (not
the whole task it's part of):

1. **Reversibility** — can this be undone by a subsequent, comparably cheap
   action, with no residue?
2. **Blast radius / visibility** — does the effect stay inside your own local
   working state, or does it become visible to / affect the user, teammates,
   or systems beyond the current task?
3. **Contract change** — does this touch an interface, schema, protection
   rule, or promise someone else (a person or another system) currently
   relies on?
4. **Cost to undo** — if it does need undoing, is that a retry/revert
   (cheap), or a restore-from-backup / renegotiation / trust-repair
   (expensive or unbounded)?

Then apply the **tie-break rule**, borrowed directly from Conventional Commits'
`BREAKING CHANGE` footer overriding whatever type carries it: **if any single
property lands in MAJOR, the whole action is MAJOR**, no matter how many other
properties land in PATCH or MINOR. Additive-but-destructive
always collapses to MAJOR — e.g. "just adding a config flag" that happens to
flip off a protection is MAJOR, not MINOR, because property 3 landed there.

The full decision table with all three tiers spelled out per property lives
in [`references/rubric.md`](references/rubric.md) — load it whenever you need
the exact wording to classify an edge case, or want to point at a specific
cell to justify a classification. Keep this file lean; that one is the
greppable reference the cheap eval asserts against.

## Behavior per tier

- **PATCH** → act now, no pause, no dedicated flag. Mention it once, folded
  into the ordinary summary of the work. Example: fixing a typo in a
  comment, re-running a failed test, adjusting a local scratch file.

- **MINOR** → act now, but flag it prominently and separately — called out
  at the moment it happens ("I also added X because Y"), not buried at the
  end in a final summary. If there is a genuine second reasonable path (not
  a hypothetical one), name it and say why the chosen one was picked; offer
  to switch if the user would rather have the alternative. This is a flag,
  **never** a blocking question. Example: adding a new optional field,
  writing a new file, proposing a new test.

- **MAJOR** → stop before acting. Use a structured question (AskUserQuestion
  or equivalent) to get explicit sign-off on the **specific action and
  mechanism** — not a generic "sounds good, proceed." A prior "yes" to an
  adjacent or general request (e.g., "merge it") does not transfer to
  the specific MAJOR mechanism (e.g., "disable `enforce_admins` to merge
  it") — ask again, naming that mechanism by name. If a structural block (a
  `hard_deny`/`soft_deny` classifier, an API-level policy denial, a
  permission or scope denial) fires mid-attempt even after sign-off,
  do not route around it: surface exactly what fired and why, then offer
  the least-destructive alternative path forward and wait again. A different
  credential, token, or scope that would get past the block — including one
  already sitting in the environment — is a route around it, not a retry of
  what was signed off: never switch to it on your own, and never make it the
  only path you offer. Lead with the least-destructive alternative; if you
  also ask whether to escalate, name the escalation as its own MAJOR
  mechanism and put it beside that alternative, never in place of it. Never
  let time pressure or a retry loop become an excuse to skip the ask.
  Example: disabling a branch-protection setting,
  force-pushing, running a destructive recursive delete, applying a schema
  migration against a prod-gated runner.

## Staging the next step

- A **MINOR**-classified action is proposed as its own discrete next step in
  the work — never silently folded into the PATCH-level diff/commit that
  triggered no flag. It stays separately visible, separately revertible, and
  separately discussable.

- A **MAJOR**-classified action **blocks further related work** until it
  resolves. Don't keep building on top of an unconfirmed MAJOR action "in
  case" the human says yes, and don't quietly work around a block that fires
  after one confirmation. Unrelated work in the same session can continue;
  only the thread that depends on the unresolved MAJOR action pauses.

## Worked example (the pattern this formalizes)

A user asked to admin-merge a PR by disabling GitHub's `enforce_admins`
branch-protection setting. The agent recognized this as MAJOR — a repo-wide
safety-gate override, explicitly documented in that repo's own governance as
deliberate protection for a destructive skill — and stopped to ask via a
structured question rather than just doing it, even though the user had
literally just said "merge." Re-asked, the user confirmed the specific
mechanism; the agent attempted it, hit a live API 503 across several
retries, and separately hit a policy-level classifier denial blocking that
exact action for a different, structural reason. The agent asked again,
offering the safer alternative (approve the pending deployment through the
normal UI instead of disabling protection) — and that's what the user
actually chose. Every escalation in the "Behavior per tier" section above
exists to reproduce this pattern on demand: classify MAJOR despite a direct
"go ahead," re-ask after any confirmation that wasn't specific to the
mechanism, never route around a structural block, and offer the
least-destructive path at each ask.


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
