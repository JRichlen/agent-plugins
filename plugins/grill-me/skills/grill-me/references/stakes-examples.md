# Worked triage examples and mid-session re-triage

Load this only when the triage call for a branch is genuinely ambiguous —
most branches are obvious from the table in SKILL.md.

## LIGHT — two-way door, small blast radius

- Renaming an internal helper function.
- Choosing a local variable naming convention.
- Reordering unexported module internals.

Depth: one confirm-or-skip question with a stated default. If the user
doesn't object, assume the recommendation and move on.

## STANDARD — mixed

- **Reversible, wide blast radius**: feature-flagging a new user-facing UI
  panel. Users see it, but it's a flag flip to pull back — the two-way door
  keeps it out of DEEP despite the audience.
- **Irreversible, narrow blast radius**: choosing a log line format for an
  internal debug log. Hard to migrate later, but nobody outside the team reads
  it — the small blast radius keeps it out of DEEP despite being a one-way
  door.

Depth: the branch's natural 1-3 questions, each with a recommendation. No
forced pushback unless an answer contradicts an earlier one.

## DEEP — one-way door, wide blast radius

- Choosing the primary-key / id shape for a new public API resource — changing
  it later breaks every client that ever called it.
- Picking an auth model for a new service — security posture, hard to unwind,
  wide blast radius by definition.
- A schema migration that drops a production column.

Depth: full sub-tree decomposition, devil's-advocate pass on the first answer,
explicit confirm required (see `technique.md`).

## Novelty bump

A pattern with no precedent in this codebase or team — say, the first time
introducing event sourcing, or the first cross-region deployment — bumps one
tier even if blast radius alone reads STANDARD. There is no established
fallback to lean on if the choice turns out wrong, and that absence is what
DEEP triage is meant to catch.

## Already-decided collapse

If the plan text already states a firm, specific choice with its own
reasoning — "we're using Postgres because the rest of the stack already runs
Postgres and we don't want a second database to operate" — don't re-ask that
as a fresh question at whatever tier the topic would otherwise carry. Collapse
it to a single confirm-or-skip line ("Postgres, per your reasoning above —
confirm?") regardless of tier. Re-litigating settled ground wastes the
question budget the dynamic-depth model exists to protect.

## Mid-session re-triage

If a LIGHT-tier answer — "just use an in-memory queue for now" — later turns
out to gate a DEEP-tier consequence the user reveals in a subsequent round
(that queue turns out to be the actual delivery guarantee for a billing
event), reopen *only that branch* at DEEP tier: devil's-advocate pass, explicit
confirm, the works. Do not restart the session or re-ask already-settled LIGHT
questions elsewhere in the tree — the re-triage is scoped to the one branch
whose real stakes were misjudged.
