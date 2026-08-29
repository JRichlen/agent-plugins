---
id: discipline.find-before-build
kind: behavior
version: 1.0.0
domains: [engineering-discipline]
---

# Find before build

Derived from the `find-before-build` plugin invariant
(`plugins/find-before-build/AGENTS.md`).

<rule id="search-first" strength="must">
Before introducing any helper, wrapper, utility, or dependency, run named
searches for an existing equivalent and show their results.
</rule>

<antipattern id="parallel-version">
Do not build a parallel version of a found, usable equivalent.
</antipattern>
