---
description: >-
  A halting discipline for iterative fix loops: after a bounded number of failed attempts at the same objective, stop and report the state with hypotheses — never make attempt N+1 on momentum. Use when re-pushing to fix CI, retrying a flaky repro, or any loop where each retry is a guess rather than a diagnosis.
---

Invoke the `stop-rule` skill and follow `skills/stop-rule/SKILL.md`.

If a retry loop is starting (or already underway): declare the bound now
(default 3 for externally visible attempts like pushes, 5 for local
retries), count every attempt at the same objective against it regardless of
mechanism, reset only on a confirmed root cause — and at the bound, stop:
write the report (objective, per-attempt changes and literal outcomes,
current world state, ranked hypotheses with confirming/killing evidence)
instead of making attempt N+1.
