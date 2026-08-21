# Strategy A — `derived-verify`, annotated

Template: `../templates/derived-verify.workflow.js`

**One line:** fan out research over fixed dimensions (a barrier), then harvest the
risky claims out of that structured output and fan adversarial skeptics at
*exactly that harvested set*. Return the raw research + verdicts; synthesize
nothing.

## The shape

```
Research (parallel, barrier)      Verify (parallel)
┌─ dim: traces  ─┐                 claim₁ → skeptic → verdict₁
├─ dim: logs    ─┤ ──harvest──►    claim₂ → skeptic → verdict₂
└─ dim: collect ─┘  riskyClaims    …
                                   returns { research, verdicts }
```

## Why each piece is there

- **`FROZEN-CONTEXT` (`CTX`)** — one ground-truth string prefixed onto every
  agent prompt. Researchers and skeptics reason from the *same* settled facts, so
  a skeptic never "refutes" a claim by disagreeing about the environment.

- **The barrier (`parallel`, not `pipeline`)** — this is deliberate. You need the
  *complete* research set in hand before harvesting, because the whole point is a
  global view of the claims: dedup across dimensions, or cap the total number of
  verifications (`maxClaims`). If you don't need that global pass, Strategy B's
  streaming pipeline is cheaper in wall-clock.

- **`DERIVED-TARGETS` (the harvest)** — `research.flatMap(r => r.riskyClaims)`.
  The verify set is a *function of the research output*, never a list the author
  guessed up front. This is the defining move: you cannot know what is worth
  fact-checking until the research surfaces it. It only works because
  `RESEARCH_SCHEMA` guarantees every research result has a `riskyClaims` array —
  structured output is what makes the harvest reliable.

- **`ADVERSARIAL-REFUTE-DEFAULT`** — the skeptic prompt says *default to
  "refuted" unless the evidence clearly supports the claim*. Disbelief is the
  default so an unsupported claim fails closed rather than getting a free pass.
  The verifiers also run as `agentType: 'general-purpose'`, a different agent
  than produced the claim, so the check isn't the researcher nodding at itself.

- **Returns raw `{ research, verdicts }`** — no synthesis. Strategy A is a
  *sensor*, not a decider. The caller inspects the verdicts and decides what a
  refuted claim means. If you want the workflow itself to reconcile into one
  answer, that's Strategy B.

## When to reach for it

- You don't know what's worth checking until the research runs.
- You want the raw research + verdicts to inspect, log, or feed elsewhere.
- A global pass over all claims matters (dedup / total cap) before verifying.

## Knobs

- `maxClaims` (default 24) — hard cap on harvested claims sent to verifiers.
  Raise for exhaustiveness, lower to bound cost.
- Swap `agentType`, or give each verifier a distinct lens, to make the adversarial
  pass perspective-diverse instead of N identical skeptics.

See `worked-example-observability.md` for a filled-in `args`.
