---
id: discipline.scope-fence
kind: behavior
version: 1.0.0
domains: [engineering-discipline]
---

# Scope fence

Derived from the `scope-fence` plugin invariant (`plugins/scope-fence/AGENTS.md`).

<rule id="trace-every-hunk" strength="must">
Keep every hunk of the diff traceable to the stated task; record out-of-scope
discoveries as findings, never fold them into the same change.
</rule>
