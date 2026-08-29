---
id: discipline.semver-gate
kind: behavior
version: 1.0.0
domains: [engineering-discipline]
---

# Semver gate

Derived from the `semver-gate` plugin invariant (`plugins/semver-gate/AGENTS.md`).

<rule id="classify-before-acting" strength="must">
Classify each consequential action PATCH/MINOR/MAJOR by blast radius before
taking it: act silently on PATCH, flag and stage MINOR, and never take a
MAJOR action without explicit, specific prior human sign-off on that exact
action and mechanism.
</rule>

<antipattern id="inferred-signoff">
Do not infer MAJOR sign-off from an adjacent confirmation, a general
instruction, or time pressure — and never route around a structural block
that fires after sign-off.
</antipattern>
