# Fog of war: the known-unknown / decided / out-of-scope trichotomy

Every piece of a charted effort must land in exactly one of three buckets:

1. **Decided** — settled, chartable as a `task` (or already resolved).
2. **Open question (known-unknown)** — genuinely unresolved, but the question
   itself can be stated precisely. Chartable as a `grilling` or `research`
   ticket.
3. **Explicitly out of scope** — neither decided nor an open question the
   effort needs to answer. Recorded as a labeled out-of-scope note attached to
   the map, not silently dropped and not silently folded into an adjacent
   ticket's scope.

A map is trustworthy as *complete* only when every piece of the effort has
been sorted into one of these three — not left to float as an implicit
assumption nobody wrote down.

## The test: can you write the question as one sentence with a question mark, right now?

This is the one heuristic that keeps "mark unknowns explicitly" from
degenerating into "be careful" or "use your judgment." Apply it at
ticket-creation time, and again any time a ticket's scope starts to feel
fuzzy mid-effort:

> **Can you state the open question this ticket exists to answer, as a single
> sentence with a question mark, right now?**

### If yes — genuine known-unknown

Type the ticket `research` or `grilling` (see `ticket-taxonomy.md` for which
of the two fits), and write that exact sentence as the ticket's
done-condition: "done when the answer to <question> is stated in a comment."

**Worked example (passes the test):** "Does the target repo already use a
`status:*` label prefix for something unrelated to wayfinder?" — one
sentence, one question mark, answerable with a stated fact. Charter it as
`research`, done-condition: "done when a comment lists the existing `status:*`
labels found, or states none exist."

### If no — not yet chartable

If the honest answer is "I can only gesture at 'figure out the auth story'"
or "something in the deploy area needs sorting out" — that's not a question,
it's a fog bank. **The ticket isn't chartable yet.**

Do not create a vague downstream ticket and hope charting resolves it later —
a ticket whose done-condition can't be stated precisely is a ticket nobody
can actually close, because there's no way to tell when it's done.

**Worked example (fails the test):** "Figure out the auth story for the new
service." This gestures at an area, not a question. The fix: it must first go
through a `grilling` ticket whose sole job is to produce the precise
question(s) — e.g. grill-me interrogates the branch and the session converges
on "Does the new service reuse the existing OIDC WIF trust, or mint its own?"
*That* sentence passes the test and becomes a proper `research` or `task`
ticket, dependent on the grilling ticket closing.

### If neither — explicitly out of scope

Some things surface during charting that are neither a decision nor a
question the effort needs answered — a related idea, a nice-to-have, a
tempting tangent. These don't get silently dropped (where they'd resurface
later as "wait, did we ever decide on X?") and they don't get silently folded
into whatever adjacent ticket happens to be charting at the time (where
they'd quietly inflate that ticket's scope beyond its stated done-condition).

Write them as a **labeled out-of-scope note** attached to the map itself —
visible, dated, with a one-line reason. This is what lets the map be trusted
as complete: a reader can see not just what's charted, but what was
considered and deliberately excluded, distinct from what was simply never
noticed.

**Worked example:** "Should wayfinder also support a Jira-backed ticket
store?" surfaces during charting. It's not decided, and it's not a question
this effort needs answered to proceed. Recorded as: "Out of scope for this
effort: Jira-backed ticket store. Reason: brief specifies gh issues or local
file fallback only; revisit if a user actually needs it."

## Why this matters at both ticket-creation time and mid-effort

The one-sentence test isn't a one-time gate at the start of charting. Re-apply
it whenever a ticket's scope starts to feel fuzzy — during grooming, during a
session that's about to close a ticket and spawns new sub-decisions (see
SKILL.md step 5), or when a dependency reveals more than expected. A ticket
that passed the test at creation can still drift into "actually I'm not sure
what this is asking anymore" — that's the moment to re-run the test, not push
through on momentum.
