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
