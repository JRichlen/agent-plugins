# Research documenter

Loads on its own independent trigger — the "Research check" in
[`SKILL.md`](../SKILL.md) — regardless of which of the 5 decision-tree
branches gets chosen (it applies to CLEAR, HANDOFF, DELEGATE, and COMPACT
alike; only CONTINUE skips it, since nothing is being lost when the session
stays live).

## When to create or update `research.md`

Trigger: this phase produced findings that were expensive to (re)derive —
an external API's undocumented behavior, an uncommon vendor integration's
quirks, exploration that took real digging to nail down — and that
knowledge is not already captured anywhere in-repo (a comment, an ADR, a
doc). If a fresh context window would have to redo that digging from
scratch, write it down before the window changes.

## Location

`research.md`, in-repo, at the root of the work it concerns (typically the
repo root or the feature's own directory) — NOT inside the handoff file, and
NOT in a private journal like dev-diary's. The point of an in-repo file is
that any fresh context window can reach it without special access: this
session's own post-compact/clear window, a future session picking the repo
back up, or a delegated subagent that was never told the story directly.

PORTABILITY: "subagent" above names Claude Code's Task tool / Workflow tool
as the concrete example of a fresh context window that can't be told the
story directly. The reasoning is harness-agnostic — any harness's equivalent
unattended-fan-out primitive has the same problem and the same fix.

## Contents

- **Prerequisites** — what you needed to know before any of this made sense
  (auth quirks, required flags, ordering constraints).
- **Findings** — what you learned, what's actually true about the external
  system, including the dead ends that are worth not re-walking.

`research.md` does NOT carry:

- The **live thread** — what's in flight right now and what's next. That is
  the handoff file's job, if a handoff file exists for this work at all.
  `research.md` is settled knowledge; the handoff file is live state.
- Narrative synthesis for a human reader days later — that's dev-diary's
  job, on its own timescale, in its own repo.

## Lifecycle

`research.md` is explicitly **temporary**, scoped to the current
sprint/feature — it is not a permanent doc and should not accumulate
indefinitely. Write a one-line staleness note at the very top stating when
it's safe to delete, for example:

```
<!-- research.md — safe to delete once feature X ships, or once superseded
     by ADR-NNN. Written 2026-08-16 during the context-handoff phase
     boundary at commit abc1234. -->
```

An undated `research.md` left in a repo indefinitely, with no one able to
tell whether it's still true, is the exact failure mode this staleness note
exists to prevent. When the condition in the note is met, delete the file —
don't let it silently outlive its usefulness.

## Referenced by the handoff file, never re-embedded

If a handoff file is also being written for this same work (decision tree
branch 3, HANDOFF), it must reference `research.md` by path — never copy its
contents in. This is
[`portable-extraction.md`](portable-extraction.md)'s pointer-only rule
applied recursively: `research.md` is itself a settled artifact the moment
it's written, so treat it exactly like a spec, plan, ADR, issue, commit, or
diff — point at it, don't paste it.
