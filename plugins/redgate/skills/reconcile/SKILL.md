---
name: reconcile
description: >-
  The END stage of Red Gate: verify a round from a context that did not do
  the work. Refuse an unratified run, re-hash both pinned artifacts and fail
  on drift, run the pinned verifier yourself, accept a PASS only with
  evidence written this run, then apply the mutation control. Use to close
  any redgate round, and never let the writer grade its own work.
license: MIT
compatibility: >-
  PORTABILITY: prose plus one plain-bash script. "A context that did not do
  the work" is satisfied by a fresh subagent where the harness has them, a
  fresh session where it does not, or the human at the round gate — the
  independence requirement ports, the mechanism adapts. No Claude-Code
  primitive is required.
---

# reconcile

## Invariant

A criterion is marked green ONLY when the pinned verifier was run by a party
that did not do the work, both pinned artifacts still hash to their ratified
values, and the harness wrote evidence for that criterion during THIS run —
and a check that survives reverting the hunk it claims to measure is
UNVERIFIABLE, never proven.

## Running it

```sh
plugins/redgate/skills/reconcile/scripts/reconcile.sh --slug <slug> [--root DIR]
```

Exit `0` all checkable green and proven · `1` unmet, drift, or unproven
evidence · `2` usage, missing run, or **unpinned** (never ratified — there is
no contract to grade).

The verifier is handed only `CRITERIA.md`, `check.sh`, and the diff. **Never
the build transcript**: a grader that reads the writer's reasoning inherits
the writer's blind spots.

## The four gates, in order

1. **Ratification** — an unpinned run is refused outright. Grading one would
   let a writer author criteria after seeing results.
2. **Drift** — re-hash `CRITERIA.md` and `check.sh` against the manifest.
   Either mismatch fails the run: a ratified artifact was edited after
   pinning. The drift verdict is distinguishable from an ordinary unmet
   criterion, so "it failed" never hides "it was tampered with".
3. **Execution** — run the pinned verifier yourself. Exit `99` is harness
   failure, not a verdict; fix the harness rather than reading it as red.
4. **Evidence** — a `PASS` is accepted only when `evidence/<n>.out` exists
   and is newer than this run's start. A verdict line without fresh evidence
   is `REJECTED`, never trusted.

## The mutation control

A green check proves a command succeeded. It does not prove the check
measures the criterion. Before accepting a round: **revert the slice's core
hunk and re-run.** A criterion that stays green was never coupled — it is
`UNVERIFIABLE`, not proven, and says so in the report.

Assert on **behavior, not messages.** A check that greps for a warning string
passes even when the gate that should act has been removed, because the
warning fires either way. Assert the exit code; on a fixture whose criteria
otherwise pass, a non-zero exit can only come from the gate under test.

<!-- MEASURED: this rule was learned the hard way, twice, while building this
     skill. Round 1's criteria for drift detection used a fixture whose
     criteria failed anyway, so "exits non-zero" was satisfied by the ordinary
     FAIL path; the first eval-tier port then grepped the drift message, which
     fires regardless of the gate. Both passed the mutation control only after
     being rewritten to assert the exit code on a passing fixture. See
     .redgate/slice2-reconcile*/gates.log for the run record. -->

## When a round cannot be salvaged

The contract is pinned; it is never edited. A round whose criteria turn out
to be wrong closes with an honest verdict and seeds the **next round's fresh
contract** — or, when the criteria are already green before any work, the
gate refuses to open at BEGIN and the round is closed unbuilt. Criteria that
are already true are regression tests, and regression tests belong in the
eval tier, where green-is-expected is the correct semantics.
