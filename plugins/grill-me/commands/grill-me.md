---
description: Interview the user about a plan before work starts, single-session and no subagents required, walking its design tree and scaling question depth to each branch's stakes (reversibility x blast radius) while offering a recommendation at almost every step. Use on phrases like grill me, interview me about this plan, stress-test this plan, or before starting a nontrivial multi-step change whose design isn't yet settled.
---

Invoke the `grill-me` skill and follow `skills/grill-me/SKILL.md`.

PORTABILITY: harness-agnostic — this command is a plain conversation with the
user, no subagents or Workflow tool required.

Treat the plan under discussion (the current conversation, or a plan the user
points at) as the design tree to walk. Run the frontier/round loop: compute
the current frontier, ask it as one numbered round with a stated
recommendation on every question, wait for answers, recompute, repeat until
the frontier is empty. Size each branch's depth to its stakes tier — do not
ask a fixed number of questions regardless of what's at stake. End with the
synthesized recap (Confirmed Decisions / Open Risks Accepted As-Is /
Deferred-for-Later) and get explicit confirmation before treating the plan as
ready to execute.
