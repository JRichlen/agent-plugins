# Strategy B — `pipelined-verdict-wins`, annotated

Template: `../templates/pipelined-verdict-wins.workflow.js`

**One line:** stream each dimension through produce → verify with *no barrier*,
then reconcile everything with one agent under an explicit **verdict-wins** rule
and a hard-constraint gate. Return one recommendation plus a self-diff of what got
overturned.

## The shape

```
pipeline (NO barrier — each dimension flows independently)
  traces:    produce ─► verify(its claims) ─┐
  logs:      produce ─► verify(its claims) ─┼─► Synthesize (single reconciler)
  collector: produce ─► verify(its claims) ─┘      │ verdict-wins precedence
                                                    │ constraints = hard gate
                                             returns { recommendation,
                                                       correctionsToPriorBrief }
```

## Why each piece is there

- **`FROZEN-CONTEXT` (`CTX`)** — identical discipline to Strategy A: one
  ground-truth string on every agent so nothing drifts.

- **`pipeline`, not `parallel` (no barrier)** — the defining structural
  difference from Strategy A. Each dimension runs produce → verify on its own;
  dimension B is still researching while dimension A's claims are already being
  checked. Wall-clock is the slowest single chain, not the sum of stages. You
  give this up only when you need a global pass over all claims first (then use
  A).

- **Inline per-dimension verify** — each dimension harvests its own `riskyClaims`
  (capped by `maxClaims`) and fans skeptics at them immediately, carrying
  `{ dimension, findings, verdicts }` forward. Same `ADVERSARIAL-REFUTE-DEFAULT`
  fail-closed skeptic as Strategy A.

- **`VERDICT-WINS` (the reconciler)** — the single synthesis agent is told,
  explicitly: *where a verdict refuted or corrected a research claim, the verdict
  wins — the refuted claim must not survive into the recommendation as if true.*
  This is the epistemic backbone. Without it, a reconciler tends to average
  research and verification into mush; with it, verification has teeth. Every
  overturned claim is listed under `correctionsToPriorBrief` — a self-diff, so
  corrections are explicit rather than silently absorbed.

- **`constraints` as a hard gate** — any strings in `constraints` are injected as
  a floor the recommendation *may not cross*. This is the constraint-axis-gating
  idea: a non-negotiable requirement (a RAM budget, an arch requirement) that can
  disqualify an option wholesale, distinct from a mere research dimension.

- **Returns one `{ recommendation, correctionsToPriorBrief }`** — Strategy B is a
  *decider*. If you want raw research + verdicts to inspect yourself instead, use
  Strategy A.

## When to reach for it

- You want one coherent recommendation out the back, not raw data.
- Latency matters — no dimension should wait for the slowest sibling.
- You have hard constraints that gate the answer.
- You're re-running against a prior brief and want the corrections made explicit.

## Knobs

- `maxClaims` (default 6) — per-dimension cap on inline verifications. Lower than
  Strategy A's default because it's per-dimension, not global.
- `constraints` (default none) — add a string per non-negotiable floor.

See `worked-example-observability.md` for a filled-in `args`.
