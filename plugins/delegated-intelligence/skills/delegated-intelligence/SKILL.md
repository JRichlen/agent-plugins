---
name: delegated-intelligence
description: >-
  Delegate independent work through bounded briefs, owned outputs and checked handbacks. Use when real workers help; keep small or tightly coupled work direct.
license: MIT
compatibility: >-
  PORTABILITY: prose and files; real dispatch requires a worker tool.
  Without one, work directly and label any sequential pass honestly.
  Independent verification cannot be simulated by changing roles in one pass.
---

# Delegate work

This service owns dispatch, briefs, output ownership, integration and recovery
for a selected unit of work. It does not take over the assistant's identity or
own the project plan. Shared authority, interaction and task-state rules live in
[the operating contract](../../context/OPERATING.md), generated from the
repository's canonical core. Do not edit that packaged copy.

## Invariant

Every dispatched job has a bounded, self-contained brief and an output owner.
A returned report is checked against artifacts and acceptance evidence before
the work is relied upon. No assignment ends with unaccounted workers.

## Entry and exit

Use when the task benefits from independent work or an additional qualified
worker, the inputs and permitted effects can be bounded, and a real worker
tool is available. Keep small or tightly coupled work direct when a brief and
integration would cost more than the work.

Exit after every assignment is reconciled as returned, verified, blocked or
stopped under the core state contract. Return evidence, gaps and the next action
to the calling method. Do not leave a coordination persona, background observer,
dashboard requirement or schedule active after that unit ends.

## Assign

1. Reuse the current task/project record. Wayfinder owns persistent plans;
   [context-handoff](../../../context-handoff/skills/context-handoff/SKILL.md)
   owns phase-boundary continuation. Do not create another planning board.
2. Write the [delegation brief](references/templates.md) before dispatch:
   objective, source context, scope, configured model/effort, tools and effects,
   operational allowance, output path/owner, return cap, acceptance and stop
   conditions. Workers return blockers to the main assistant.
3. Allocate against the whole cycle: coordinator, workers, review, retries,
   duplicated context and handoffs. Reserve room for integration. State unknown
   monetary cost rather than inventing it; an estimate is not an enforced cap.
   Preserve configured provider/model choices.
4. Give workers only the tools needed for the assignment. Workers never receive
   agent-spawning or session-control tools, including scheduling, messaging and
   connectors that send or spend. The main assistant performs those actions
   under the core authority contract.
5. Fan out independent assignments with disjoint output ownership. Shared inputs
   are read-only; do not launch downstream work before its dependencies exist.
   Assign one integrator for shared/derived files.

## Hand back and integrate

Workers write partial artifacts as useful work lands and return a short brief
with source/evidence pointers. Do not flood the main context with raw transcripts.
The worker reports `returned`; it cannot declare the coordinator's check complete.

Inspect the actual output: existence, non-empty content, expected change and a
diff for unrelated edits. Then check the acceptance condition. A complete file
or a worker's confidence does not establish semantic correctness. Use
[verify-before-claim](../../../verify-before-claim/skills/verify-before-claim/SKILL.md)
for evidence behind a completion claim; use an independent check only when
required and actually available.

Update the existing record with the core state and evidence. Share material
changes, blockers and needed decisions from that record. Attribute reported
findings and distinguish them from checks performed directly.

## Recover or stop

Read [recovery](references/recovery.md) when output is missing, invalid, stale
or interrupted. Preserve valid outputs; invalidate downstream work only when
it consumed an invalid dependency. Include the previous failure in a retry brief.

[stop-rule](../../../stop-rule/skills/stop-rule/SKILL.md) owns retry accounting,
bounds and stop reports. This service supplies no second retry quota. A user
stop takes precedence over recovery: stop dispatching, account for in-flight
actions and uncertain outcomes, preserve results, and return control.

Learning proposals belong to recurrence-detector and existing decision records.
This service does not schedule follow-ups or adopt instruction changes.
