# Agent OS paired follow-up

This follow-up isolates one treatment delta: the existing `recipe-aware.md` context versus that same context plus `guardrails.md`. It uses six preregistered seam scenarios arranged as three contrast pairs and two paired seeds per treatment. The automation-identity pair is a negative control; reconciliation and Adapter evidence are the targeted pairs.

All candidate and blind primary-judge calls use exact model `openai/gpt-5.6-luna`, exact provider `OpenAI`, and exact standard endpoint tag `openai`. Flex, Fast, fallbacks, tools, web search, retries, and arbitration are disabled. Candidate and primary judge therefore share a model family and may have correlated errors. The optional archive pass compares Luna's rejudgments with the original Nemotron judgments over the exact full stored Nemotron responses from immutable Actions run `33281138920`, with content and provenance digests verified and no review re-windowing. That tests judge-family sensitivity only on the old candidates; it does not cross-validate the new Luna/Luna ablation.

The follow-up run hard cap is $0.50. The original run spent exactly $0.006922945, so the cumulative experiment cap is $0.506922945. `AGENT_OS_PRIOR_NEW_SPEND_USD` deducts prior follow-up spend, and `AGENT_OS_BUDGET_USD` may only tighten the remaining follow-up allowance. The cap is not a spend target: `cost-baseline.json`, the append-only ledger, and `summary.md` report actual token usage and cost by stage, role, and scenario after the run.

Calls are admitted in stages:

1. Price all 24 paired candidates and admit the full stage before inference.
2. Rebuild the six judge envelopes from actual candidate texts, recompute their full conservative maximum, and admit all six together only when actual stage-1 spend plus that maximum fits.
3. Admit the largest fixed-priority prefix of six archive rejudge calls that fits after actual earlier spend.

The primary numeric outcome is the guarded-minus-recipe-aware mean on each scenario's preregistered dimensions. Seeds are averaged within scenario, then the two scenarios are averaged within each contrast pair; unlike dimensions are never pooled across pairs. All ten scores remain diagnostic, and grounded hard-failure incidence is co-primary. Guardrails are selected provisionally only if both targeted pair means are at least +0.15, every targeted scenario's worst replicate is nonnegative, and the negative-control mean and worst replicate are nonnegative. This narrow follow-up supports no broad effect claim. Any paired cutoff, review truncation, invalid/ambiguous/very-low-confidence judgment, fingerprint mismatch, broken pair, or grounded hard failure in either arm suppresses automated selection for manual audit; paired hard-failure direction remains diagnostic. Archive diagnostics neither select nor suppress the new ablation.

Offline validation requires only Node.js 22:

```sh
node experiments/agent-os/follow-up/test.mjs
node experiments/agent-os/follow-up/preflight.mjs --mode ablation --validate-only
```

For `combined` or `rejudge`, also pass `--source DIR` pointing to the downloaded original artifact. A live run always consumes a fresh, integrity-bound preflight and requires `OPENROUTER_API_KEY`.

Before the new workflow exists on the default branch, dispatch `scale.yml` from this branch with `ac_sizes=agent-os-follow-up`, `agent-os-follow-up-ablation`, or `agent-os-follow-up-rejudge`; set `ac_seeds` to the PR number and `rg_runs` to the this-run budget.
