# Failure handling and recovery

Treat agent failure as normal. This is the detail behind the short list in
`SKILL.md`.

## Relaunch rules

- **One-for-one.** Relaunch only what was lost. Add the failure reason to the
  retry brief.
- **Rest-for-one.** If a downstream stage consumed a failed upstream output, redo
  that stage too.
- **Two retries, then escalate** with partial results and a recommendation.

## Interrupts and restarts

- **User interrupt.** An interrupt can stop every background agent. Check which
  outputs landed on disk, compare with the task list, mark landed items done,
  relaunch only the lost work, and say what you did in one line.
- **Container or session restart.** Pending result notifications can be dropped.
  On resume, do not trust the board alone: check output files and the work
  directory first, reconcile, then relaunch only what is truly missing. Never
  relaunch work whose file already exists and is complete.

## Partial and stray results

- **Partial results** are usable. Record what is missing as a gap, not as a failed
  job.
- **Stray behavior** (out-of-scope tool calls, wrong tier, unrequested actions):
  note it, fix the allowlist, relaunch if the output is tainted.

## Spot-check, do not trust

After an agent reports "corrections applied" or "file updated", check cheaply
yourself: the file exists, is non-empty, a grep finds the change, and a diff shows
nothing else changed (a worker that did what it was asked can still have rewritten
the rest of the file). A report is a claim; the file is the evidence. An empty or missing output behind a "done"
report is a failed task, relaunched with the reason in the brief.

## Verification catches real errors

A fresh verifier, not the producer, told to try to falsify. Typical catches: a
widely reported feature that never shipped, and a retired product's stale numbers
cited as current. Old notes keep their historical wording; the latest synthesis
carries the guards (what was corrected, what is unverified).
