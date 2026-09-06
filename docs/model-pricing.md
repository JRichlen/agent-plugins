# OpenRouter price monitoring and staged strategy

`model-pricing.yml` can check public endpoint metadata daily at 13:25 UTC,
then ask a bounded GLM agent to propose a strategy only after a material change.
It ships **disabled**, with the agent disabled and both spending allowances zero.
Adding the workflow does not authorize recurring model calls.

The output is a GitHub Actions artifact containing price evidence, a structured
recommendation, and an allowlisted config-change plan. It does **not** create a
pull request, edit active model settings, run calibration, or merge changes.
Download `model-pricing-<run-id>` from the run; an actionable change also appears
in its job summary. Unchanged scans produce no summary or external message.
Artifacts expire after 90 days; download proposals worth retaining.

## What it watches

`ci/model-pricing/policy.json` lists five subject candidates and a separate
Sonnet 5 judge price watch. New catalog models are not discovered automatically;
adding candidates requires a reviewed policy change. Each route keeps provider
tag, tier, quantization, context length, text/cache rates, conditions, and its
exact endpoint source. No endpoint fallback or tier is treated as equivalent.

The held token mix is 496,085 input and 164,797 output tokens, with no assumed
cache hits: a historical subject-only illustration, not a monthly forecast or
invoice. Explicit discounts are retained without applying them again. Unknown
metering or conditions suppress comparable cost estimates. Provider telemetry
is not used as proof of reliability. The Sonnet watch records OpenRouter rate
changes only: the real judge uses direct Anthropic, its workload is separate,
and the monitor has no authority to replace it or use subject self-grading.

Added/removed routes and changed conditions/capabilities require review. A
comparable held-mix price change requires both 15% and $0.02; the comparison
baseline stays fixed through smaller moves, so cumulative changes count.
Unknown-condition rate changes and judge rate changes trigger review without
inventing savings. The agent gets a bounded sample of source rows; the complete
snapshot is retained in the artifact. Sampling is not a quality ranking.

## Activation, only after approval

1. Review this policy and create the state branch **once**, before enabling the
   monitor. In a new temporary clone with no existing state branch or history,
   create orphan branch `automation/model-pricing-state`, clear its index, copy
   `ci/model-pricing/initial-state.json` from the reviewed default branch as
   `state.json`, commit that single file, and push the state branch. First verify
   it has never held a ledger. If it existed, restore its history instead; never
   initialize an empty replacement to regain monthly allowance. Do not run
   orphan/index-cleanup commands in a working checkout with user changes.
2. Set repository variable `OPENROUTER_PRICE_MONITOR_ENABLED=true`. Scheduled or
   manual dispatches from the default branch now scan public metadata only.
   The first valid scan establishes a baseline without an agent call. Feature
   branch dispatches and pull requests cannot enter the monitor job.
3. For automatic strategy on subsequent material changes, separately approve
   and commit `agent.enabled=true`, `per_run_usd=0.05`, `monthly_usd=1`, and one
   exact supported GLM endpoint tag in `agent.provider`. These are proposed
   ceilings, not enabled defaults. The implementation refuses larger values.
   Keep GLM `max` reasoning, at most 4,096 generated tokens and 32,768 input
   bytes, and rate ceilings $0.10 input/$0.40 output per million tokens.
4. Supply a **dedicated** OpenRouter key as `PRICE_STRATEGY_KEY`, restricted to
   a monthly limit no higher than $1 including BYOK usage. Do not reuse the
   general CI key. The read-only key preflight must confirm monthly reset,
   positive limit within policy, and remaining allowance for the full run.
   Creating/changing this key or its permissions needs separate authorization.
   A manual dispatch follows exactly the same budget and dedupe rules.

Disable the repository variable to stop scans, or set `agent.enabled=false`
to retain metadata monitoring without inference. The workflow never changes
these controls itself. GitHub schedules can be delayed; this is daily polling,
not continuous monitoring or guaranteed delivery.

## Budget and failure handling

The state branch stores snapshots, a pending evidence fingerprint, and an
append-only reservation ledger. A single workflow concurrency group plus
non-force pushes serialize updates. The full per-run allowance is committed
and pushed **before** the one model request. Every attempt retains that entire
reservation for its UTC calendar month, including successful calls. A rerun,
duplicate fingerprint, missing ledger, stale feed, rejected push, or exhausted
monthly allowance cannot silently retry or reset it. No expiring cache holds
the budget. Unknown usage retains the reservation and stops the strategy stage.

The controller pins one provider, disables fallbacks, requires advertised
parameters, sends `max_price` ceilings, bounds input/output, and verifies the
reported usage cost. Its conservative token-rate envelope and durable
reservations are operational limits, **not an invoice guarantee**; the dedicated
provider key limit is a separate account control. OpenRouter fees, billing
timing and tokenization require account-level reconciliation. No automatic
refund, key-limit increase, or monthly ledger reset is implemented.

The analyst has no tools. Schema validation accepts only cited route IDs,
allowlisted subjects, and hold/validate/stage decisions; it rejects URLs and
credential-shaped output. Its plan can refer only to the three existing subject
config paths and is marked `apply:false`. Correct citations do not prove sound
reasoning or model quality. Every proposed subject change still needs existing
Jori real/control cases, routing and trajectory contracts, independent judging,
an approved calibration budget, and human review. Thresholds stay unchanged.

Public feeds and model output are untrusted data. HTTP errors are reported as
sanitized statuses without bodies or credential-bearing URLs. No raw model
response, key response, or secret is uploaded. Failed evidence never replaces
the baseline. If state is lost, recover the original branch/history and
reconcile the dedicated key before resuming; do not rerun to bypass a fault.

## Validation and sources

Run `python3 ci/model-pricing/test_monitor.py` and `evals/cheap/run.sh` offline.
Tests cover normalization, material changes, freshness, reservations, dedupe,
and proposal constraints, including rejection fixtures and a budget-guard
mutation. They do not prove live GitHub scheduling/authentication, OpenRouter
enforcement, agent output quality, or realized savings. No paid monitor call is
required merely to add this default-off capability.

Primary protocol references: [endpoint inventory](https://openrouter.ai/docs/api/api-reference/endpoints/list-all-endpoints-for-a-model),
[provider controls](https://openrouter.ai/docs/guides/routing/provider-selection),
and [current-key limits](https://openrouter.ai/docs/api/api-reference/api-keys/get-current-api-key).
The monitor reads only the public inventory and the dedicated key's own limits;
it does not administer keys or accounts.
