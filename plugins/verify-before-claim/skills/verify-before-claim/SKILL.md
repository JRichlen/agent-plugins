---
name: verify-before-claim
description: >-
  Always-on discipline that runs inline, in the main thread, before writing
  any sentence that asserts a fact, completion, or reproduction. Name the
  specific check that would prove the claim false, run it directly this turn,
  and attach its literal output next to the claim — never assert something as
  settled that wasn't checked, and never let a flagged uncertainty smooth into
  confident prose a few lines later. Use whenever you are about to write
  "done", "fixed", "passes", "confirmed", "verified", "reproduced", or any
  sentence that states a fact about the codebase or the world.
license: MIT
compatibility: >-
  PORTABILITY: pure conversational and procedural discipline — no subagent-
  spawning tool, no Workflow tool, no hooks, no harness-specific primitive
  required. It runs in the same turn, by the same agent, using whatever
  direct-inspection tools the harness already offers (run a command, read a
  file, fetch a URL, run a test). Ports to any harness that can execute a
  command and read its own output before writing a sentence.
---

# verify-before-claim

## Invariant

A claim of fact, completion, or reproduction must ALWAYS be backed by the specific check that would prove it false, performed directly — and NEVER asserted as settled when that check wasn't run; residual uncertainty must ALWAYS be flagged explicitly, never smoothed into confident-sounding prose.

## Not this

Two plugins in this marketplace look adjacent. Neither is this skill:

- **second-opinion** (`plugins/voice/skills/second-opinion`) is *post-hoc and
  offer-only*: it re-checks a verdict that **already exists**, only runs when
  the user asks or accepts an offer, and is gated on a subagent-spawning tool
  being available — it must decline rather than simulate if one isn't. It
  batches fact-checking plus scoped advisor personas, then re-emits the
  response in a mandatory grouped Verified/Flagged/Conflict format with a `Δ
  Validation` delta line, and that output shape is forbidden unless the
  dispatched work actually ran and returned.

  `verify-before-claim` never waits to be asked and never gates on a subagent
  tool. It is a default, continuous discipline that runs inline in the main
  thread every time the agent itself is about to write a claim, using direct
  checks — run the command, read the file, fetch the page — rather than
  dispatching subagent fact-checkers. It has no grouped output format to
  counterfeit; the "proof" it requires is the check's literal output sitting
  next to the claim, not a re-emitted verdict block. second-opinion audits a
  verdict after the fact, on request, via subagents; verify-before-claim stops
  the original claim from ever being written unverified, unprompted, by the
  same agent making it, in real time.

- **orchestrate** (`plugins/orchestrate/skills/orchestrate`) is a multi-agent
  Workflow-tool *template*: two JS workflow scripts that fan research out
  across `parallel()`/`pipeline()` subagents and adversarially verify the
  claims that surface, with frozen-context injection and per-stage JSON
  schemas as the load-bearing mechanics. It is infrastructure for
  orchestrating *other agents'* claims across a fan-out.

  `verify-before-claim` has no Workflow tool, no fan-out, no JSON schema
  contracts between stages — it governs a single agent's own claims about its
  own work, in ordinary conversation or task execution, not a scripted
  multi-agent pipeline. Where orchestrate answers "how do I keep a fleet of
  research subagents honest," verify-before-claim answers "how do I keep
  myself, right now, from asserting something I didn't check."

Worth a passing note on **tracer-bullets**: it shares the vocabulary of "real,
not fake" (a tracer bullet must be a real end-to-end slice, not a mock), but it
governs *scoping and build-order decisions* — what to build first, what to
keep versus discard — not claim-making. It never overlaps with this skill's
territory of "don't assert what you haven't checked."

## When to use this

Trigger before writing any sentence in this turn that asserts one of:

- **a fact** about the world or the codebase — "the file contains X", "the API
  returns Y", "this matches the spec"
- **completion** — "done", "fixed", "passes", "the merge is clean",
  "implemented"
- **reproduction** — "I reproduced the bug", "confirmed", "verified"

This is not a skill you invoke once at the start of a task. It fires every
time, inline, for every claim — that repetition is the whole point.

## The core procedure — every claim, every time

Before writing the claim:

1. **Name the single observation that would prove it false** — out loud, in
   your own reasoning, not implicitly. Ask yourself: "if this were false, what
   would I see?" A named check is concrete: a command, a file read, a fetched
   URL, a diff, a test run. It is never a feeling.
2. **Run that exact check directly, in this turn.** Not inferred from a
   similar case, not delegated to a status field someone else set, not
   assumed from adjacent evidence.
3. **Only after the check has actually run, write the claim** — and attach the
   check's literal output next to it: the command and its result, the quoted
   file content, or the test run's pass/fail line. Not a paraphrase of what
   you expected the output to be.
4. **If the check could not be run** — no access, no time, ambiguous target,
   tool unavailable — the claim must NOT be asserted as settled. Say so
   explicitly, adjacent to the claim: "not verified: X" or "assumed,
   unchecked: X" — never buried in a caveats section at the end, never
   omitted.
5. **Name residual uncertainty in the same sentence or the next one** —
   partial coverage, an untouched edge case, a flaky result, a check that only
   covers part of the claim. A claim's confidence level must not decay to
   "settled fact" as the response goes on.

**"Done" is legwork, not a status update.** A ticket, task, or claim is not
done because a field changed, or because it should be true given the plan —
it is done because the specific verifying action was performed in this turn
and its output is shown.

## Which reference loads when

The core procedure above is always active and needs no reference load — it is
the one thing every single claim requires, so splitting it into a reference
would force a load on every claim, which defeats progressive disclosure. The
four references below are genuinely separable sub-procedures: each fires only
when its trigger condition is met, and they are not mutually exclusive — a
research task that also produces a handoff doc loads both
`primary-source-research.md` and `uncertainty-flagging.md`.

| Situation | Load |
|---|---|
| Claim is about a bug report being real/reproducible, or a PR/merge being "ready to build on" | `references/pre-claim-reproduction.md` |
| The claim is going into a handoff doc, questionnaire response, or any deliverable someone else will act on without re-checking it | `references/uncertainty-flagging.md` |
| The claim cites an external source, or the task is "research X" / "find out whether Y" and produce findings | `references/primary-source-research.md` |
| Uncertain what a skill, plugin, tool, or command actually does, before describing or relying on its behavior | `references/skill-behavior-verification.md` |
| None of the above — an in-the-moment claim during ordinary work | Core procedure only, no reference load |

<!-- ANTI-PATTERN-LIST-START -->
## Anti-patterns — named here, never used unflagged anywhere else in this file

These phrases are smells, not moods. Each is a specific, checkable substitute
for the check this skill requires — none of them is a check.

- `should work` — a prediction standing in for a run result.
- `this looks correct` — an impression standing in for a check's output.
- `presumably` — an inference standing in for direct observation.
- `I'm confident this is right` used with no check cited next to it — a
  feeling standing in for evidence.
- bare `verified` with no command or output shown next to it — the word doing
  the work the check was supposed to do.
- a caveat placed only in a final "Note:" line after confident prose has
  already asserted the claim as settled — smoothing residual uncertainty out
  of the sentence where it belonged.

`be careful` is deliberately not on this list — it isn't a check, it's a
mood, and this skill only bans substitutes for checks.
<!-- ANTI-PATTERN-LIST-END -->
