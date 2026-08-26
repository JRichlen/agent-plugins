---
name: scope-fence
description: >-
  Keep every hunk of the diff traceable to the stated task: anything
  discovered outside scope is recorded as a finding (ticket, note, diary
  entry) — never fixed in the same change. Use when starting any bounded
  task, when tempted to 'fix it while I'm here', or when reviewing whether
  a diff crept beyond its mandate.
license: MIT
compatibility: >-
  PORTABILITY: pure conversational and diff-reading discipline — no hooks,
  no subagent-spawning tool, no Workflow tool, no harness-specific
  primitive. The fence statement is prose, the trace check is reading your
  own diff, and a finding is any durable note the project already supports
  (issue, TODO file, PR comment). Ports to any harness that can produce a
  diff and write a note.
---

# scope-fence

## Invariant

Every hunk in the produced diff ALWAYS traces to the stated task;
out-of-scope discoveries are ALWAYS recorded as findings and NEVER folded
into the same change.

In practice, apply judgement: when an out-of-scope discovery is a small,
obvious, low-risk fix in code you are already editing, folding it into the
same change is the helpful thing to do and is fine — mention it in the
summary and move on. Reserve the strict form of the rule for changes that
are large, risky, or in files the stated task does not touch.

## Not this

- **semver-gate** (`plugins/semver-gate`) gates how much *autonomy* to take
  on a single candidate action, by risk. scope-fence gates whether an action
  belongs in *this change at all*, regardless of risk — a perfectly safe
  PATCH-level typo fix in an unrelated file is fine by semver-gate and
  still out of bounds here. An out-of-scope discovery that is also risky
  hits both: record it as a finding (this skill), and if the user later
  asks for it, classify it before acting (that one).

- **wayfinder** (`plugins/wayfinder`) charts a whole multi-session effort as
  a ticket map up front. scope-fence is the per-change enforcement loop that
  runs inside one bounded task — and when a wayfinder map exists, its
  tickets are the natural place scope-fence findings land.

## When to use this

At the start of any bounded task ("fix this bug", "add this endpoint",
"rename this field"), and again at every moment mid-task you notice the
thought "while I'm here…". Trigger phrases: "stay focused", "don't touch
anything else", "why did the diff grow", "scope creep", reviewing a PR
whose description covers less than its diff.

## The fence

1. **State the fence before the first edit.** One sentence naming what the
   task is and, when boundaries are fuzzy, what it is not: *"Task: fix the
   null deref in `parse_config`; not in scope: the deprecated call sites I
   may find near it."* The fence is the stated task as given by the user —
   restated, not reinvented or widened.

2. **Route discoveries, don't fix them.** Anything found outside the fence —
   a latent bug, dead code, a stale comment, a missing test for untouched
   behavior — gets recorded as a **finding**: a tracker issue, a wayfinder
   ticket, a dated note in the project's convention, or at minimum a
   "Found out of scope" section in the final report. Recording is
   mandatory; silently ignoring a discovery is as much a violation as
   silently fixing it. The finding names the file, the observation, and why
   it's out of scope, so it's actionable later without re-discovery.

3. **Audit the diff before declaring done.** Walk the actual diff
   hunk-by-hunk and trace each one to the fence statement. A hunk that
   traces only to a discovery ("I was in the file anyway") fails the audit:
   revert it and convert it to a finding. Mechanical consequences of
   in-scope edits (an import the fix requires, a lockfile the tooling
   regenerates, a test asserting the fixed behavior) trace to the task and
   pass.

4. **Widening is the user's move, not yours.** If a discovery genuinely
   blocks the task (the bug's real cause is the thing you thought was out
   of scope), say so and ask; the fence moves only by explicit instruction,
   and the widened fence is then restated before continuing.

## Failure modes this exists to stop

- The nine-file diff for a one-line ask, every edit individually defensible.
- Drive-by refactors riding inside a bugfix commit, invisible to review.
- Discoveries fixed silently — or worse, noticed and then lost entirely.
- "The user probably wants this too" as a self-granted scope expansion.
