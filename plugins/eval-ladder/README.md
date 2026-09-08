# eval-ladder

Design and audit the eval ladder for an agent system: build tiers bottom-up from
observed failures, pick the cheapest rung that can catch a given regression,
name what each rung structurally cannot prove, validate every LLM judge against
human labels (TPR and TNR separately), and score irreversible-action scenarios
pass^k rather than by majority.

## The invariant

> Never present an eval result as evidence beyond what its tier structurally
> proves: every green is reported with its blind spot, every LLM-judge verdict
> is bounded by that judge's measured TPR/TNR against human labels, and a
> scenario guarding an irreversible action passes only when EVERY trial passes
> (pass^k) — never on a k-of-N majority.

A green check is a claim, and the claim is not "the system works" — it is "this
tier's specific probe did not fire." Stating the difference is the whole skill.

## The ladder

| # | Rung | Structurally cannot prove |
|---|---|---|
| 0 | Structural (parses, wiring, greps) | Whether a sentence still means anything |
| 1 | Discriminating corpus (mutation fixtures) | Defects it has no fixture for |
| 2 | Code assertion | Subjective quality |
| 3 | LLM judge (binary, critique-grounded) | Anything beyond its measured TPR/TNR |
| 4 | Trajectory / frozen decision point | That the chosen path then worked |
| 5 | Outcome / environment state | Anything outside the diffed scope |
| 6 | Sandboxed cross-harness end-to-end | Non-safety qualities |
| 7 | Human demonstration | Nothing — and nothing can machine-enforce it |

Two rules: **descend before you ascend** (never buy a judge for what a predicate
can decide) and **grade the surface closest to the harm** (an agent can say
"booked" with no row in the database).

## References

- `skills/eval-ladder/references/eval-surfaces.md` — the five gradable surfaces.
- `skills/eval-ladder/references/judge-alignment.md` — error analysis and judge
  validation (TPR/TNR, self-agreement as the noise floor).
- `skills/eval-ladder/references/metric-choice.md` — pass@k vs pass^k, floors,
  FAULT vs FAIL, saturation, controls.
- `skills/eval-ladder/references/integrity-hazards.md` — tuning on the gate,
  criteria drift, the harness confound, contamination.
- `skills/eval-ladder/references/source-map.md` — the primary source behind each
  rule.

Distilled from [benchflow-ai/awesome-evals](https://github.com/benchflow-ai/awesome-evals)
and the primary sources it indexes.

## Install

```
/plugin marketplace add JRichlen/agent-plugins
/plugin install eval-ladder@jrichlen
```

## License

MIT
