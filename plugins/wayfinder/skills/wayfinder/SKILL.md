---
name: wayfinder
description: >-
  Chart a multi-session effort as a labeled map of typed decision tickets
  (grilling / prototype / research / task) with explicit dependencies and an
  open frontier agents self-assign into. Plans; never executes. Use this
  skill whenever the user is working with wayfinder, and on phrases like
  "chart this effort", "break this into tickets", "what's the frontier",
  "plan across sessions", or "map out the dependencies for this work".
license: MIT
---

# wayfinder

PORTABILITY: the ticket-store discipline (GitHub issue labels, or a local
frontmattered file store) and the DAG/frontier mechanics are pure prose and
data — no hooks, no Workflow tool, no harness-specific primitive of
wayfinder's own. The "Not this" section below names subagents and the
Workflow tool only to describe two other plugins that wayfinder can dispatch
to, not a dependency of this skill. The map and its checks port to any harness
that can write a comment and read a label or field.

## Invariant

A multi-session effort must ALWAYS be represented as a labeled map of typed decision tickets with dependencies made explicit before any ticket is dispatched; planning tickets must NEVER be conflated with or silently converted into execution tickets — a ticket whose true scope turns out to require changing real system state MUST close as resolved-into-a-new-linked-task-ticket, never be relabeled in place; and only the non-blocking frontier — every ticket that is itself still OPEN and whose own listed dependencies are ALL CLOSED (an empty dependency list counts as trivially all-closed), computed fresh each time, never cached — may be dispatched in parallel; NEVER a ticket with an open dependency, and never a ticket excluded just because it itself has not yet closed — a ticket's own not-yet-closed status is what makes it eligible, not what disqualifies it.

## Not this

Two plugins in this marketplace look adjacent. Neither is this skill:

- **orchestrate** (`plugins/orchestrate/skills/orchestrate`) is a
  Workflow-tool *template pair* (`derived-verify` /
  `pipelined-verdict-wins`) for a **single session's** research-and-verify
  fan-out. It has no persistent state across sessions: a template script
  runs once, returns `{research, verdicts}` or a reconciled brief, and is
  done. It has no concept of a ticket, a dependency graph, or a frontier that
  persists between invocations — every run starts from a caller-supplied
  `dimensions` list, not a chart built up over time.

  wayfinder is the opposite: durable, cross-session, ticket-typed state that
  orchestrate's fan-outs could later be *dispatched against* (a wayfinder
  `task` ticket on the frontier is a plausible orchestrate input) but
  wayfinder never itself fans out subagents or verifies claims — it only
  charts the map and gates dispatch order.

- **grill-me** (`plugins/grill-me/skills/grill-me`) is a single-session,
  no-subagents-required, **live interrogation of one plan, right now**,
  ending in a synthesized recap the user confirms before work starts. It has
  no ticket store, no persistence across sessions, and layers a stakes triage
  (reversibility x blast-radius) on top of its own frontier to size question
  *depth* within one session. Its "frontier" is a design-tree concept scoped
  to one interrogation session, not a multi-session dispatch queue with
  typed, independently-assignable tickets.

  wayfinder can legitimately spawn a grill-me session as the concrete work
  behind a `grilling`-type ticket — that's the natural composition point —
  but wayfinder itself never interrogates the user live. It records that a
  `grilling` ticket exists and is open, and moves on to charting the rest of
  the map.

The load-bearing distinction: orchestrate and grill-me are both
single-session and stateless across sessions (orchestrate = execute-and-verify
now; grill-me = interrogate-and-confirm now). wayfinder is the only one of the
three that persists a plan as inspectable state across many sessions, and
explicitly forbids that state from ever being silently treated as execution.

## When to use this

Trigger on "chart this effort", "break this into tickets", "what's the
frontier", "plan across sessions", "what can I work on right now", or
whenever a piece of work is too big for one session and needs a durable,
inspectable plan that multiple sessions (or multiple agents) will pick up
from over time. Not for a single session's own scratch todo list, and not as
a substitute for actually doing the work — wayfinder charts and gates; it
never executes.

## Modeled on homelab-board

This follows the `homelab-board` discipline (GitHub issue labels as the
only state, exactly one column label per issue, unlabeled is a real signal
not a default, `status:blocked` requires a stated blocker in a comment)
applied to planning tickets instead of ops tickets. The rule that discipline
exists to enforce, carried over verbatim: **a control that reports success
without doing the thing is the exact failure to avoid.** Any rendered view
wayfinder produces (a printed frontier list, a dependency diagram) is always
a throwaway query over the ticket store — it must write to the ticket store,
or it must not exist as a separate board.

## The procedure

### 0. Detect the ticket store

Before charting anything, resolve where tickets live for this effort:

- If a `gh`-backed repo is in scope and the user confirms GitHub issues are
  the store, tickets are GitHub issues; state is issue labels — exactly one
  status label per ticket, comment-stated blockers, mirroring
  `homelab-board`'s invariant exactly.
- Otherwise, tickets are a local Markdown/YAML ticket file (one file, or one
  dir of frontmattered files) under a `.wayfinder/` directory created in the
  repo root, with the same label semantics expressed as a `status:` field
  instead of a GitHub label. This is a fallback, not a second first-class
  design — same schema, different substrate.
- Never invent a third rendering (an HTML board, a dashboard) as the store.
  Per the homelab-board postmortem this skill quotes above, any rendered view
  is always a throwaway query, never itself the state.

### 1. Chart the effort into typed tickets

Read `references/ticket-taxonomy.md` before charting the first ticket. Break
the effort into tickets, each tagged with exactly one type — `grilling`,
`prototype`, `research`, or `task`. The type gates what "done" means and what
may ever be silently reclassified: a ticket's type is fixed at creation, and
a scope surprise closes it and spawns a new linked ticket of the correct type
(never a silent in-place relabel — see `ticket-taxonomy.md`'s type-lock
rule).

### 2. Build the dependency graph, don't just list tickets

Read `references/task-breakdown.md` before charting dependencies. For every
ticket, state its upstream dependencies explicitly as a list of ticket IDs —
an empty list is itself a claim ("this can start now"), not an omission. This
produces a DAG, not a flat backlog, and it's checked two mechanical ways:

- **Cycle check**: if resolving dependencies ever revisits a ticket already
  on the current resolution path, that's a cycle — stop and force the user
  to break it (split a ticket, or demote one edge to "informs") before
  charting proceeds.
- **Frontier definition**: a ticket qualifies for the frontier only when
  BOTH of the following hold — and each condition is checked against a
  different ticket, so never let one leak onto the other's target:
  1. **This ticket itself is still OPEN.** A ticket that has already closed
     is done, not dispatchable, and can never re-enter the frontier.
  2. **Every ticket THIS ticket depends on is CLOSED.** That CLOSED test
     applies only to the tickets in its own dependency list — never to the
     ticket itself. An empty dependency list has nothing to check, so
     condition 2 is trivially satisfied.
  A ticket with an empty dependency list is therefore trivially on the
  frontier the instant it is open — no matter how close the ticket itself
  looks to being done ("the PR is up," "it's waiting on one approval," "it'll
  merge within the hour" all still mean OPEN, not CLOSED). Do not apply
  condition 2 to the ticket being evaluated — that is the exact mistake to
  avoid: a ticket is excluded from the frontier only because something IT
  depends on is still open, never because the ticket itself hasn't closed.
  Computed fresh each time — never a cached "on frontier" flag.

### 3. Mark unknowns explicitly — the fog-of-war check

Read `references/fog-of-war.md` at ticket-creation time, and again whenever a
ticket's scope starts to feel fuzzy. The test: **can you state the open
question this ticket exists to answer, as one sentence with a question mark,
right now?**

- Yes → genuine known-unknown; type it `research` or `grilling`, and write
  that sentence as the ticket's done-condition.
- No → not yet chartable; it must first go through a `grilling` ticket whose
  sole job is to produce the precise question. Never chart a vague
  downstream ticket and hope it resolves itself later.
- Neither decided nor an open question → explicitly out of scope; write it
  as a labeled out-of-scope note attached to the map, never silently dropped
  or silently folded into an adjacent ticket.

### 4. Dispatch — frontier only, in parallel

wayfinder's own output stops at the labeled map with a computed frontier. It
hands off dispatch — to the user, to `orchestrate`, or to plain parallel
agent calls — under one stated rule: only tickets currently on the frontier
may be dispatched concurrently, and a ticket must never be dispatched while
any of its listed dependencies is still open. This is checked the same
mechanical way as the frontier computation itself (see
`references/task-breakdown.md`) — not a vibe check.

### 5. Update the map as sessions land

Each session that closes a ticket:

1. Close it in the ticket store (issue close, or `status:` field update).
2. Recompute the frontier — which tickets just became newly unblocked.
3. If the closing session surfaced new sub-decisions, chart them as new
   tickets with dependencies back to the just-closed one, going through
   steps 1 and 3 again for each new ticket.

The map is never re-planned from scratch — it's incrementally extended, the
same way homelab-board issues are never bulk-recreated, only
relabeled/closed/commented.

## Every judgment call resolves to a named, restatable check

None of the above is a vibe check. Each one is defined once, where it's used
(steps 0-3 above), and worked with examples in the reference file that owns
it:

- Type conflation → the type-lock rule (`references/ticket-taxonomy.md`).
- Frontier membership → the frontier definition (`references/task-breakdown.md`).
- Cycles → the path-revisit cycle check (`references/task-breakdown.md`).
- Known-unknown vs. not-yet-chartable → the fog-of-war test (`references/fog-of-war.md`).
- Board-vs-reality drift → the control-must-write-to-the-store rule (above,
  under "Modeled on homelab-board").
