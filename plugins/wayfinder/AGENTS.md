# AGENTS.md — wayfinder

Chart a multi-session effort as a labeled map of typed decision tickets (grilling / prototype / research / task) with explicit dependencies and an open frontier agents self-assign into. Plans; never executes.

## How to use it

Read `skills/wayfinder/SKILL.md` and follow it — it is the authoritative
description of this plugin's workflow and the invariant it defends. It leads
with the Invariant, then a "Not this" section distinguishing wayfinder from
`orchestrate` and `grill-me` (adjacent-looking plugins in this same
marketplace), then the charting procedure (steps 0-5) with pointers into
three reference files:

- `skills/wayfinder/references/ticket-taxonomy.md` — the four ticket types
  and the type-lock rule.
- `skills/wayfinder/references/task-breakdown.md` — the dependency DAG, the
  cycle check, and the frontier definition.
- `skills/wayfinder/references/fog-of-war.md` — the known-unknown / decided /
  out-of-scope trichotomy and its one-sentence-question test.

The command `commands/wayfinder.md` is the entry point a user invokes.

## The invariant this plugin defends

A multi-session effort must ALWAYS be represented as a labeled map of typed decision tickets with dependencies made explicit before any ticket is dispatched; planning tickets must NEVER be conflated with or silently converted into execution tickets — a ticket whose true scope turns out to require changing real system state MUST close as resolved-into-a-new-linked-task-ticket, never be relabeled in place; and only the non-blocking frontier — every ticket that is itself still OPEN and whose own listed dependencies are ALL CLOSED (an empty dependency list counts as trivially all-closed), computed fresh each time, never cached — may be dispatched in parallel; NEVER a ticket with an open dependency, and never a ticket excluded just because it itself has not yet closed — a ticket's own not-yet-closed status is what makes it eligible, not what disqualifies it.

The deterministic checks that defend it live in `evals/cheap/checks.sh` and run
as part of the marketplace cheap tier.
