# Typed deltas — writing entries a detector can read

An entry rewritten in prose each day is readable by a human and opaque to a
machine. Emitting **typed deltas** alongside the prose costs a line and makes
the growth loop's DETECT step possible without re-reading a month of text.

## The three operations

| Op | Means | Example |
|---|---|---|
| `ADD` | something is true now that was not before | `ADD capability: redgate reconcile ships` |
| `UPDATE` | a standing fact changed | `UPDATE policy: deep tier is per-plugin path-scoped, not repo-wide` |
| `REMOVE` | something stopped being true | `REMOVE assumption: pier fires on any scripts PR` |

## Failure-shape tags

A day that contained a failure carries a `SHAPE:` tag naming the *mechanism*,
not the symptom — that tag is what `recurrence-detector` clusters on:

```
SHAPE: uncoupled-verifier — a check passed for a reason unrelated to what it measured
SHAPE: stale-doc-claim — an instruction file asserted something the repo had changed
SHAPE: budget-not-seam — decomposition triggered by exhaustion rather than a named failure
```

Reuse an existing tag verbatim when the shape repeats. **A new tag for the
same mechanism defeats the count**, and the count is the whole point — three
sightings under three different names look like three incidents.

## The rule

Deltas are **appended, never rewritten**. The prose entry may be revised
(that is `dev-diary-review`'s job); the delta lines are the ledger, and a
ledger you rewrite is not a ledger.
