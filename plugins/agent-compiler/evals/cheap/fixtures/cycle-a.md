---
id: cycle.a
kind: behavior
version: 1.0.0
tasks: [pull-request-review]
requires: [cycle.b]
---

# Fixture: dependency cycle (half A)

<rule id="a" strength="must">
Half of a two-module requires cycle.
</rule>
