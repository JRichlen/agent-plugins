---
description: >-
  Map a catalog consolidation by unit of work rather than by file, with one verb per entity and counts that must reconcile. Use for a "meta diff" or when merging or pruning plugins, skills, services or packages.
---

Invoke the `consolidation-map` skill and follow `skills/consolidation-map/SKILL.md`.

Get the inventory (every entity that existed before) and the decisions (what
happens to each, and why). Ask for any missing decision instead of inferring
it. Group the rows by unit of work, give each unit a Why and a What's lost
line, then reconcile: before = kept + merged-away + retired, after = kept +
new, every entity once. If anything fails to reconcile, print
RECONCILIATION FAILED with the offending entities and stop.
