---
name: eval-ladder
description: >-
  Design and audit the eval ladder for an agent system: build tiers bottom-up
  from observed failures, pick the cheapest rung that can catch a given
  regression, name what each rung structurally cannot prove, validate every LLM
  judge against human labels (TPR and TNR separately, never raw agreement), and
  score irreversible-action scenarios pass^k rather than by majority. Use when
  designing, auditing, or defending a test/eval strategy for an agent, skill, or
  prompt; when adding an eval tier or LLM judge; when a suite is all-green and
  you cannot say what it would catch; or on phrases like "assess our testing
  strategy", "do we have eval coverage", "is this judge trustworthy",
  "pass@k or pass^k", "what does this tier actually prove".
license: MIT
compatibility: >-
  PORTABILITY: pure analytical and authoring discipline — no hooks, no
  subagent-spawning tool, no harness-specific primitive. The rungs are ordinary
  scripts, config files and prose that any harness can run; the procedure is
  reading and reasoning. Works unchanged on claude-code, codex, gemini, cursor.
---

# eval-ladder

## Invariant

Never present an eval result as evidence beyond what its tier structurally
proves: every green is reported with its blind spot, every LLM-judge verdict is
bounded by that judge's measured TPR/TNR against human labels, and a scenario
guarding an irreversible action passes only when EVERY trial passes (pass^k) —
never on a k-of-N majority.

A green check is a claim. The claim is not "the system works"; it is "this
tier's specific probe did not fire." Stating the difference is the whole skill.

## When to use this

- Designing an eval suite for an agent, skill, prompt, or tool from scratch.
- Auditing an existing suite: what does it cover, what can it structurally never
  cover, where would a real regression walk through.
- Adding a tier, a judge, or a scenario — deciding which rung it belongs on.
- A suite that is all-green and has never gone red: it may be measuring nothing.
- Reviewing someone's claim that a change is "verified" or "tested".
- Choosing a metric: pass@k, pass^k, a pass-rate floor, or a hard gate.

Do **not** use it to write the eval's actual content for a domain you have not
looked at. The first rung is looking at real failures; this skill will send you
there rather than let you skip it.

## The order that matters most

Build **bottom-up from observed failures**, not top-down from imagined
invariants. The single highest-return activity is error analysis: sample 20–100
real traces, have one person write a free-text note on the *first* thing that
goes wrong in each, cluster those notes into 4–8 failure modes, then build one
narrow binary check per mode. Suites authored from design intent test the
failures you imagined; suites authored from traces test the ones you have.

A suite with no error-analysis origin is a hypothesis, not a measurement. Say so
when you report it. See [judge-alignment.md](references/judge-alignment.md).

## The ladder

Cheapest first. Each rung catches a class of defect the rungs below it
structurally cannot — that "cannot" is what earns the rung its cost.

| # | Rung | Catches | Structurally cannot |
|---|---|---|---|
| 0 | **Structural** — parses, wiring, manifests, load-bearing greps | Broken plumbing, deleted invariant text | Whether a sentence still *means* anything |
| 1 | **Discriminating corpus** — mutate a known-good baseline, assert rejection *for the right reason* | A gate that has stopped gating | Defects it has no fixture for |
| 2 | **Code assertion** — regex, schema, state query, per observed failure | Anything a deterministic predicate can decide | Subjective quality; unanticipated shapes |
| 3 | **LLM judge** — binary, few-shot-critique-grounded rubric | Residual subjective failures | Anything beyond its measured TPR/TNR |
| 4 | **Trajectory / decision point** — the path, or the next move at a frozen prefix | Wrong route, wrong tool, wrong order | That the chosen path then *worked* |
| 5 | **Outcome / environment state** — diff the world before vs after | "It said done but nothing happened" | Intent, and anything outside the diffed scope |
| 6 | **Sandboxed cross-harness end-to-end** | Harness-dependent behavior; the real loop | Non-safety qualities; costs real money |
| 7 | **Human demonstration** — the thing run on real material, misses included | Whether the change is worth having | Nothing — and nothing can machine-enforce it |

Two rules govern movement on the ladder:

1. **Descend before you ascend.** If a deterministic predicate can decide a
   failure, never buy a judge for it. Judges cost 100+ labels, ongoing
   validation, and a permanent uncertainty band.
2. **Grade the surface closest to the harm.** Text output is the weakest
   surface: an agent can say "your flight is booked" with no row in the
   database. Prefer environment state, then trace, then output. See
   [eval-surfaces.md](references/eval-surfaces.md).

## The audit procedure

For each tier in the suite under review, answer all five.
A tier that cannot answer #2 or #5 is decoration.

1. **What does it prove?** One sentence, in terms of a defect it would catch.
2. **What can it structurally not prove?** If this is blank, the tier is being
   over-claimed. Write it down and publish it beside the green.
3. **What is the grader, and is the grader validated?** Deterministic, or a
   model? If a model: TPR and TNR against held-out human labels, or it is an
   opinion. See [judge-alignment.md](references/judge-alignment.md).
4. **What is the metric, and does it match the question?** Capability → pass@k.
   Reliability, and anything irreversible → pass^k. See
   [metric-choice.md](references/metric-choice.md).
5. **How would it go red?** Name a concrete change that turns it red. If you
   cannot, it is not a gate. Then check the twin: is there a must-not-fire
   control proving the green is not what the bare system does anyway?

Then sweep the whole suite for the failure modes that live between tiers rather
than inside one — saturation, tuning on the gate, criteria drift, the harness
confound, contamination. See
[integrity-hazards.md](references/integrity-hazards.md).

## Reporting

Report coverage as a matrix of *surface × rung*, not as a count of tests. State
the blind spots as first-class findings. Rank recommendations by
`frequency × severity`, and say which rung each belongs on and what it costs.

Never write "fully tested". Write what was probed, by what grader, at what
confidence, and what remains unprobed.

## References

- [eval-surfaces.md](references/eval-surfaces.md) — the five gradable surfaces,
  which rung reaches each, and why output-only grading is the weakest.
- [judge-alignment.md](references/judge-alignment.md) — error analysis, binary
  judges, critique shadowing, and validating a judge with TPR/TNR.
- [metric-choice.md](references/metric-choice.md) — pass@k vs pass^k, floors,
  FAULT-vs-FAIL separation, difficulty calibration, and starvation.
- [integrity-hazards.md](references/integrity-hazards.md) — saturation, tuning
  on the gate, criteria drift, the harness confound, contamination, judge bias.
- [source-map.md](references/source-map.md) — which primary source each rule
  comes from, for when a claim here needs checking at the source.
