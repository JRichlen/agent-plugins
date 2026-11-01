---
name: verify-before-claim
description: Choose and run the concrete check needed to support a factual, completion or reproduction claim, then report the result and remaining uncertainty.
license: MIT
---

# Check a claim

The [core operating contract](../../context/OPERATING.md) owns the binding
claim-integrity invariant. Load this procedure to choose or perform a concrete check; it
does not take over the task or require a separate workflow.

1. Name the observation that could show the claim false: a source read,
   reproduction, command, test, or other concrete check.
2. Run it against the relevant current state. A worker report is attributed
   evidence, not a check the coordinator independently performed.
3. Match the claim to the observation. Show or point to the actual result;
   qualify partial coverage, stale inputs and unresolved uncertainty.
4. If the check cannot run, return the claim as unverified and name the blocker.
   Do not silently turn a proposed or reported result into verified completion.

Load the relevant reference only when needed:

| Claim concerns | Procedure |
|---|---|
| Bug reproduction or PR/merge readiness | [references/pre-claim-reproduction.md](references/pre-claim-reproduction.md) |
| A handoff or deliverable another person will act on | [references/uncertainty-flagging.md](references/uncertainty-flagging.md) |
| External research | [references/primary-source-research.md](references/primary-source-research.md) |
| A skill, tool or command's actual behavior | [references/skill-behavior-verification.md](references/skill-behavior-verification.md) |

For selected work requiring a fixed executable acceptance contract and an
independent reviewer, use [verify-work](../verify-work/SKILL.md). An offer-only
second opinion remains a separate method; this procedure does not invoke it.

Exit with the supported claim, evidence pointer and remaining uncertainty.


---
name: verify-work
description: Use an agreed executable acceptance contract and independent review when selected work needs fixed criteria, protected checks and fresh evidence. Optional; not a default task workflow.
license: MIT
compatibility: Bash and coreutils are required by the helpers. Independent review needs an actual separate reviewer/context; scripts do not attest that identity. The Claude Code write hook is host-specific.
---

# Verify work against agreed acceptance criteria

Enter when the task needs a fixed executable acceptance contract or the user
requests this verification method. Ordinary checks can use
[verify-before-claim](../verify-before-claim/SKILL.md) directly. Read the
[core operating contract](../../context/OPERATING.md); authority, scope,
interaction and task state remain there. This method owns no coordinator,
planning cadence, model choices, retries or second project ledger.

1. **Agree what counts.** Use [criteria-contract](../criteria-contract/SKILL.md)
   to write criteria and a checker, observe the appropriate negative controls,
   and pin both after the required owner agreement. Record unresolved human
   observations explicitly rather than calling them mechanically proven.
2. **Protect the contract.** The work's author must not edit pinned criteria,
   checker or manifest to make the result pass. A changed requirement returns
   to the task owner for a new contract. Existing scope and action-risk methods
   determine any required decision; this method adds no repeated approval cycle.
3. **Obtain independent review.** Give an actual reviewer the pinned contract,
   relevant sources and change, then use [reconcile](../reconcile/SKILL.md).
   Identify what actually ran and who/context performed it. Do not label the
   author's own check or sequential rewording an independent review.
4. **Return the result.** Report passed, unmet, drifted, unproven and blocked
   criteria with evidence pointers. A harness fault is not a failed criterion
   and is never proof that the target was rejected. Apply a relevant mutation
   or counterexample control before claiming the check measures its subject.

The helpers retain the `.redgate/<slug>/` data format for existing acceptance
records. It is a legacy storage ABI, not a required public product or a new
mandatory ledger. Do not create a case solely because a task is complex.

Exit to the original task owner with the observations, reviewer provenance and
next decision/blocker. Neither green checks nor this method grant permission
to merge, publish, spend or broaden work.

PORTABILITY: On another harness without the Claude Code write hook, use a
supported equivalent write guard or check pinned hashes before and after work.
Hash checks detect drift afterward; they do not prevent writes. If prevention
is required and unavailable, report that unmet prerequisite rather than claiming
protected execution. Independent review still requires an actual reviewer.


---
name: criteria-contract
description: Prepare and pin agreed executable acceptance criteria for a selected verify-work case. Observe negative controls before work and protect the pinned checker afterward.
license: MIT
---

# Prepare an acceptance contract

Dependency of [verify-work](../verify-work/SKILL.md), not an automatic prerequisite
for every task. The [core](../../context/OPERATING.md) owns authority and
scope; use the existing task record for required agreement and decisions.

1. Run `scripts/scaffold-run.sh --slug <slug> --root <workspace>` to create the
   compatibility-format case. Existing cases are never overwritten.
2. Replace template criteria with testable statements and `check_cmd` lines.
   Keep required human observations as WITNESS. Include at least two executable
   checks and more executable checks than human observations.
3. Run the generated checker and observe every executable criterion reject the
   applicable negative state/control. Exit 1 means criterion failure; exit 99
   means a broken harness and does not count as a negative proof.
4. After the required owner agreement, run `scripts/scaffold-run.sh --pin <slug>
   --root <workspace>`. This records hashes of criteria and checker. Pinning is
   an integrity operation; a hash alone is not evidence of human authorization.

The `.redgate/` path and ARM/TRACE manifest labels remain a compatibility data
format. No recursive round, budget or cadence policy follows from those labels.
After pinning, return the case path and negative-control evidence to the task
owner. Do not edit ratified artifacts during work. A requirement change needs
a new contract rather than a re-pin of the old one.

`scripts/criteria-index.sh` optionally indexes existing records as pointers.
It is not a required new record or proof that an old check is applicable now.


---
name: reconcile
description: Independently run an agreed pinned acceptance checker, reject changed criteria or stale/missing evidence, and return the observed verdict to the task owner.
license: MIT
---

# Reconcile an acceptance result

Enter for a selected [verify-work](../verify-work/SKILL.md) case, from an actual
reviewer/context that did not produce the work. Read the pinned criteria,
checker, relevant source and change. Preserve reviewer provenance in the existing
task record; the script cannot mechanically establish reviewer independence.

Run `scripts/reconcile.sh --slug <slug> --root <workspace>`.

- Unpinned or missing case: refused, exit 2.
- Changed criteria/checker: drift, exit 1.
- Harness fault: no valid verdict, exit 1; do not count it as negative proof.
- Unmet criterion or missing/stale evidence: not accepted, exit 1.
- Green executable criteria with evidence from this execution: exit 0, subject
  to criterion quality, required human observations and independent provenance.

Use an applicable mutation/counterexample control to establish that a check
rejects the wrong state. A check that remains green when its relevant change
is removed is not proof of that behavior. Preserve WITNESS observations as
unproven until the required human observation occurs.

Return the verdict, actual evidence and remaining limits to the task owner.
Do not prescribe another delivery round or grant release/action authority.
