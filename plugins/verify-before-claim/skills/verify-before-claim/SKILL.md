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
