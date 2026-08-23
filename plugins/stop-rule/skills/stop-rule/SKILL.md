---
name: stop-rule
description: >-
  A halting discipline for iterative fix loops: after a bounded number of
  failed attempts at the same objective, stop and report the state with
  hypotheses — never make attempt N+1 on momentum. Use when re-pushing to
  fix CI, retrying a flaky repro, or any loop where each retry is a guess
  rather than a diagnosis.
license: MIT
compatibility: >-
  PORTABILITY: pure loop-accounting discipline — no hooks, no
  subagent-spawning tool, no Workflow tool, no harness-specific primitive.
  The bound is a number declared in prose, the counter is honest
  bookkeeping, and the stop-report is a message. Ports to any harness
  where an agent can count its own attempts and write a report.
---

# stop-rule

## Invariant

Attempts at one objective are ALWAYS counted against a bound declared up
front, and hitting the bound ALWAYS produces a stop-and-report with current
state and ranked hypotheses — NEVER a further attempt on momentum.

## Not this

- **diagnosing-bugs** (`plugins/diagnosing-bugs`) governs *how* to work a
  bug: ranked falsifiable hypotheses before code changes. stop-rule governs
  *when the loop itself must halt* — and its stop-report deliberately hands
  off in diagnosing-bugs' vocabulary: the report's ranked hypotheses are
  the entry point for a disciplined diagnosis (or a fresh session) instead
  of attempt N+1. A loop run properly under diagnosing-bugs may still hit
  the bound; the bound still wins.

- **verify-before-claim** (`plugins/verify-before-claim`) checks claims
  before they're written. Its pressure-point overlap: attempt N+1 usually
  ships with the implicit claim "this one should do it." stop-rule removes
  the option of making that claim at all past the bound.

## When to use this

The moment work becomes a retry loop: pushing again to fix the same CI
failure, re-running a repro hoping it flakes the other way, adjusting a
prompt/config/flag and re-trying the same command, any sequence where the
change between attempts is a guess rather than the output of a diagnosis.
Trigger phrases: "still failing", "try again", "one more push", your own
third consecutive attempt at the same red check.

## The rule

1. **Declare the bound at attempt one** — the moment you notice an
   objective may take repeated attempts, state it: *"CI fix: bound is 3
   attempts."* Default bound: **3** for pushes and other externally visible
   attempts, **5** for purely local retries. Declaring it up front is what
   makes it a rule; a bound chosen while at the limit is a rationalization.

2. **Count honestly, per objective.** An attempt is any try at the same
   objective, however the mechanism varies — a different flag, a tweaked
   assertion, a reworded fix are all attempts at the same objective, not
   fresh objectives. Reframing the objective to reset the counter is the
   canonical cheat; a genuinely new objective comes with a diagnosis
   explaining why the old one was wrong.

3. **Diagnosis resets; momentum doesn't.** The counter resets only when a
   root cause was actually established (in diagnosing-bugs' sense: a
   confirmed, falsifiable explanation of the previous failures) — because
   then the next attempt is the *first* attempt at a new, understood
   problem. "I have a better feeling about this one" resets nothing.

4. **At the bound: stop and report.** No attempt N+1. The stop-report
   contains: the objective; what each attempt changed and what happened
   (literal failure output, not paraphrase); current state of the world
   (what's pushed, what's red, what's half-done); and ranked hypotheses
   with, for each, what evidence would confirm or kill it. Then hand
   control back — to the user, to a fresh diagnosis, or to a decision to
   abandon — rather than continuing.

## Failure modes this exists to stop

- Three speculative pushes for one CI failure, each a guess wearing a
  commit message.
- The counter quietly reset because the fourth attempt "is really a
  different approach."
- Burning the session's remaining budget on attempt seven instead of
  writing the report that would have let attempt one of a real diagnosis
  succeed.
- A stop that reports "it didn't work" with no state, no outputs, and no
  hypotheses — technically halted, uselessly so.
