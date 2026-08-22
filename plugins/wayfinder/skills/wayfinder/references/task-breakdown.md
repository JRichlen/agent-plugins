# Task breakdown: plan → dependency DAG → dispatch-only-the-frontier

Charting a multi-session effort is not "list the tickets." It's "list the
tickets AND state, for each one, exactly what has to close before it can
start." That second half turns a flat backlog into a directed acyclic graph
(DAG), and the DAG is what makes dispatch order a computed fact instead of a
guess.

## Every ticket states its dependencies explicitly

For every ticket charted (see `ticket-taxonomy.md` for the four types), write
its upstream dependencies as a list of ticket IDs that must be CLOSED before
this ticket may be dispatched.

**An empty dependency list is itself a claim** — "this can start right now" —
not an omission or a default you forgot to fill in. Write `dependencies: []`
deliberately, the same way you'd write a non-empty list deliberately.

Worked example DAG (four tickets, mixed types):

```
WAYF-001 [grilling]  "Which repo, gh issues or local file store?"   deps: []
WAYF-002 [research]  "Does the repo already have status:* labels?"  deps: []
WAYF-003 [task]      "Create .wayfinder/ or wire gh labels"         deps: [WAYF-001, WAYF-002]
WAYF-004 [task]      "Chart the remaining tickets for the effort"   deps: [WAYF-003]
```

`WAYF-001` and `WAYF-002` both have empty dependency lists — both are
trivially on the frontier the moment they're charted, and both can run in
parallel with each other right now. `WAYF-003` depends on both closing before
it can start. `WAYF-004` depends only on `WAYF-003`.

## The cycle check (mechanical, not a judgment call)

Before charting is considered complete, walk the dependency graph: starting
from any ticket, follow its dependency edges outward. **If resolving
dependencies ever revisits a ticket already on the current resolution path,
that's a cycle.**

This is a straightforward DAG-traversal check (depth-first, tracking the
current path, flagging a repeat node on that path — not merely a repeat node
anywhere in the graph, which would false-positive on a diamond dependency that
isn't a cycle at all).

**Worked example of a real cycle:**

```
WAYF-010 deps: [WAYF-011]
WAYF-011 deps: [WAYF-012]
WAYF-012 deps: [WAYF-010]   <- revisits WAYF-010, which is on the current path
```

None of these three tickets can ever reach the frontier — each is waiting on
a dependency that is itself waiting on it, transitively. This is not a rare
edge case; it's what happens when two tickets get charted as "informs each
other" but get written down as "blocks each other" in both directions.

**When a cycle is found, charting stops and the user resolves it** by one of
two moves — this is a human call, not something the check makes for you:

1. **Split a ticket** — the cyclic pair usually means one ticket is actually
   two tickets bundled together, one of which doesn't need the other to
   start.
2. **Demote one edge from "blocks" to "informs"** — some dependencies aren't
   true blockers, just useful context. If ticket A merely benefits from
   knowing ticket B's outcome but doesn't actually need it closed first,
   that's not a `deps` edge at all; note it as an "informs" cross-reference
   in the ticket body instead.

Charting does not proceed with a known, unresolved cycle in the graph — a
cyclic dependency set can never produce a non-empty frontier for that subset,
so leaving it in place silently strands those tickets forever.

## The frontier definition (the exact heuristic)

A ticket qualifies for the frontier only when **both** of these hold — and
each condition is checked against a *different* ticket, so never let one
leak onto the other's target:

1. **This ticket itself is still OPEN.** A ticket that has already closed is
   done, not dispatchable, and can never re-enter the frontier.
2. **Every ticket THIS ticket depends on is CLOSED.** That CLOSED test
   applies only to the tickets in its own dependency list — never to the
   ticket itself. An empty dependency list has nothing to check, so
   condition 2 is trivially satisfied.

**A ticket with zero dependencies is therefore trivially on the frontier**
the instant it is open — condition 2 is already (vacuously) satisfied, so
condition 1 is the only thing left to check. This holds no matter how close
the ticket itself looks to being done: "the PR is up," "CI is green," "it's
waiting on one reviewer's approval," "it'll merge within the hour" all still
describe a ticket that is OPEN, not one that has CLOSED. Progress toward
done is not done. **Do not apply condition 2's CLOSED test to the ticket
being evaluated** — that is the exact mistake to avoid: a ticket is excluded
from the frontier only because something *it* depends on is still open,
never because the ticket itself hasn't closed yet.

- A ticket with one open dependency is NOT on the frontier, no matter how
  close that dependency is to closing.
- Frontier membership is **computed fresh each time**, never cached. There is no
  stored "is-on-frontier" flag on a ticket — recomputing from current
  dependency-closed state is what keeps the frontier from drifting out of
  sync with the labels the way a cached flag could (the same discipline
  homelab-board applies to its single status label: state lives in the labels
  themselves, never in a derived field someone forgot to update).

## Dispatch rule: only the frontier, only in parallel

This is the second half of wayfinder's invariant, and it's checked the same
mechanical way as the frontier computation itself:

- Only tickets currently on the frontier may be dispatched concurrently.
- A ticket must **never** be dispatched while any of its listed dependencies
  is still open — not "probably about to close," not "the dependency owner
  says it's basically done." Open means open.

wayfinder's own output stops at the labeled map with a computed frontier; it
hands off the actual dispatch (to the user, to `orchestrate`, or to plain
parallel agent calls) under this rule, and states the rule explicitly to
whatever does the dispatching — it doesn't just imply it.
