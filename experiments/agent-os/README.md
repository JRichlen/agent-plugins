# Agent OS design-context experiment

## Purpose

This is a small, budget-capped design experiment, not a permanent CI suite. It asks:

> What is the smallest Agent OS context that causes useful, repeatable improvement in automation design without adding semantic failures or unnecessary context?

The smoke run compares four cumulative treatments against the same six scenarios. A larger prompt does not win merely because its aggregate score is slightly higher. Experiments discover the contract; later tests may defend a contract that has earned evidence.

## Settled boundary under test

Agent OS is the design/control plane for reusable Recipes and independently triggered Automations. It is not an agent runtime and does not own Actor composition. `agent-compiler` owns compiled agents, `grill-me` owns generic interactive interrogation, and Redgate plus specialist skills remain optional working capabilities a Recipe may reference.

The canonical ontology is:

```text
Lane / Workstream / Automation / Trigger / Recipe / Adapter / Evidence
```

The experiment may refine how much of this contract belongs in the default skill context versus progressive references. It should not casually replace the boundary from one noisy aggregate.

## Layout

```text
experiments/agent-os/
  README.md
  DESIGN_EVIDENCE.md
  config.mjs             # models, budget, dimensions, and run settings
  preflight.mjs          # deterministic validation, model resolution, cost ceiling
  run.mjs                # candidate, judge, arbiter, ledger, and summaries
  scenarios.json         # candidate prompt plus hidden judge-only contract
  variants/
    baseline.md
    taxonomy.md
    recipe-aware.md
    full-agent-os.md
  results/               # generated evidence; never a source-of-truth input
```

## Treatments

Treatments are standalone and cumulative:

1. **baseline** — generic automation-design help with no Agent OS vocabulary.
2. **taxonomy** — baseline plus the seven concepts, relationships, Actor/Automation boundary, and working-discipline neutrality.
3. **recipe-aware** — taxonomy plus the detailed Recipe/Automation/Workflow/Skill/Actor composition contract.
4. **full-agent-os** — recipe-aware plus naming, `Gov`/`Meta`, three truths, reconciliation, curation, human gates, interactive composition, adapter honesty, and privacy.

The runner must preserve the exact rendered treatment text and its hash/size in the evidence manifest. The blind judge receives the scenario and candidate response, never the treatment name or treatment prompt.

## Scenario isolation

Each scenario contains:

- `prompt` — the only scenario field passed to the candidate;
- `judge.applicableDimensions` — the ten required numeric rubric dimensions, in the runner's canonical order;
- `judge.criteria` — hidden, scenario-specific anchors for 0–4 scoring;
- `judge.hardFailures` — hidden semantic failures that outweigh prose quality.

Titles, criteria, and hard failures must never be interpolated into the candidate request. In particular, the candidate does not see labels such as "Recipe vs Automation" or instructions such as "expect dependsOn". That separation keeps baseline from being taught the answer by the test itself.

The six smoke scenarios exercise reusable intent versus deployment, semantic dependencies versus clock spacing, compiled-agent reuse, working-discipline neutrality, three-truth reconciliation, and interactive curation. Every response receives a numeric 0–4 score on all ten dimensions. Each hidden criterion explains what good restraint looks like even when a dimension is not central to that scenario, so the judge never emits an `N/A` and never treats unsupported invention as harmless.

## Scoring

The blind judge scores every dimension from 0 to 4:

- taxonomy correctness
- Recipe versus Automation distinction
- dependency modeling
- ontology minimality
- reuse of existing capabilities
- working-discipline neutrality
- cross-harness honesty
- evidence awareness
- human-gated mutation
- actionability

Hard failures override style and small score gains. They include Actor/Automation identity conflation, mandatory Redgate or skill primitives, promotion of harness-native artifacts into canonical ontology, clock spacing used as dependency semantics, invented adapter capabilities, either direction of silent reconciliation overwrite, unapproved high-consequence mutation, and unsanitized private-to-public transfer.

Report the mean over all scenario/dimension cells, plus every per-scenario delta and hard-failure count. Treat the interpretation bands as research heuristics:

- less than `+0.15` over baseline: weak evidence;
- `+0.15` through `+0.35`: useful signal requiring raw-output inspection;
- greater than `+0.35`: strong signal only if repeatable and free of new hard failures.

When treatments are effectively tied, choose the smaller one. A one-sample smoke run is a signal, not proof of repeatability; confirm a consequential boundary change with targeted replication or a follow-up ablation.

## Deterministic interfaces

The intended dependency-free Node 22 interfaces are:

```sh
node experiments/agent-os/preflight.mjs --out experiments/agent-os/results
node experiments/agent-os/run.mjs --preflight experiments/agent-os/results/preflight.json
```

`config.mjs` is the single configuration source for model IDs, call limits, output ceilings, and the hard budget. `preflight.mjs` validates all source files, resolves exact OpenRouter models and pricing, enumerates the maximum call plan, estimates its conservative maximum cost, and fails before inference when the estimate exceeds the cap. Its optional `--out` selects the generated-results directory. `run.mjs` requires a successful matching preflight, accepts optional `--preflight` and `--out` paths, enforces the remaining worst-case reservation before every call, records actual `usage.cost`, and stops rather than treating missing usage or price data as zero. Without `--out`, run output is written beside the selected preflight.

The Actions workflow supplies `OPENROUTER_API_KEY` through the environment. Local deterministic validation must not require the key; live model resolution and inference do.

## Evidence artifact

A complete raw artifact should contain at least:

```text
results/
  manifest.json          # commit/run provenance, prompt hashes, model resolution, settings
  preflight.json         # model catalog matches, pricing snapshot, call plan, max estimate
  ledger.jsonl           # successful paid responses with usage.cost and cumulative spend
  calls.jsonl            # per-call role, scenario/treatment IDs, tokens, actual cost, cumulative spend
  raw/candidate/         # exact candidate request/response envelopes
  raw/candidates/        # readable candidate response text by scenario/treatment
  raw/judge/             # exact blind-judge envelopes and local validation
  raw/arbiter/           # only ambiguous/conflicting cases that used the arbiter
  aggregate.json         # scores and treatment aggregates
  scenario-deltas.json   # every treatment delta against the scenario baseline
  hard-failures.json     # grounded global and scenario-specific hard failures
  summary.md             # concise human-readable result and recommendation
```

Keep transport `FAULT` separate from semantic `FAIL`, fail closed when evidence is incomplete, and never serialize API headers or environment secrets. Raw model text is untrusted Markdown: upload it as an artifact and post only bounded, escaped summaries and representative excerpts.

## GitHub Actions bootstrap

GitHub accepts `workflow_dispatch` events only for workflow files that already exist on the default branch. Therefore a newly added `agent-os-experiments.yml` cannot dispatch itself from this unmerged PR, even when `--ref agent-os-lousy-agents-handoff` is supplied.

The existing default-branch `.github/workflows/scale.yml` can carry a narrowly named Agent OS bootstrap sentinel/input that checks out the requested PR ref and invokes this experiment. The sentinel exists only to cross that registration boundary; it is not a required check, a second experiment implementation, or permission to merge. Once the dedicated workflow exists on the default branch, retire the bootstrap path and dispatch the dedicated workflow normally.

## Reading the result

Inspect representative raw responses before changing implementation direction:

- If baseline nearly matches the instructed treatments, do not scaffold a broad default skill.
- If taxonomy captures the lift, keep the front door tiny.
- If recipe-aware captures most lift, put Recipe semantics near the front door and progressively disclose reconciliation/adapters.
- If full context helps only reconciliation or interactive curation, keep those rules in their relevant Recipes/references.
- If a larger treatment adds a hard failure, narrow it even if its aggregate rises.
- Do not infer Adapter ontology or cross-harness implementation changes from smoke scenarios that did not exercise them.

Record the accepted interpretation in `DESIGN_EVIDENCE.md`; do not turn these scenarios into required CI during the experiment.
