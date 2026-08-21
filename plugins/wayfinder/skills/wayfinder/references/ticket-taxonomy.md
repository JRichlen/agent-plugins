# Ticket taxonomy

Every ticket on a wayfinder map carries **exactly one type**, chosen from this
list of four. The type is load-bearing: it gates what "done" means for the
ticket, and it gates what may ever be silently reclassified. A ticket's type
is fixed at creation — see "The type-lock rule" below.

## The four types

### `grilling`

An open design/interrogation question that must be resolved before downstream
tickets can be typed at all. Its done-condition is a decision recorded
somewhere durable (a comment, a linked doc) — not a changed system, not a
finding, a **decision**.

Often this literally means "run `grill-me` on this branch of the plan and
record what it converges on." wayfinder doesn't run the interrogation itself
(see SKILL.md's "Not this" section) — it records that a `grilling` ticket
exists, that it's open, and moves on to charting the rest of the map.

**Worked example:** "Decide whether the ticket store fallback lives under
`.wayfinder/` or `.tickets/`." Done when: a comment states the chosen
directory name and why.

### `prototype`

A throwaway spike whose only output is an answer to one stated unknown — not
shippable code. The code a prototype ticket produces is disposable by
definition; if it's good enough to keep, that's a **task** ticket's job to
formalize it (see the type-lock rule), not the prototype ticket's job to ship
it in place.

**Worked example:** "Spike whether `gh issue list --json` returns labels fast
enough for a 500-issue repo to make live frontier computation viable." Done
when: a comment states the observed latency and a yes/no on viability.

### `research`

A fact-finding ticket whose done-condition is a **stated finding**, not a
changed system. Research tickets exist to convert an open question into a
recorded fact other tickets can depend on.

**Worked example:** "Find out whether the target repo already has a
`status:*` label taxonomy from another tool that would collide with
wayfinder's." Done when: a comment lists the existing labels found (or states
none exist).

### `task`

An execution ticket: it changes real system state — code, infra, config, a
merged PR. This is the only type whose done-condition is "the system is now
different," and it is the only type that may ever be dispatched to do work
that isn't itself planning.

**Worked example:** "Implement the `.wayfinder/` fallback directory creation
in the detect-store step." Done when: the change is merged.

## What "done" means, per type

| Type | Done when |
|---|---|
| `grilling` | A decision is recorded (comment/linked doc) |
| `prototype` | A stated answer to the named unknown is recorded |
| `research` | A stated finding is recorded |
| `task` | Real system state has changed (merged, deployed, applied) |

None of these four done-conditions is interchangeable with another. A
`research` ticket is not done because code got written during the research —
that's scope creep into `task` territory, and the type-lock rule below is
exactly what stops it from being absorbed silently.

## The frontier self-assignment mechanic

A ticket is **on the frontier** when every ticket it lists as a dependency is
CLOSED. Agents (or humans) self-assign only from the frontier — never from the
full backlog. This holds identically regardless of type: a `task` ticket
blocked on an open `grilling` ticket is not on the frontier, and a `grilling`
ticket with zero dependencies is trivially on the frontier the moment it's
charted. See `task-breakdown.md` for the full mechanics of computing this.

## The type-lock rule (never relabeled in place)

**A ticket's type never changes in place.** This is the concrete mechanism
behind the plugin's invariant: "planning tickets must NEVER be conflated with
or silently converted into execution tickets."

If work on a `grilling`, `prototype`, or `research` ticket reveals that its
true scope requires changing real system state, that ticket MUST close as
**resolved-into-a-new-linked-task-ticket**:

1. Close the original ticket with a comment stating what it resolved into and
   linking the new ticket's ID.
2. Open a new ticket, typed `task`, with a dependency back on the ticket that
   revealed the need for it (or on whatever prerequisite actually applies).
3. The new `task` ticket goes through fog-of-war charting like any other new
   ticket (see `fog-of-war.md`) — it is not exempt just because it emerged
   mid-session.

**Worked example of a scope surprise, handled correctly:**

A `research` ticket, "Find out whether the ticket store fallback needs a
schema migration for existing `.wayfinder/` files," turns up during
investigation that a migration script actually needs to be written and run.

- Wrong: relabel the research ticket `task` in place and keep working in it.
- Right: close the research ticket with "Finding: yes, a migration is needed
  because format changed in v2 → see WAYF-014" and open `WAYF-014`, typed
  `task`, dependency `WAYF-009` (the research ticket), done-condition "the
  migration script is merged and run against the existing store."

**Worked example of a scope surprise, handled incorrectly (the failure mode
this rule exists to prevent):** relabeling `WAYF-009` from `research` to
`task` in place. Now the ticket's history reads as if it was always an
execution ticket, its original done-condition ("a finding is stated") is
gone, and any other ticket that depended on "the research finding being
recorded" has no way to tell that the finding never actually landed — the
execution work silently absorbed it.
