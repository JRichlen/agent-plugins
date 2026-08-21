---
description: >-
  Chart a multi-session effort as a labeled map of typed decision tickets
  (grilling / prototype / research / task) with explicit dependencies and an
  open frontier agents self-assign into. Plans; never executes. Use on
  "chart this effort", "break this into tickets", "what's the frontier", or
  "plan across sessions".
---

Invoke the `wayfinder` skill and follow `skills/wayfinder/SKILL.md`.

First detect the ticket store (GitHub issues via `gh` if a repo is in scope
and confirmed, otherwise a local `.wayfinder/` directory) — step 0 of the
procedure. Then chart the effort into typed tickets per
`skills/wayfinder/references/ticket-taxonomy.md`, build the explicit
dependency DAG per `skills/wayfinder/references/task-breakdown.md` (running
the cycle check before charting is considered done), and run the
one-sentence-question fog-of-war test from
`skills/wayfinder/references/fog-of-war.md` on every ticket whose scope feels
fuzzy. Report the computed frontier — every open ticket whose dependencies
are all CLOSED — and stop there: wayfinder hands dispatch off to the user, to
`orchestrate`, or to plain parallel agent calls, and never executes the
charted work itself.
