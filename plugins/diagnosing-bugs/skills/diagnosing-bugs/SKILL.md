---
name: diagnosing-bugs
description: >-
  Diagnose a bug by writing ranked, falsifiable hypotheses before any code
  change, tagging temporary debug instrumentation for a zero-tolerance sweep,
  and gating the regression test to a red-then-green proof at the confirmed
  seam. Use when fixing a bug, debugging a failure, triaging an error, or the
  user asks to diagnose/root-cause/troubleshoot an issue.
---

# diagnosing-bugs

## Invariant

A bug fix must never begin with a code change: a ranked, falsifiable
hypothesis list — each entry stating its claim, its supporting evidence, and
the specific observation that would prove it false — must be written down
before any diagnostic or fix code is written. Any temporary debug
instrumentation added while testing those hypotheses must always carry one
fixed, consistent, grep-able tag and must NEVER ship untagged or unswept — a
`grep -rn 'DBGRM:' <scope>` sweep over the touched scope must return zero
lines before the fix is considered done. A fix must never land without a
regression test gated to the actual seam that broke, proven by a
red-on-pre-fix / green-on-post-fix check — not a coincidental higher-level
assertion that happens to pass.

Everything else in this procedure — the specific ranking heuristics, the
minimization tactics, how the feedback loop gets tightened — is allowed to be
approximate and adapted to the bug at hand.

These three checkpoints are never allowed to soften: **hypothesis-before-code**,
**tag-before-ship**, **seam-gated-test**.

Write this first, before any workflow prose. The invariant is what the cheap
eval defends; everything below exists to keep it true.

## Where this comes from

The applied write-up this skill is sourced from is Matt Pocock's "How I
Diagnose Bugs" (aihero.dev, `/skills-diagnosing-bugs`) — the same corpus
`tracer-bullets` and its siblings in this marketplace were harvested from.
This skill is the applied, disciplined restatement of "guess and check" as an
actual procedure with falsifiability and auditability built in, rather than a
vibe.

## When to use this

- Any time a bug is confirmed to exist and the next step is figuring out
  *why*, before writing a fix.
- Debugging a failure, triaging an error report, root-causing a flaky test,
  or investigating a regression.
- The moment the temptation is "let me just try changing this and see if it
  helps" — that is exactly the moment this skill exists to interrupt.
- Not for the moment a bug is first noticed or reported (that's triage/intake)
  and not for designing new work from scratch (see `tracer-bullets` for
  scoping unbuilt work) — this skill starts once a repro is in hand and a fix
  is the goal.

## The procedure

Seven sequential steps, one source procedure. Every invocation needs all of
them, in order — none is independently optional.

### Step 0 — Tight feedback loop (prerequisite, not optional)

Before hypothesizing, confirm a fast, deterministic, sharp-signal repro
exists: one command or test that reproduces the bug and reports pass/fail in
seconds, with no flakiness.

**Concrete check:** can you run the repro twice in a row and get the same
verdict in under ~10 seconds? If not, tighten the loop first — isolate the
failing unit, stub slow externals, pin the failing input. If no such repro
exists, building it *is* the first task. Do not proceed to Step 1 on a
slow, manual, or flaky loop: every hypothesis test in the steps that follow
inherits that loop's cost and noise, and a noisy loop makes falsification
itself unreliable.

### Step 1 — Ranked, falsifiable hypotheses, written BEFORE any code change

Before touching code — fix code *or* diagnostic code — write a numbered list.
Each entry has three required parts:

1. **Claim** — the specific mechanism believed broken. Not "something's wrong
   with auth," but "the token refresh fires before the old token is revoked,
   so both are briefly valid."
2. **Evidence so far** — what's already been observed that makes this
   plausible.
3. **Falsifying test** — the exact, cheap observation that would prove this
   claim FALSE. If you cannot state one, it is not a hypothesis — it is a
   vibe, and it does not go on the list.

Order the list by likelihood given the evidence (Occam's razor: prefer the
explanation that covers all observed symptoms with the fewest assumptions);
when two entries are close in likelihood, promote whichever is cheaper to
falsify.

"I'll just try this and see" is never a valid Step 1. If code changed before
this list existed, the list was skipped, not satisfied.

### Step 2 — Test the top-ranked hypothesis using the tight loop

Run the falsifying test from the top of the ranked list. If it needs internal
visibility the loop doesn't already give you, add temporary debug
instrumentation (log/print/assert) — see the tagging rule in Step 6, applied
without exception, even for a single throwaway `console.log`.

### Step 3 — Falsify or confirm, then move

- **Falsified** → cross it off with the observed evidence, move to the next
  ranked entry. Re-rank if the failed test surfaced new evidence — don't just
  fall through the original order blindly.
- **Confirmed** → proceed to Step 4.

Do not silently keep guessing outside the list. Every additional guess gets
appended to the ranked list, with its own falsifying test, before it's tried.

### Step 4 — Minimize to the load-bearing case

Once the mechanism is confirmed, strip the repro to the smallest input,
state, or code path that still reproduces it. For each element — input
field, config flag, code path, fixture — ask "does removing this still
reproduce the bug?" Keep removing while the answer is yes. Stop when the
remaining set is minimal.

That minimal set is both the sharpest possible feedback loop and the precise
seam the fix and regression test in Step 5 must target.

### Step 5 — Fix at the confirmed seam, then gate the regression test to it

Implement the fix. The regression test must exercise the exact boundary
identified in Step 4 — not a coincidental higher-level test that happens to
pass through that code path.

**Deterministic proof it's gated correctly:** check out the pre-fix state
(stash the fix, or diff against the parent commit) and confirm the new test
goes **RED**; reapply the fix and confirm it goes **GREEN**. A test that
passes even without the fix is not gated to the real seam — go back to Step
4, the minimization wasn't tight enough. Skipping this red/green bracket is
skipping the gate, not satisfying it loosely.

### Step 6 — Zero-tolerance instrumentation sweep before shipping

Any code added purely to *observe* behavior during Steps 0–4 (not part of the
eventual fix) must be tagged with a single, fixed, greppable marker. The
default literal tag is **`DBGRM:`** (debug — remove), used as a
comment/log-message prefix regardless of language:

- `// DBGRM: ...`
- `# DBGRM: ...`
- `console.log('DBGRM:', ...)`
- `print(f"DBGRM: {x}")`

Before the fix is considered done, run:

```
grep -rn 'DBGRM:' <scope>
```

over the touched scope. It **MUST return zero lines.** Anything still tagged
is either deleted, or — in the rare case it's genuinely worth keeping as
permanent observability — deliberately un-tagged and justified in the commit
message. Never leave it tagged-and-shipped: a tagged-and-shipped instance
means the sweep wasn't actually run.

### Step 7 — Auditability

The ranked hypothesis list from Step 1, with which entries were falsified or
confirmed and why, should be visible in the artifact that survives the task —
PR description, commit message, or chat output. The point of ranking
*before* testing is that someone else can audit the reasoning path
afterward, not just trust the final diff.

## Decision points, stated as concrete checks

Not "be careful" — a concrete check for each judgment call:

- **Loop tight enough?** → two consecutive runs, same verdict, under ~10
  seconds. If not, fix the loop before Step 1.
- **Is this actually a hypothesis?** → can you name the observation that
  would prove it false? If not, it doesn't go on the list.
- **Does this debug line need the `DBGRM:` tag?** → yes, always, no
  exceptions, if its only purpose is diagnostic observation.
- **Is the regression test gated correctly?** → red on pre-fix checkout,
  green on post-fix. Skipping this bracket is skipping the gate, not
  satisfying it loosely.

## Am I done?

All four, not a subset:

1. A ranked hypothesis record exists and is visible (Step 1 + Step 7).
2. `grep -rn 'DBGRM:' <scope>` returns zero lines (Step 6).
3. A regression test exists, gated to the Step 4 seam, verified red-then-green
   (Step 5).
4. The fix actually resolves the original tight-loop repro from Step 0.
