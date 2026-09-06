# Orchestration reference

## Routing baseline

Use Luna for fast, bounded extraction, summaries, triage, and small edits. Use Terra for balanced bounded coding. Use Sol for reliable everyday analysis, implementation, and review. Use Astra for demanding ambiguity, synthesis, or high-consequence work only when authorized. These are provisional role baselines, not a ranking or guarantee; verify runtime availability and reasoning settings before dispatch.

For cross-vendor candidates, read [model-equivalence.md](model-equivalence.md). It supplies sourced task-fit hypotheses, not provider substitutions or permission to change a configured model, account, or provider.

Bounded known questions usually need one appropriately sized worker and a clear acceptance check. Exploratory unknowns benefit from a finite decomposition pass, followed by narrower work that gathers decision-changing information. Fan out only independent work. Shared dependencies, duplicated prompts, or common sources can make agreement correlated rather than confidence. Lightweight coordination can aggregate clear high-I/O checks; uncertain decomposition and semantic reconciliation need a capable lead.

## Whole-cycle guardrails

Estimate total cost over actual or expected calls:

`Σ(input tokens × applicable input rate + output tokens × applicable output rate + cache/tool costs, if applicable)`

Include workers, coordinators, reviews, retries, duplicated context, and handoffs. Use current provider rates only when available; do not invent prices. Keep cost, latency, and confidence separate. When a monetary budget exists, check estimated worker batch plus coordinator/review cost and retry reserve against the remaining amount. For otherwise authorized routine work when dollar data is unavailable, use explicitly bounded available model, effort, worker, round, and output allowances; label monetary cost unknown and do not block solely on missing price data. New paid external usage or experiments still require authorization and a budget. Tokens per call vary, so do not infer worker-count ratios from model names. Cheap width should add distinct evidence, not repeated guesses. No premium-model fanout without explicit approval.

## Calibration

A baseline is a reasoned starting hypothesis from task shape and model role. Empirical calibration requires matched task-class acceptance tests, comparable settings, recorded evidence, usage where available, failures, and validity checks. Prefer bounded stronger reference samples when authorized. Track first-pass acceptance, cost to accepted outcome, rework time, wall clock, review escapes, duplicated exploration, coordinator/context share, uncertainty, and source coverage. Keep raw examples and separate provider or transport failures from model quality. Worker self-confidence alone does not decide escalation or stopping.

OpenAI’s [practical guide](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/) supports establishing a capable-model accuracy baseline before testing smaller substitutions for cost and latency. Anthropic’s [multi-agent research report](https://www.anthropic.com/engineering/multi-agent-research-system) describes benefits for independent research and warns of token overhead and poor fit for shared dependencies. These are context-specific external observations, not universal local results.
