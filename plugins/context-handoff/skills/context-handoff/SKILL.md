---
name: context-handoff
description: >-
  Walk the ordered continue, clear, handoff, delegate, compact decision tree at a phase boundary, and keep any handoff artifact pointer-only — settled specs, plans, ADRs, issues, commits, and diffs referenced by path or URL, never copied inline. Use this when the context window is getting full, you're wondering whether to clear or compact, you need to hand off to another harness, directory, or colleague, you've hit a phase boundary and aren't sure whether to keep going or start fresh, or you want to cache hard-won research before it's lost.
---

# context-handoff

## Invariant

At every phase boundary, the continue / clear / handoff / delegate / compact choice must ALWAYS be reached by walking the one ordered decision tree top-to-bottom — continue, then clear, then handoff, then delegate, then compact, first match wins — never guessed ad hoc, never invoked mid-phase (mid-phase there is nothing to decide: continue, or split remaining work into a subagent), and never jumped to out of order. Anything that crosses a handoff boundary (specs, plans, ADRs, issues, commits, diffs) must ALWAYS be referenced by path or URL, NEVER copied or quoted inline into the handoff artifact, so the receiving session reads the live source instead of a copy that can drift from it.

## Not this

- **Not `orchestrate`.** orchestrate answers a strictly later, narrower
  question: given that you're about to fan out subagents on a research-and-
  verify job, how do you structure that fan-out so plausible-but-wrong
  findings don't survive (frozen ground-truth context, per-stage schemas,
  adversarial disbelief-by-default verifiers). context-handoff answers a
  prior, more general question: am I at a phase boundary right now, and if
  so, should I even continue / clear / hand off / delegate / compact — fully
  independent of whether the eventual shape is a multi-agent fan-out at all.
  The two touch at exactly one point: if this skill's tree routes to DELEGATE
  and the delegated work happens to be a research-and-verify fan-out, reach
  for orchestrate's templates to shape it. context-handoff never prescribes
  fan-out internals; orchestrate never asks whether a fan-out should start.
- **Not `dev-diary`.** dev-diary produces a human-readable, first-person,
  past-tense journal entry summarizing a whole day's work, written for the
  user's future self to skim days later — narrative synthesis and judgment
  are the point, and it deliberately paraphrases rather than pointing at raw
  sources. A context-handoff handoff artifact is the opposite shape on every
  axis that matters: machine/agent-facing, present-tense, written mid-task at
  a phase boundary (not end-of-day), meant to let another session or agent
  resume live execution. The test: if this file is for a human to read days
  later, use dev-diary; if it's for the next session/agent to resume
  execution from, use context-handoff's handoff branch.

## When the tree applies

The tree is consulted ONLY at a phase boundary — the previous phase's output
is settled (committed, consumed by whatever needed it, or otherwise done) and
the next phase has not yet started. This is a literal, checkable gate, not a
mood.

**Boundary check:** "Is there a just-finished unit of work behind me and a
not-yet-started one ahead, right now?" If NO — still mid-phase — STOP, do not
run the tree. Mid-phase there are only two implicit moves: keep going, or
split the *remaining* work into a subagent while you keep going. Those are
not tree outcomes; they require no decision procedure.

If YES, walk the tree below, top to bottom, and stop at the first branch
whose check passes. This ordering is itself part of the invariant — never
jump straight to a later branch because it "feels right"; the earlier
branches are cheaper/safer and must be ruled out first.

PORTABILITY: "subagent" and "the harness's fan-out primitive" below name
Claude Code's Task tool / Workflow tool as the concrete example. The
discipline — decide IF delegation is warranted before deciding HOW — is
harness-agnostic; on another harness, re-implement DELEGATE with whatever
that harness's equivalent unattended-fan-out primitive is.

## The ordered decision tree

### 1. CONTINUE

**Check:** Does the next phase need this session's context essentially
as-is (recent tool outputs, working-file state, conversational nuance), AND
is the context window still comfortably below the point where quality
degrades — the "smart zone," not just "still fits under the hard cap"?

If both hold → stay in the same session. No artifact produced. This is the
ONLY branch that keeps the session itself as the primary source — nothing is
compressed, summarized, or exported.

### 2. CLEAR

**Check:** Is everything produced/consumed so far positively confirmed
disposable — no downstream phase, no other agent, no future session, no
future-you needs any of it?

If yes → clear. Cheapest branch on the tree, but ONE-WAY: you must be able to
answer "yes, disposable" affirmatively, not merely fail to think of a use for
it. Absence of an obvious need is not the same as confirmed disposability —
when unsure, this branch does not match; move to the next.

### 3. HANDOFF

**Check:** Does something concrete have to physically TRAVEL — to a
different harness (e.g. Claude Code → Codex), a different directory/repo/
worktree, a different person (colleague), or a forked side-task that
proceeds in parallel while the current session continues on the main thread?

If yes → write a portable handoff artifact. Load
[`references/portable-extraction.md`](references/portable-extraction.md) now
for the exact shape and the drift/resolvability/size checks. This branch is
the most commonly mis-reached-for: never use it just because you want to
summarize progress. Reaching HANDOFF requires naming which concrete thing is
crossing which concrete boundary (harness / directory / person / parallel
fork) — if you can't name it, this branch does not match.
Before a handoff artifact travels off-machine, run `evals/cheap/secret-gate.sh`
(in the marketplace repo) over the draft — a mechanical scan for pasted secrets.

### 4. DELEGATE (subagent)

**Check:** Is the remaining work scoped tightly enough to run unattended —
bounded enough that the delegate won't need you mid-execution?

If yes → delegate via the harness's fan-out primitive (Task tool / Workflow
tool / equivalent). If the delegated work is itself a multi-agent
research-and-verify fan-out, reach for the `orchestrate` plugin's templates
to shape it — context-handoff decides IF/whether to delegate, orchestrate
governs HOW a research fan-out runs once delegation is chosen. Do not inline
fan-out mechanics here.

### 5. COMPACT (default)

If none of 1–4 matched → compact. Compress the context and keep going in a
fresh window: intent survives even though verbatim history doesn't. This is
the ordinary default, not a last resort — most phase boundaries land here.
Landing here is not a failure to find a "better" branch; it's what happens
when nothing is disposable, nothing has to travel, and nothing is bounded
enough to delegate.

## Research check (independent trigger)

Run this regardless of which of the 5 branches the tree selects (except
CONTINUE, where nothing is being lost): "Did this phase produce findings
that were expensive to (re)derive — an external API's undocumented
behavior, an uncommon vendor integration, exploration that took real
digging?"

If yes, and it is not already captured in-repo, load
[`references/research-documenter.md`](references/research-documenter.md)
and write/update `research.md` BEFORE executing the chosen branch —
clear/handoff/delegate/compact all risk losing un-cached findings to a
fresh context window. `research.md` is a temporary, sprint/feature-scoped
artifact, not a permanent doc — note in it when it's safe to delete (e.g.
"delete once feature X ships" / "superseded by ADR-NNN").

## Reference files

| File | Loads when | Contains |
|---|---|---|
| [`references/portable-extraction.md`](references/portable-extraction.md) | Tree resolves to HANDOFF | The pointer-only rule, drift check, handoff-file shape, resolvability check, deterministic quoted-block size check |
| [`references/research-documenter.md`](references/research-documenter.md) | Independent research trigger above, any branch except CONTINUE | When/what/lifecycle for `research.md`, and how a handoff file must reference it by path rather than re-embed it |
