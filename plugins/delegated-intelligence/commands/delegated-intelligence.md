---
description: Run large or multi-part work in background subagents so the main thread keeps talking with the user. Covers model tiers, briefs, handbacks, budgets and recovery. Not for small known-file jobs.
---

Invoke the `delegated-intelligence` skill and follow `skills/delegated-intelligence/SKILL.md`.

First decide inline or delegate: one known file, about two tool calls, or an
answer needed now stays inline. Otherwise make a task list, write a
self-contained brief for each task (tier, tools, search budget, output path,
return cap), launch independent tasks together in the background, and keep
talking with the user. When work lands, read the short return brief, spot-check
the files, and report. Say "pending" for anything not in.

PORTABILITY: where the harness has no background subagents, run each brief as a
separate pass that starts from the files and tell the user what is running
between passes.
