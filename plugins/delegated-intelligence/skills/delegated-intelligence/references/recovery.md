# Recover delegated work

This is the execution recovery method. Core owns state and authority,
stop-rule owns retry bounds, and the calling task owns acceptance.

## Inspect before relaunch

Reconcile the existing task record with actual output and source versions.
For each affected assignment, inspect its output, acceptance evidence and
dependencies. Classify a missing/empty output behind a success report as invalid;
do not trust the report or record alone.

Preserve a valid completed output. File existence alone does not establish
validity: a stale input, wrong result or unrelated edit can invalidate it.

## Limit the repair

- Relaunch only the missing or invalid assignment.
- Recheck a downstream assignment only if it consumed an invalid dependency.
- Add the failure reason and discriminating evidence to the retry brief.
- Charge retries to the same task under stop-rule's accounting. Do not reset
  the counter by changing the worker or wording.
- Record useful partial results and unresolved gaps rather than rerunning all work.

## Interrupts and user stops

After interruption, inspect artifacts and reconcile before deciding what can
resume. A restart notification is not evidence that work landed or disappeared.

On a user stop, stop dispatching. Account for every worker and in-flight action,
request cancellation where supported, preserve results and state any uncertain
outcome. Do not relaunch because a file is missing while a stop remains active.

## Return control

Exit once affected assignments have a core state, evidence/gaps and a next action
in the existing record. If acceptance needs independent verification and no
qualified worker is available, report that boundary; a sequential self-review
is not an independent check.
