# Agent OS design evidence

**Status:** Awaiting smoke results

**PR:** #83 (`agent-os-lousy-agents-handoff`)
**Evidence authority:** None yet — this file is a result template, not a claim that inference ran.

## Research question

What is the smallest Agent OS context that causes useful, repeatable improvement in automation design without adding semantic failures or unnecessary context?

## Pre-registered interpretation

- Prefer the smallest treatment that earns measurable lift.
- New hard failures outweigh a higher mean score.
- Inspect scenario-level deltas and representative raw responses before changing docs or implementation.
- Treat less than `+0.15` mean rubric lift over baseline as weak evidence, `+0.15` through `+0.35` as a useful signal, and greater than `+0.35` as strong only when repeatable and free of new hard failures.
- A one-sample smoke run may guide low-risk context placement; it does not by itself justify a new canonical node or broad cross-harness capability claim.

## Preflight record

Awaiting generated `preflight.json`.

| Item | Result |
|---|---|
| Commit and source hashes | — |
| Candidate model resolution | — |
| Primary blind-judge model resolution | — |
| Arbiter model resolution | — |
| Conservative maximum cost | — |
| Hard budget | `$0.05` |
| Deterministic validation | — |

## Smoke result

Awaiting generated evidence.

| Treatment | Mean 0–4 score | Delta vs baseline | Hard failures | Actual cost |
|---|---:|---:|---:|---:|
| baseline | — | — | — | — |
| taxonomy | — | — | — | — |
| recipe-aware | — | — | — | — |
| full-agent-os | — | — | — | — |
| **Total** |  |  |  | — |

## Scenario-level deltas

Awaiting `aggregate.json`, `scenario-deltas.json`, and raw judgments.

## Representative evidence

Awaiting raw candidate responses and blind judgments. Include both successes and failures, with scenario/treatment IDs and artifact paths. Do not substitute paraphrased recollection for the raw evidence.

## Faults and limitations

Awaiting run results. Record transport faults separately from semantic failures, missing or non-numeric usage data, judge disagreements, any arbitration, sample count, and threats to interpretation.

## Recommendation

Awaiting evidence. No Agent OS implementation boundary change is approved by this placeholder.

When results exist, state explicitly whether they support:

1. no default Agent OS context beyond baseline;
2. taxonomy-only front-door context;
3. Recipe-aware front-door context with progressive reconciliation/adapters; or
4. a broader context, followed by targeted ablation before wholesale adoption.

## Documentation seams to re-check after evidence

These are review targets, not pre-decided changes:

- clarify the currently unexplained `*`/`+` relationship cardinalities and whether every Automation binds at least one Recipe;
- distinguish expected evidence contracts from emitted runtime Evidence without reflexively adding an eighth ontology node;
- verify that the operator-facing `.Agent` naming convention does not cause compiled Actor identity to be reused as Automation identity;
- sequence `grill-my-automations` so confirmed grill-me decisions produce a proposed diff without bypassing confirmation;
- decide from scenario-level evidence whether reconciliation belongs in default context or a progressively disclosed reference;
- avoid Adapter or cross-harness claims until dedicated capability-honesty scenarios run.

## Tracking

The repository issue used for ongoing experiment learning should link the workflow run, raw artifact, concise PR #83 summary, actual spend, and the final commit that records this evidence. The issue is the running laboratory notebook; this file is the durable, reviewed conclusion.
