---
id: discipline.egress-gate
kind: behavior
version: 1.0.0
domains: [engineering-discipline]
---

# Egress gate

Derived from the `egress-gate` plugin invariant (`plugins/egress-gate/AGENTS.md`).

<rule id="enumerate-outbound" strength="must">
Before any call that transmits content off-machine, enumerate what is being
sent and to whom; never include secrets, credentials, or out-of-scope content
in an outbound payload.
</rule>
