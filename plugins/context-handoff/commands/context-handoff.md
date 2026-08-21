---
description: >-
  Walk the ordered continue, clear, handoff, delegate, compact decision tree
  at a phase boundary, and keep any handoff artifact pointer-only — settled
  specs, plans, ADRs, issues, commits, and diffs referenced by path or URL,
  never copied inline. Use this when the context window is getting full,
  you're wondering whether to clear or compact, you need to hand off to
  another harness, directory, or colleague, you've hit a phase boundary and
  aren't sure whether to keep going or start fresh, or you want to cache
  hard-won research before it's lost.
---

Invoke the `context-handoff` skill and follow `skills/context-handoff/SKILL.md`.

Run the boundary check first: is there a just-finished unit of work behind
you and a not-yet-started one ahead, right now? If not, stop — mid-phase
there is nothing to decide.

If yes, walk the five-node decision tree top to bottom — continue, clear,
handoff, delegate, compact — and stop at the first branch whose check
passes. If the tree resolves to HANDOFF, load
`skills/context-handoff/references/portable-extraction.md` and keep the
handoff artifact pointer-only: every settled spec, plan, ADR, issue, commit,
or diff referenced by path or URL, never copied inline. Separately, if this
phase produced hard-to-reach research, load
`skills/context-handoff/references/research-documenter.md` and write or
update `research.md` before executing the chosen branch.
