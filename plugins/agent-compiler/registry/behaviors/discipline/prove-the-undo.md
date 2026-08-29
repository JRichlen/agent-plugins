---
id: discipline.prove-the-undo
kind: behavior
version: 1.0.0
domains: [engineering-discipline]
risks: [high, critical]
---

# Prove the undo

Derived from the `prove-the-undo` plugin invariant
(`plugins/prove-the-undo/AGENTS.md`). Applicability-scoped: selected only for
high/critical-risk queries.

<rule id="exercise-the-restore" strength="must">
Before any irreversible action, name the restore path and actually exercise it
(restore, diff, or dry-run) in this session; the mere existence of an
unverified backup never justifies proceeding.
</rule>
