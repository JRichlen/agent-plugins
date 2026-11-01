# Compare models without turning on a tournament

Start by fixing fixture meaning and calibrating judgment. A cheaper model that
fails easier tasks can manufacture apparent skill benefit. A stronger judge
cannot repair a contradictory deterministic oracle.

This directory is a **free planning foundation**, not an execution platform.
It reuses existing Promptfoo packs and matrix/replay concepts. No runner,
provider batch adapter, paid pilot or model-default switch is enabled.

## Configure one comparison

| Source | Owns |
|---|---|
| `models.json` | Exact provider identifiers, available revision, role, family, effort/tokenizer evidence and rate evidence; no credentials |
| `suites.json` | Versioned case/arm definitions, immutable source commit and file hashes, tools/authority conditions and missing qualification |
| `comparison.json` | Explicit selected cells, cases, arms, repeats, attempt/token bounds and estimate cap |
| `plan.py` | Free schema/source validation, counting and immutable dry-run receipt |

The supplied comparison selects zero cells with zero caps. From the repository
root, with Python and Git:

```sh
python3 evals/experiments/plan.py
python3 evals/experiments/plan.py --receipt /tmp/new-comparison-plan.json
python3 -m unittest discover -s ci/tests -p 'test_comparison_plan.py'
```

The receipt path must not exist. A plan's `state: planned` is not a result.
Adding a model requires an explicit registry entry and free schema validation;
live compatibility and cost/data authority remain separate prerequisites. A
provider alias without a known revision stays unresolved. Do not infer one
model's parameters, thinking semantics or tokenizer from another's settings.

Select cells individually; there is no automatic models × suites cross-product.
Each cell names subject, judge, suite, cases, arms, repeats, maximum attempts,
execution mode and per-role input/output token bounds. Counts include allowed
attempts, not only successful observations. Rates are unknown until backed by
the exact provider route/context/tier; unknown rates produce unknown estimates
and an unknown budget check. An estimate cap is not spending approval or a bill.

The frozen example is an existing **opposite-rubric boundary calibration**, not
a common-outcome efficacy suite. Its real and calibration arms reward different
behavior. It has no human gold or independent tournament holdout. Never tune
PR129's frozen corpus or describe this example as controlled efficacy evidence.

## Execution modes and batches

`sync` describes the current per-request shape. `replay` plans judge calls over
an identified saved-output file with zero new subject attempts; a future adapter
must verify its bytes, row selection and matching suite conditions before use.
No replay calls are made here. `provider_batch` currently fails closed as
unsupported; it never silently falls back to synchronous paid calls.

Pinned Promptfoo 0.122.0 does not become a provider batch orchestrator through
`maxConcurrency` or an invented `batch: true`. A future batch adapter needs:

- Durable submission identity and batch ID; resume before considering resubmit.
- Stable per-cell/custom IDs because result order is not guaranteed.
- Retained partial successes and usage; retry only confirmed infrastructure or
  expiry failures within the reserved attempt/output budget, not bad behavior.
- Explicit provider eligibility, cancellation state and data/retention authority.

Subject and judge are dependent stages, so two asynchronous windows can add
substantial delay. A batch of requests is not a tool-using agent session. See
[Anthropic batches](https://platform.claude.com/docs/en/build-with-claude/batch-processing),
[OpenAI batches](https://developers.openai.com/api/docs/guides/batch), and
[OpenRouter batches](https://openrouter.ai/docs/batch-quickstart). Do not halve a
gateway route's price without route-specific batch evidence.

## Evaluate the judge before the subject tournament

First reuse saved outputs with blinded human labels, negative/near-miss and
adversarial examples, frozen rubric versions and a sealed holdout. Report
false-pass/false-fail rates, abstention/disagreement, JSON validity, latency,
actual tokens and observed cost. Human gold is not supplied by another model.
Use a cross-family adjudicator for disagreements and a random audit, not every
row. Same-family subject self-grading is rejected by the planner.

Haiku 5.5 is a leading proposed judge candidate; Luna is another comparison
candidate. Qwen remains the configured subject baseline. Other subject routes,
including Nemotron, require exact revision/provider/quantization and adapter
evidence before comparison. These are proposals, not activated defaults or
measured local winners. Keep rate snapshots and route evidence with
[`ci/model-pricing`](../../ci/model-pricing/); its watch policy is not proof of
the model actually configured in every eval pack.

Only after judge calibration should a quality study compare matched no-skill
and skill arms with identical task, tools, authority and budget, repeated trials,
no-activation cases and real artifact checks. Keep boundary fragility and
representative user-model lanes separate. Report useful quality, failures,
latency and cost per valid evaluation; do not collapse them into a misleading
single winner. Live execution and any later promotion need separate approval.
