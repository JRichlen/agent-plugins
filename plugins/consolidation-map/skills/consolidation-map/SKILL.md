---
name: consolidation-map
description: >-
  Map a catalog consolidation by unit of work rather than by file, with one
  verb per entity and counts that must reconcile. Use for a "meta diff" or
  when merging or pruning plugins, skills, services or packages.
license: MIT
compatibility: >-
  PORTABILITY: pure bookkeeping and prose — no hooks, no scripts, no
  harness-specific primitive. The delegation tiers are advice; one agent can
  play every role. Ports to any harness that can read an inventory and write
  a document.
---

# consolidation-map

## Invariant

Every entity in the before-inventory appears in exactly one disposition row,
the before and after counts reconcile, and a map that does not reconcile is
reported as failing — NEVER presented as done, and NEVER filled in with a
decision the user did not make.

## Not this

- **A file diff or a changelog.** `git diff` and a PR file list answer *what
  bytes moved*; this answers *what happened to each thing and why*. Keep the
  raw diff underneath as the receipt, never as the lead.
- **docs-hygiene** (`plugins/docs-hygiene`) audits instruction files for
  claims that went stale. A map is a one-time account of a change, not an
  audit of what the docs say now.
- **graveyard** (`plugins/graveyard`) archives and deletes repositories. This
  skill only describes a consolidation; it never removes, moves or archives
  anything.
- **semver-gate** (`plugins/semver-gate`) classifies how risky one change is
  to its consumers. A map records what happened to each entity; it does not
  grade the blast radius.

## When to use this

A catalog is being (or was just) reorganized and a reader needs the story, not
the file list: several plugins folded into one, a skill split in two, a
service retired, a package renamed. Also when a PR touches dozens of entries
and the reviewer cannot tell which moves were deliberate.

## Inputs

1. **Inventory** — the before-list: every entity that existed, by name. If
   the user supplied only a repo or a range, build the list from it.
2. **Decisions** — what the user decided for each entity or group, and why.

If a decision is missing for any entity, ask. One question at a time, as a
multiple choice with the recommended disposition first. A before/after
inventory shows *that* an entity went away, not whether it was merged
somewhere or retired outright; that is a decision, so never infer it from
the diff. Name an entity with no decision as `UNDECIDED` in the output rather
than guessing; it gets no verb row and is not counted, and the map stays a
draft until it is decided.

## The verbs

A closed set. Every entity gets exactly one.

| Verb | Meaning | Counts as |
|---|---|---|
| keep | stays as-is | kept |
| new | created by this work | new |
| absorb | an existing entity that gains the contents of others | kept |
| merge-into | a source that disappears into a named target | merged-away |
| deprecate | still present, flagged to go | kept |
| retire | removed with no replacement | retired |

"Absorb" and "merge-into" are one relationship seen from both ends. Write the
target's row as **absorb** (or **new** if it did not exist) and each source's
row as **merge-into** with the target named; the sources are rows in their own
right, so nothing disappears silently.

## The map

Group by **unit of work**: one intent, however many entities or files it
touched. The unit's title says the intent in a phrase ("A and B go away
because they were built into C"). Omit empty groups, and put all untouched
entities in a single closing **Unchanged** group.

Each unit carries:

- its rows (verb, entity, and for merge-into the target);
- **Why:** one line, taken from the decision or the record; if none was
  recorded, write "not recorded" rather than supply one;
- **What's lost:** what no longer exists or no longer works the same way, or
  "nothing" if that is true. If you cannot say, say that — do not write
  "nothing" to close the box;
- for a retire, the evidence it is unused, or "evidence: none supplied".

Lead with the counts line, then the units, then the reconciliation:

```
Consolidation map: <catalog>, <date>
Before N | After M | Net M-N   (kept K, merged-away X, retired R, new W)

## Unit: <intent>
- new         C
- merge-into  A -> C
- merge-into  B -> C
Why: ...
What's lost: ...

## Unchanged
- keep  D, E, F

## Reconciliation
N = K + X + R : <n> = <k> + <x> + <r>   OK | FAIL
M = K + W     : <m> = <k> + <w>         OK | FAIL
Every inventory entity appears once: OK | FAIL (<names>)
Every merge-into target survives:    OK | FAIL (<names>)
```

## Reconciliation

Before = kept + merged-away + retired. After = kept + new. Deprecated and
absorbing entities are in both lists, so they count as kept.

Also check the rows, not just the totals: no entity in two rows, none in
zero, no row for an entity absent from the inventory unless it is **new**,
and every merge-into target is itself in the after-list (never a retired or
merged-away entity). Two errors can cancel in the totals, so the counts alone
are not the check.

On any mismatch, or while any entity is `UNDECIDED`, print
`RECONCILIATION FAILED`, list the offending entities, and stop. Do not adjust
a count to make it balance, and do not hand over the map as complete.

## Delegation

When the catalog is large, split the work by what each part needs:

- **Bulk reading** — listing the inventory and collecting facts for each
  entity — fits the cheapest, fastest tier.
- **Judgment** — grouping into units, writing the Why and What's lost lines —
  fits a mid tier.
- **Verification** — re-deriving the counts and the row checks from the
  inventory and the rows, without reading the author's totals — fits the
  strongest tier available, and is a different run from the one that wrote
  the map.

Only the parent asks the user anything; a delegate that hits a missing
decision returns it to the parent.
