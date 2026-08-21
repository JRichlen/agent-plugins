---
description: Stream each dimension through research→verify with no barrier, then reconcile into one recommendation where refuting verdicts win (Strategy B — a decider)
argument-hint: "[what to decide — e.g. 'recommend an observability stack within our RAM budget']"
---

# /pipelined-verdict-wins

Run the **pipelined-verdict-wins** orchestration template (Strategy B): each
dimension flows produce → verify independently (no barrier), then one reconciler
folds everything into a single recommendation under an explicit **verdict-wins**
rule — where a verifier refuted a research claim, the refuted claim cannot
survive into the answer as if true — plus a hard-constraint gate. It returns one
`{ recommendation, correctionsToPriorBrief }`. Reach for it when you want a
coherent decision out the back, latency matters, and there are floors the answer
may not cross.

**Invoke the `orchestrate` skill and follow it.** The skill explains
the shared discipline, helps you scout `dimensions` and `constraints`, and points
at the template to run with `Workflow({ scriptPath, args })`. The template lives
at `skills/orchestrate/templates/pipelined-verdict-wins.workflow.js`;
the annotated walkthrough is `references/strategy-b-pipelined-verdict-wins.md`
and a filled-in example is `references/worked-example-observability.md`.

Task: `$ARGUMENTS`

Before running, settle these fields (the skill walks you through them):
- **context** — only settled facts, ~5–15 lines, injected into every agent.
- **dimensions** — the axes that actually cut the problem; scout them first.
- **constraints** (optional) — the non-negotiable floors the answer may not cross.
- **maxClaims** (optional) — per-dimension cap on inline verifications.
