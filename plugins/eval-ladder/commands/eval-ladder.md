---
description: Design or audit an eval strategy — map coverage onto the surface × rung matrix, name each tier's blind spot, check every judge is validated, and rank the gaps.
---

Invoke the `eval-ladder` skill and follow `skills/eval-ladder/SKILL.md`.

Use it two ways:

**Audit** (`/eval-ladder audit`, or when pointed at an existing suite) — walk
every tier through the five audit questions, build the surface × rung coverage
matrix, and report the blind spots as first-class findings ranked by
`frequency × severity`. Report what was probed and by what grader;
never report "fully tested".

**Design** (`/eval-ladder` on a system with no suite yet) — start at error
analysis on real traces, not at a rubric. Build the cheapest rung that can catch
each observed failure mode, and only buy an LLM judge for the residual
subjective modes that survive.

If the user names a specific decision instead — which metric to use, whether a
judge is trustworthy, whether a green means anything — answer that directly from
the relevant reference rather than running the whole audit.
