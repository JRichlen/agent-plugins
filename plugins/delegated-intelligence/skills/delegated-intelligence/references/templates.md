# Delegated execution templates

Use only the fields needed to make a bounded assignment reviewable. The core
[task-state contract](../../../context/OPERATING.md) defines shared state;
these templates add execution detail rather than another project plan.

## Delegation brief

```text
TASK ID: <existing task id>
OBJECTIVE: <bounded deliverable> | PURPOSE: <why it is needed>
CONTEXT: <source pointers, inputs and relevant verified findings>
SCOPE: IN: <...> OUT: <...>
TIER: <configured model and effort; task-fit reason, no vendor default>
TOOLS ALLOWED: <allowlist and permitted effects>
CONTROL TOOLS: no agent spawning, session control, messaging, scheduling, sending or spending
ALLOWANCE: <worker/round/search/output limits; whole-cycle reserve; cost estimate or unknown>
OUTPUT PATH: <one owner; shared inputs read-only>
RETURN: <bounded summary and evidence pointers; no raw transcript dump>
DONE WHEN: <checkable acceptance condition>
STOP WHEN: <scope/effect/allowance limit, user stop or unresolved blocker>
IF BLOCKED: preserve partial results, report to the main assistant, stop; do not interview the user
```

A retry uses the same task id and adds `PREVIOUS ATTEMPT:` with the failure
and diagnostic evidence. Retry limits come from stop-rule, not this template.

## Return brief

```text
TASK ID: <existing task id>
STATE: returned | blocked | stopped
OUTPUT: <paths and source/evidence pointers>
FINDINGS: <bounded factual summary; distinguish observations from inference>
CHECKS: <checks actually run and their results>
GAPS: <unchecked, missing, stale or uncertain>
ALLOWANCE USED: <observable usage; estimates labeled>
NEXT ACTION: <proposed next step, not authorization>
```

A worker never marks its return `verified`. The calling assistant checks the
artifacts and required acceptance evidence first.

## Existing task record

Retain the core fields: id, objective, owner, scope, state, evidence, next_action
and decision_required. Add output ownership, dependencies, attempts and allowance
usage to that same record when useful. Do not create a separate status board.
Persistent planning remains Wayfinder's responsibility.

## Status update

Lead with the objective's current state and material change. Include relevant
evidence/limits, next action and any required decision. Use the core interaction
contract; there is no separate question format or timed check-in policy here.
