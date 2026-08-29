---
id: discipline.stop-rule
kind: behavior
version: 1.0.0
domains: [engineering-discipline]
---

# Stop rule

Derived from the `stop-rule` plugin invariant (`plugins/stop-rule/AGENTS.md`).

<rule id="declare-attempt-bound" strength="must">
Declare an attempt bound before entering any retry loop, count attempts
honestly against it, and at the bound stop and report state with ranked
hypotheses — never make attempt N+1 on momentum.
</rule>

<probe id="is-this-a-guess">
Is the next retry a diagnosis-driven change, or a guess repeated harder?
</probe>
