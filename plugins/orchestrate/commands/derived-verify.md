---
description: Fan out research over dimensions, then adversarially verify the risky claims it surfaces (Strategy A — a sensor, returns raw research + verdicts)
argument-hint: "[what to research and verify — e.g. 'compare these three queue backends for our cluster']"
---

# /derived-verify

Run the **derived-verify** orchestration template (Strategy A): a barrier
fan-out of research over fixed dimensions, then adversarial skeptics pointed at
*exactly* the risky claims that research surfaced — targets harvested from the
fan-out, not guessed up front. It returns the raw `{ research, verdicts }`; it
does not decide for you. Reach for it when you don't yet know what's worth
fact-checking and you want to inspect the verdicts yourself.

**Invoke the `orchestrate` skill and follow it.** The skill explains
the shared discipline (frozen ground-truth context, per-stage structured output,
adversarial verifier that defaults to disbelief), helps you scout the right
`dimensions` inline, and points at the template to run with
`Workflow({ scriptPath, args })`. The template lives at
`skills/orchestrate/templates/derived-verify.workflow.js`; the
annotated walkthrough is `references/strategy-a-derived-verify.md` and a filled-in
example is `references/worked-example-observability.md`.

Task: `$ARGUMENTS`

Before running, settle these three fields (the skill walks you through them):
- **context** — only settled facts, ~5–15 lines, injected into every agent.
- **dimensions** — the axes that actually cut the problem; scout them first.
- **maxClaims** (optional) — cap on harvested claims sent to verifiers.
