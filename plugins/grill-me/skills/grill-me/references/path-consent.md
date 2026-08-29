# Path consent — progressive disclosure for the interview

Deep questions asked before the goal is confirmed are the most expensive
kind of waste this skill can produce: the user answers four careful
questions about a branch they never wanted explored. Path consent converts
the design-tree walk into disclosure — the user sees the map and the price
before paying for any descent.

## Before the anchor — the decline gate

The anchor is not the first move; triage is. Read the whole plan and tier
each branch. If **every** branch triages LIGHT end to end, there is no
session to run — say so briefly ("no session needed") and stop. Do not set
an anchor for a plan that has nothing above LIGHT to route: the anchor and
the consent menu exist to price STANDARD/DEEP descents, and a fully-settled
or all-two-way-door plan has none, so the ceremony would be pure overhead.
The anchor below is reached only once at least one STANDARD or DEEP branch
survives triage.

## The anchor (round 0)

No branch questioning before three slots are set:

1. **Goal** — what we are trying to do.
2. **Outcome** — what success observably looks like when we are done.
3. **Out of scope** — what this session is explicitly not deciding.

Infer all three from the plan text and the conversation first; if they are
already stated, *confirm in one line* rather than re-asking. If they are
not, the anchor is one exchange — never a series. Every branch in the tree
must trace to the anchor; a branch that does not is out-of-scope by
default and is offered as a drop ("this doesn't serve the stated goal —
drop it, or widen the goal?"), never silently explored.

## The consent header

Before descending into any STANDARD or DEEP branch, present the branch as
a header and let the user route:

```
🧭 Path — <branch name> [<tier>, ~<n> questions]
➡️ recommend for the whole path: <one line>
explore / accept / defer / out-of-scope?
```

- **explore** — the only answer that spends questions; descend at the
  branch's tier.
- **accept** — the branch resolves to the stated recommendation with no
  questions asked; lands in the recap under **Confirmed Decisions**,
  marked accepted-by-recommendation.
- **defer** — the branch is pruned for this session; lands under
  **Deferred-for-Later**.
- **out-of-scope** — the branch and its subtree are pruned; recorded so
  the recap shows what was consciously excluded.

LIGHT branches never get a consent header — they are already a single
confirm-or-skip, and a header would double their cost. Consent chooses
*whether* to descend; the stakes tier still chooses *how deep*.

## Routing — the right questions, in the right order

- **Leverage order.** Offer consent headers ordered by stakes × how
  unsettled the branch is. The branch most likely to change everything
  else comes first, not the one easiest to ask about.
- **Structural before granular.** A question is premature if an unresolved
  ancestor branch could invalidate its answer. The frontier rule already
  defers questions with *data* dependencies; this extends it to
  *abstraction* dependencies — naming-level questions wait while an
  architecture-level branch is open.
- **Batch the menu.** When several branches await consent, present the
  headers together as one routing round, then explore only the chosen
  paths — the user routes once instead of being asked path-by-path.

## The irreversibility exception

A DEEP branch whose consequence is a one-way door cannot be quietly
deferred: deferring it is allowed, but it is recorded under **Open Risks
Accepted As-Is** and that consequence is stated at defer time ("deferring
this means the data shape ships undecided — accepted?"). Consent lowers
question cost; it never lowers the stakes floor.

Re-triage still applies: a deferred or accepted branch that a later answer
reveals to be load-bearing reopens — that one branch, at its new tier, not
the whole session.

## Failure modes this exists to stop

- **Anchorless interrogation** — a deep question series fired before the
  goal and outcome are confirmed; the exact waste this reference removes.
- **Anchor before decline** — setting an anchor or opening round 0 on a
  plan that triages LIGHT end to end, instead of declining with "no
  session needed"; the decline gate above runs first, ahead of the anchor.
- **Consent spam** — headers on LIGHT branches, or re-asking consent a
  question at a time instead of batching the routing round.
- **Menu without a recommendation** — a bare "want to explore X?" gives
  the user nothing to accept; every header carries the ➡️ line.
- **Defer treated as resolution** — a deferred branch is an open item in
  the recap, never a decision.
- **Scope-silent exploration** — descending into a branch that doesn't
  trace to the anchor because it seemed interesting.
