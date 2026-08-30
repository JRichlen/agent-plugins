# Agent OS design evidence

**Status:** Smoke and targeted all-Luna follow-up completed; treatment conclusion remains provisional

**PR:** [#83](https://github.com/JRichlen/agent-plugins/pull/83) (`agent-os-lousy-agents-handoff`)

**Evidence:** [workflow run 33281138920](https://github.com/JRichlen/agent-plugins/actions/runs/33281138920), [raw artifact 9723030558](https://github.com/JRichlen/agent-plugins/actions/runs/33281138920/artifacts/9723030558), [automatic PR summary](https://github.com/JRichlen/agent-plugins/pull/83#issuecomment-5465508778), and [learning log #85](https://github.com/JRichlen/agent-plugins/issues/85)

## Research question

What is the smallest Agent OS context that causes useful improvement in automation design without adding semantic failures or unnecessary context?

This was one deterministically configured, seeded smoke sample per scenario/treatment, not a repeatability claim. The pre-registered rule prefers the smallest treatment with at least `+0.15` mean lift, no new hard failure, and a score within `0.10` of the best qualifying treatment.

## Preflight and accounting record

| Item | Result |
|---|---|
| Source commit | `90ba2272c7bf691b0808b7581e30ee8354361b05` |
| Input fingerprint | `8d90a5e91823514bc7074531859de78438e8f8119fbcee888d80514e1700687b` |
| Preflight integrity | `cfb5584e2ccd74392f423a829f7c40520e0f80b344d25e40d77231916060a220` |
| Candidate | requested `nvidia/nemotron-3.5-lightning`; canonical slug `nvidia/nemotron-3.5-lightning-20260807`; paid DeepInfra `deepinfra/bf16` |
| Primary judge | requested `nvidia/nemotron-3-super-120b-a12b`; canonical slug `nvidia/nemotron-3-super-120b-a12b-20230311`; paid DeepInfra `deepinfra/bf16` |
| Reserved arbiter | requested `nvidia/nemotron-3-ultra-550b-a55b`; canonical slug `nvidia/nemotron-3-ultra-550b-a55b-20260604`; paid DeepInfra `deepinfra/fp4`; not used |
| Planned maximum | 24 candidates + 6 judges + at most 1 arbiter |
| Conservative maximum | `$0.044144221625` |
| Hard budget | `$0.05` |
| Actual calls | 24 candidates + 6 judges; 30/30 successful |
| Actual spend | **`$0.006922945`** (`$0.003416520` candidates + `$0.003506425` judges) |

All 30 ledger rows contain numeric OpenRouter `usage.cost`, selected DeepInfra router metadata, exact-model provenance, and matching raw request/response envelopes. The ledger sum equals `status.json`. Manifest, preflight, source, treatment, and rendered-prompt hashes were independently recomputed from the downloaded artifact.

## Blind-judge result

| Treatment | Context bytes | Mean 0–4 | Delta | Judge-emitted hard failures | Length-limited candidates | Candidate cost |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 293 | 2.9667 | — | 0 | 4/6 | `$0.000656600` |
| taxonomy | 1,696 | 3.2500 | `+0.2833` | 0 | 3/6 | `$0.000786720` |
| recipe-aware | 2,963 | 3.3000 | `+0.3333` | 0 | 2/6 | `$0.000904720` |
| full-agent-os | 4,738 | 3.3667 | `+0.4000` | 0 | 3/6 | `$0.001068480` |

The mechanical selector chose **recipe-aware**: it is only `0.0667` behind full, inside the `0.10` near-best band, while removing 1,775 context bytes. That is a useful signal, not proof.

## Scenario-level deltas

| Scenario | taxonomy | recipe-aware | full-agent-os | Interpretation |
|---|---:|---:|---:|---|
| reusable process / one deployment | `+0.4` | `+0.4` | `-0.4` | The machine judge preferred taxonomy/recipe-aware; manual review still found invented consumers and relationship errors, while full invented `native` Adapter support. |
| dependency, not clock | `0.0` | `0.0` | `0.0` | All four received exactly `3.0`; no treatment separation. |
| compiled participant reused by jobs | `+0.1` | `+0.6` | `+0.6` | Recipe-aware/full created two Automation identities; taxonomy collapsed two jobs under one Automation. |
| portable working disciplines | `+0.3` | `+0.3` | `+0.3` | Minimal taxonomy already supplied most measured lift; all outputs retained flaws. |
| desired/observed reconciliation | `0.0` | `0.0` | `0.0` | The judge collapsed all responses to `3.0`; no treatment fully satisfied truth separation, relationship semantics, evidence classification, and approval. |
| interactive portfolio curation | `+0.9` | `+0.7` | `+1.9` | Full context front-loaded `grill-me`, consent, and a proposed diff before its cutoff. This belongs in the curation Recipe/reference. |

Full's gain is concentrated: interactive curation contributes 19 of its 24 judge-awarded rubric-point improvement over baseline. Excluding that scenario, mean lift is taxonomy `+0.16`, recipe-aware `+0.26`, and full `+0.10`. Recipe-aware is positive on four scenarios, tied on two, and negative on none; full is positive on three, tied on two, and negative on one.

## Representative raw evidence

- **Recipe-aware relative identity/reuse success:** `raw/candidates/compiled-agent-reused-by-jobs/recipe-aware.md` models two independently managed Automations sharing one compiler-owned Curator artifact, with independent triggers and Evidence. Taxonomy instead makes the Curator hash one Automation with two trigger slots. The recipe-aware response still invents exact clock times and muddies Recipe versus compiled-participant binding.
- **Full-context success in the right place:** `raw/candidates/interactive-portfolio-curation/full-agent-os.md` assigns the portfolio map and domain diff to Agent OS, generic questioning/consent to `grill-me`, and ends exploration without applying changes. The required deliverable appears before the output cutoff.
- **Full-context regression:** `raw/candidates/reusable-process-deployed-check/full-agent-os.md` declares an unnamed Adapter `native`, even though the scenario provides no harness capability evidence, and scores `-0.4` versus baseline.
- **Reconciliation miss:** only full includes the sequence `propose diff -> grill -> apply approved diff`, but it calls both relationships `feeds` and does not preserve the required blocking `dependsOn`. Baseline, taxonomy, and recipe-aware direct a design-graph change without an explicit approval boundary.

## Manual audit versus judge output

`hard-failures.json` is empty, but raw review found semantic failures the primary judge described or overlooked without emitting their IDs:

- definite `independentJobsCollapsed` in compiled-participant / taxonomy;
- definite `inventedAdapterCapability` in reusable-process / full;
- strong `ungatedStructuralMutation` matches in baseline, taxonomy, and recipe-aware reconciliation responses;
- probable harness-native ontology promotion in baseline/taxonomy portable-discipline responses.

The zero in the result table therefore means **judge-emitted zero**, not independently verified zero. These misses do not overturn the recipe-aware boundary: the clearest taxonomy failure strengthens the need for Recipe/Automation deployment semantics, while the reconciliation and Adapter misses identify two compact safety rules the recipe-aware treatment lacked.

## Faults and limitations

- Twelve of 24 candidate responses ended at the 512-token ceiling: baseline 4, taxonomy 3, recipe-aware 2, full 3. Both auto-selected representative examples are truncated.
- The live judge was not told which responses ended at the output ceiling; the cutoff diagnostics were added only in the post-run harness repair.
- Seventeen of 24 responses received one repeated value across all ten dimensions, and 12 received exactly `3.0`, showing strong judge central tendency.
- Five of six validation files contain `closeScoreMargin`; the run-time policy treated those as nonblocking and used no arbiter.
- The interactive full response received ten perfect `4`s despite ending mid-next-action. Its placement of the deliverable before cutoff likely inflated the apparent full-context advantage.
- Candidate and judge were both Nemotron-family models, so correlated vocabulary/style preference is possible.
- There was one candidate and one primary judgment per cell/scenario, no repeat, no second judge, and no dedicated privacy scenario. Capability honesty was exercised only in two narrow scenario shapes.
- No transport or accounting faults occurred.

The post-run harness raises the candidate ceiling, exposes cutoff diagnostics to the judge and summary, strengthens hard-failure instructions, and sends the single close-case arbiter to the highest-consequence pre-registered scenario. Those changes require a future targeted replication; they do not rewrite this artifact.

## Implementation boundary

The evidence supports a **Recipe-aware front door with two compact safety invariants**, not the full operating contract:

1. Keep taxonomy, Recipe-versus-Automation deployment semantics, `dependsOn`/`feeds`, Actor/Automation separation, sibling capability references, and the human mutation gate immediately available.
2. State compactly that desired design and observed/live state remain separate; structural reconciliation is a proposed diff requiring approval.
3. Start every Adapter capability `unassessed`; after discovery without enough evidence, mark it `unverified`; assign a support rating only when current evidence supports it. Never infer `native` from prose or a file.
4. Progressively disclose the detailed three-truth reconciliation workflow, Adapter matrix, Gov/Meta curation model, and interactive portfolio contract through relevant references/Recipes.
5. Put the full interactive contract in `grill-my-automations`, where the only large full-context gain occurred.

No canonical ontology change is justified. A useful follow-up is a targeted `recipe-aware + compact guardrails` ablation with the repaired output/arbitration settings. Do not make this smoke a required CI gate yet.

## Targeted all-Luna follow-up

The pre-registered paired follow-up ran on [workflow 33286358010](https://github.com/JRichlen/agent-plugins/actions/runs/33286358010) with `openai/gpt-5.6-luna` as both candidate and blind judge, pinned to the standard OpenAI endpoint. It compared `recipe-aware` with `recipe-aware + compact guardrails` over six scenarios, two paired seeds per scenario, then rejudged the six immutable smoke scenarios with Luna to measure judge-family sensitivity.

### Controlled cost baseline

| Item | Actual |
|---|---:|
| Candidate generation, 24 calls | `$0.011382000004` |
| Primary judging, 6 calls | `$0.0083061` |
| Archive rejudging, 6 calls | `$0.01084685` |
| **New follow-up total, 36 calls** | **`$0.030534950004`** |
| Prompt / completion / total tokens | `53,339 / 15,154 / 68,493` |
| Paired candidate-plus-judge cost per scenario | `$0.00328135` |
| Live full-plan conservative maximum | `$0.101554589691` |
| Hard cap | `$0.50` |

The actual run used 30.07% of its conservative full-plan maximum and 6.11% of its hard cap. A `$0.50` cap therefore gave ample room for this controlled tier. The useful baseline is not merely cost per model call: the six primary judgments cost 73% as much as all 24 candidate generations, and the diagnostic archive stage contributed 35.5% of total spend. Judge prompt/output size and optional rejudging materially affect eval cost.

The artifact's `executedCallsConservativeMaximumUsd` field incorrectly reports zero because executed ledger rows omitted the pico-dollar maximum even though their dollar maximum, actual costs, and the independently recomputable full-plan maximum are intact. The harness now records both units; the historical artifact remains immutable.

### Paired result and manual interpretation

The valid negative-control and Adapter contrasts were ceiling-level ties:

| Contrast | Valid paired replicates | Mean guarded delta | W/T/L |
|---|---:|---:|---:|
| Automation identity, negative control | 4/4 | `0.0` | `0/4/0` |
| Adapter evidence, target | 4/4 | `0.0` | `0/4/0` |
| Desired/observed reconciliation, target | 0/4 | n/a | n/a |

Both reconciliation judgments were invalid, so the pre-registered selector correctly suppressed a recommendation. One Luna judgment omitted a required checklist key after emitting a duplicate JSON key; the other wrapped checklist evidence in literal quote characters while its hard-failure evidence used the exact source text. These are judge-output conformance failures, not candidate cutoffs and not evidence of either treatment winning.

Manual review of the eight reconciliation candidates finds that both arms generally preserve desired and observed state, separate dependency from artifact flow, reject performance evidence as authorization, and require human approval. The guarded arm more consistently names separate design/live diffs, capability verification, and post-change verification. The base arm already contains most of those protections, so the present prompts appear saturated near the judge's ceiling. This is a qualitative learning, not a recovered paired estimate.

The next controlled test should use strict scenario-specific structured output for judgments and reserve input budget for the schema. The harness now does that. Exact-quote grounding remains validator-enforced because JSON Schema cannot prove that a string is a substring of a candidate response. Any new paid replication still requires a separate authorization and a fresh preflight.

### Judge-family sensitivity

Only three of six archive comparisons validated. On those old candidates, Luna's mean aggregate score was lower than the original Nemotron judgment by `-0.425`, `-0.300`, and `-1.200` for reusable-process, interactive-curation, and dependency scenarios respectively. Luna also added one grounded `inventedAdapterCapability` failure. This is strong evidence that absolute scores and hard-failure detection are judge-sensitive. It does not independently validate the new ablation because Luna generated and judged the new candidates.

## Agentic trajectory calibration

[Workflow 33286362425](https://github.com/JRichlen/agent-plugins/actions/runs/33286362425) preflighted a three-scenario, low/medium/high reasoning trajectory design with up to four evidence-tool turns plus one judge call per episode. The exact standard OpenAI Luna route resolved and the 45-call conservative maximum was `$0.76118688432` under the approved `$1.00` cap.

The first request failed before a usable trajectory with HTTP 404: OpenRouter reported that no endpoint could handle the requested parameters. No ledger row or paid `usage.cost` was returned, so known actual spend is `$0`; fail-closed unresolved exposure is bounded by that one call's `$0.016915264096` maximum. The artifact did not preserve the exact failed request, which prevents a perfect post-mortem reconstruction; source and preflight preserve its deterministic shape.

OpenRouter's Responses API supports the request's reasoning-context and encrypted-reasoning fields, but `require_parameters` is documented as a Chat Completions provider-selection filter and the endpoint catalog does not enumerate several Responses gateway fields. The repaired harness keeps exact `openai` pinning, disables fallbacks, explicitly checks reasoning/tool/structured-output capability, and no longer applies that catalog filter to the Responses request. It also writes the request before dispatch and preserves HTTP error bodies and hashes. This repair is offline-tested but **not live-verified**, and no retry was attempted under the one-shot authorization.

Consequently, the realistic Agent OS trajectory cost remains unknown. Redgate should receive the same trajectory tier only after Agent OS completes one clean calibration, so the shared accounting and transport design can be reused rather than duplicating an unverified path.
