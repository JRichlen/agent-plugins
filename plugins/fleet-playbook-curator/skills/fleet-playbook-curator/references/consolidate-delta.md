# Typed deltas — index updates a detector can read

The playbook is a curated index whose claims carry `repo@sha:path` citations
and an as-of stamp. Rewriting it wholesale each run loses *what changed*,
which is exactly what the growth loop's DETECT step needs.

## The three operations

| Op | Means |
|---|---|
| `ADD` | a new citation entered the index |
| `UPDATE` | a claim's target moved, or its as-of stamp advanced with changed content |
| `REMOVE` | a claim's source is gone or no longer supports it |

Each delta keeps the citation it concerns: `UPDATE repo@sha:path — <what changed>`.

## Why this matters here specifically

A stale index claim that gets corrected repeatedly is a **failure shape**, not
a chore. Tag it so the detector can count it:

```
SHAPE: stale-doc-claim — index asserted a path that had been renamed (3rd occurrence)
```

Three corrections of the same kind is the signal that a rule is missing —
which is the difference between the index growing and the system learning.

## The rule

Deltas are appended to the run log, never folded into the index prose. The
index says where truth lives; the delta log says how that changed — and only
the second one is countable.
