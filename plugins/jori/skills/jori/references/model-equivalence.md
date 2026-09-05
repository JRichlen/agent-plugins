# Rough task-fit equivalents across providers

**Snapshot: 2026-09-05.** This is a rough task-fit equivalents table, **not model equivalence**. It offers version-specific candidates to validate against a task's acceptance check. It does not establish quality parity, cost parity, safety parity, benchmark rank, availability, or a right to switch provider, account, or model.

Jori's Luna, Terra, Sol, and Astra names are local role baselines. A local runtime may expose a different catalog, effort range, tool set, context limit, account policy, or no external provider at all. Before any dispatch, confirm that the candidate is available, configured, and authorized in the active runtime. This guide does not make Anthropic, Google, NVIDIA, OpenRouter, or any other provider available to Codex.

This routing discipline is harness-agnostic. Reimplement it with the active harness's model-selection or fan-out primitive; do not assume that a named model, sub-agent, tool, or effort control transfers between runtimes.

## Candidate hypotheses by task shape

| Local role baseline | Use when | Anthropic candidate to validate | Google candidate to validate | Do not conclude |
| --- | --- | --- | --- | --- |
| Luna | bounded extraction, triage, summaries, or small edits | Claude Haiku 4.5 — Anthropic calls it its fastest model. | Gemini 3.5 Flash-Lite — Google calls it its fastest, most cost-effective 3.5 model for high-throughput execution. | Either is a Luna replacement, has the same latency or price, or is enabled locally. |
| Terra | balanced bounded coding | Claude Sonnet 5 — Anthropic describes it as its best combination of speed and intelligence. | Gemini 3.6 Flash — Google describes it as balancing speed and multimodal capabilities across everyday and agentic tasks. | Equivalent coding reliability, tool behavior, context, effort settings, or cost. |
| Sol | everyday analysis, implementation, and review where rework matters | Claude Opus 5 — Anthropic positions it for complex agentic coding and enterprise work. | Gemini 3.7 Flash — Google positions it for complex coding, agentic workflows, and multi-step execution. | A stronger general result on this task class without matched acceptance evidence. |
| Astra | demanding ambiguity, synthesis, or high-consequence work already authorized | Claude Fable 5.1 — Anthropic positions it for demanding reasoning and long-horizon agentic work. | Gemini 3.1 Pro Preview — Google positions it for complex problem solving and agentic/vibe coding. | Safety parity, high-consequence suitability, or that a preview model is production-approved here. |

The local OpenAI catalog publicly describes Astra for complex reasoning and coding, Terra as an intelligence/cost balance, Luna for cost-sensitive high-volume workloads, and Sol for complex professional work. That supports the local labels as useful starting roles; it does not make the rows above universal product mappings. See [OpenAI's catalog](https://developers.openai.com/api/docs/models).

## Capability, cost, latency, and runtime boundaries

Provider marketing labels are evidence about the provider's intended task fit, not measurements from this project. Keep the following decisions separate.

| Question | What the sources support | What must be verified before use |
| --- | --- | --- |
| Task fit | The candidate table records each provider's current published positioning. | A matched task-class acceptance check, including failure modes relevant to this work. |
| Cost and latency | Anthropic publishes relative latency labels for its current lineup; Google labels several Flash models as speed or high-throughput oriented. This guide makes no cross-provider price or latency comparison. | Current account pricing, rate limits, cache/tool charges, queueing, and observed end-to-end latency. |
| Effort, context, and tools | Anthropic's overview publishes model-specific effort, context, and tool support; for example, it lists Haiku 4.5's default effort as unsupported while its other current listed models use `high`. Google publishes capabilities per model page; OpenAI publishes these for its public catalog. | The exact model snapshot and API/runtime surface. A Luna `low` setting cannot be copied to Haiku 4.5 blindly. A listed capability can be disabled by an account, region, wrapper, policy, or tool configuration. |
| Authorization and dispatch | None of these sources authorizes a provider configuration change. | Choosing an already-available model inside approved task and worker allowances is routine. Changing a configured provider, account, model default, preview opt-in, or cost/authority allowance requires user authorization, then configured credentials and policy approval. |

## Source register

Use the exact model ID and lifecycle status when implementing a validated route. Provider catalogs change, previews can be retired, and aliases can move.

| Provider | Version-specific examples used above | Primary source |
| --- | --- | --- |
| OpenAI | `gpt-6-astra`, `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna` | [OpenAI model catalog](https://developers.openai.com/api/docs/models) |
| Anthropic | `claude-fable-5-1`, `claude-opus-5`, `claude-sonnet-5`, `claude-haiku-4-5-20251001` | [Anthropic models overview](https://platform.claude.com/docs/en/models/overview) and [model deprecations](https://platform.claude.com/docs/en/about-claude/model-deprecations) |
| Google | `gemini-3.5-flash-lite`, `gemini-3.6-flash`, `gemini-3.7-flash`, `gemini-3.1-pro-preview` | [Gemini model catalog](https://ai.google.dev/gemini-api/docs/models) and [version naming guidance](https://ai.google.dev/gemini-api/docs/models#model-version-name-patterns) |
| NVIDIA | `nvidia/nemotron-3.5-lightning-30b-a3b` | [NVIDIA model card](https://build.nvidia.com/nvidia/nemotron-3.5-lightning-30b-a3b/modelcard) |
| GitHub | Copilot Auto/HyDRA; Project HydraFusion research preview | [Auto model selection](https://docs.github.com/en/copilot/concepts/models/auto-model-selection), [Copilot CLI model controls](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference), [HyDRA routing](https://github.blog/ai-and-ml/github-copilot/getting-more-from-each-token-how-copilot-improves-context-handling-and-model-routing/), [HydraFusion preview](https://github.blog/ai-and-ml/github-copilot/project-hydrafusion-frontier-quality-via-multi-model-orchestration/), [models and pricing](https://docs.github.com/en/copilot/reference/copilot-billing/models-and-pricing), and [GitHub Models retirement](https://docs.github.com/en/github-models) |

### Deployment-oriented example with no Jori tier mapping

NVIDIA's dated Nemotron 3.5 Lightning card describes that specific checkpoint as suited to long-running autonomous agents, sub-agent workhorse deployments, and agentic workflows. That is a deployment-oriented candidate to validate when such a provider is available, configured, and authorized. The card does not support assigning Lightning to Luna, Terra, Sol, or Astra, or making a reasoning, safety, latency, cost, or tool-compatibility comparison.

The marketplace's behavioral fixtures currently name a different OpenRouter evaluator, `nvidia/nemotron-3-ultra-550b-a55b`. That evaluator is not a recommendation or an equivalence claim for NVIDIA Lightning; its price, availability, tool support, effort controls, and context in another runtime are **Unknown** here.

## GitHub Copilot routing

GitHub documents two distinct Hydra-named systems. Neither is a base model, an external API offered by this skill, or blanket authorization to fan out work.

| GitHub surface | What it is | Useful routing choice | Boundaries |
| --- | --- | --- | --- |
| Model picker | Direct selection of a Copilot-supported model in the current client. | Pick a named model only after checking the current client, plan, and organization policy. Copilot CLI can scope a choice to the session, repository, local settings, or future sessions. | The available list and capabilities differ by surface and policy. A picker choice is not a cross-vendor equivalence result. |
| Auto with **HyDRA** | Copilot's task-aware platform router. GitHub says HyDRA evaluates task complexity while a companion system tracks model health and availability. | Use Auto when the active Copilot surface supports it and platform-controlled selection is acceptable. GitHub reports the model used after a response. | HyDRA is not a selectable base model or documented API. It controls model choice, not Jori's explicit worker count, authority bounds, evidence, or stop conditions. |
| Project **HydraFusion** | A GitHub Copilot CLI research preview for runtime multi-model orchestration. GitHub documents Single, Cascade, and Critique patterns. | For a substantial, well-scoped first-turn coding task, enable the preview in Copilot CLI with `/experimental on`, then select `HydraFusion (Research Preview)` from `/model`, if available and authorized. | GitHub controls the underlying model/workflow legs. Per-leg model choice, hard usage caps, external API access, and availability beyond the preview instructions are **not documented as available** here. Do not represent it as Jori-managed fan-out. |
| Coding agent, code review, and Actions | Separate Copilot product surfaces with their own support, policies, and billing. | Check the surface-specific documentation before choosing a model or agent workflow. | No general Copilot model table proves that a feature, tool, or model is enabled in every surface. This guide adds no GitHub Actions model dispatch. |

Auto is generally available in Copilot Chat on the web and VS Code, Copilot CLI, Copilot cloud agent, and the GitHub Copilot app, subject to plan and policies. GitHub's current preview instructions identify HydraFusion as CLI-only through `/experimental`; do not infer that it is available in the other Auto surfaces.

GitHub's current Copilot billing docs describe input, output, and cached tokens converted to AI credits, with plan-specific included allowances and overage treatment. HydraFusion's preview says usage is based on underlying models' tokens at their standard rate. These values are not interchangeable with a direct provider API token bill. Premium-request multipliers apply only to legacy annual Pro and Pro+ request-based billing; do not use them as generic Copilot accounting. This guide does not calculate a price, allowance, or hard cap.

Copilot CLI documents `--max-ai-credits` and `/limits` as a soft per-response limit, not a hard monetary ceiling. With Auto custom agents, a subagent inherits the resolved session model even if its model field differs; an unhonorable model or effort request can fall back to the session value. Record the model actually reported after the response, not only the requested model. These are compatibility notes, not a guarantee that the active Copilot plan exposes them.

GitHub Models is separate from Copilot routing and is retired; it is not a route in this guide.

### Operational response rule for Hydra-named requests

When a user proposes a Hydra-named Copilot plan, explicitly distinguish **Auto with HyDRA** (platform model selection) from **HydraFusion** (a Copilot CLI research-preview compound workflow). Treat a requested per-leg pin or hard budget as **unverified** when the documentation does not establish that control; do not turn undocumented into impossible. Stop a plan that depends on such a pin or cap until the control is verified, or the user authorizes a revised route without it. Use only verified client syntax and billing conversions: do not invent Copilot commands, translate AI credits to a dollar guarantee, or present a direct-provider API as a proven hard-cap replacement without current evidence.

### Choosing a GitHub route

Choose an explicit Copilot model when reproducibility, a known model ID, a known effort/context setting, and direct cost inspection matter more than platform adaptation. Choose Auto with HyDRA when a configured Copilot surface is authorized to adapt among policy-allowed models for the task and current service health; record the model GitHub reports after the response. Choose HydraFusion only when multi-model execution is explicitly authorized, the Copilot CLI research preview is available, and the work is a substantial, well-scoped first-turn coding task; expect GitHub to choose its own workflow legs and assess the resulting token-to-credit usage after the run. Do not select any GitHub route when the plan, policy, model availability, or budget authority is unknown.

## Calibration rule

For a candidate that is available, configured, and authorized: hold the task class, acceptance check, input bounds, tool policy, and effort setting as comparable as the runtime allows. Record first-pass acceptance, rework, wall-clock time, token/tool use, provider failures, and cost when it is actually available. Keep the cheaper or faster candidate only when it meets the same acceptance rule. Escalate for evidence, not a name or table position.
