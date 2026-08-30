import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  CONFIG,
  EXPERIMENT_DIR,
  ORIGINAL_ACTUAL_SPEND_USD,
  buildCandidateMessages,
  buildJudgeMessages,
  candidateSeed,
  canonicalJson,
  deterministicCellOrder,
  effectiveNewBudgetPico,
  inputTokenUpperBound,
  judgeResponseFormat,
  judgeSeed,
  loadFollowUpInputs,
  picoToUsd,
  requestInputTokenUpperBound,
  sha256,
  usdToPico,
} from "./config.mjs";
import { loadSourceArtifact } from "./source.mjs";

export function parseArgs(argv) {
  const options = { mode: "combined", out: path.join(EXPERIMENT_DIR, "results"), source: null, validateOnly: false };
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === "--mode") options.mode = argv[++index] ?? "";
    else if (argument === "--out") options.out = path.resolve(argv[++index] ?? "");
    else if (argument === "--source") options.source = path.resolve(argv[++index] ?? "");
    else if (argument === "--validate-only") options.validateOnly = true;
    else if (argument === "--help") {
      console.log("usage: node experiments/agent-os/follow-up/preflight.mjs [--mode combined|ablation|rejudge] [--source DIR] [--out DIR] [--validate-only]");
      process.exit(0);
    } else throw new Error(`unknown argument: ${argument}`);
  }
  if (!new Set(["combined", "ablation", "rejudge"]).has(options.mode)) throw new Error("--mode must be combined, ablation, or rejudge");
  if (!options.out) throw new Error("--out requires a directory");
  if (options.mode !== "ablation" && !options.source) throw new Error(`--source is required for ${options.mode} mode`);
  return options;
}

async function fetchJson(url, apiKey) {
  const response = await fetch(url, { headers: { Authorization: `Bearer ${apiKey}`, Accept: "application/json" }, signal: AbortSignal.timeout(45_000) });
  const text = await response.text();
  let body;
  try {
    body = JSON.parse(text);
  } catch {
    throw new Error(`OpenRouter returned non-JSON for ${url} (HTTP ${response.status})`);
  }
  if (!response.ok) throw new Error(`OpenRouter resolution failed for ${url} (HTTP ${response.status}): ${body?.error?.message ?? text}`);
  return body;
}

function splitModelId(model) {
  const slash = model.indexOf("/");
  if (slash <= 0 || slash === model.length - 1) throw new Error(`invalid exact model id: ${model}`);
  return [model.slice(0, slash), model.slice(slash + 1)];
}

function pricePico(pricing, key) {
  return usdToPico(pricing?.[key] ?? "0");
}

function maximumInputUnitPrice(pricing) {
  return ["prompt", "input_cache_read", "input_cache_write"].map((key) => pricePico(pricing, key)).reduce((maximum, value) => (value > maximum ? value : maximum), 0n);
}

function callMaximumPico(endpoint, inputUpperTokens, maxOutputTokens) {
  return pricePico(endpoint.pricing, "request") + BigInt(inputUpperTokens) * maximumInputUnitPrice(endpoint.pricing) + BigInt(maxOutputTokens) * pricePico(endpoint.pricing, "completion");
}

export function routedCallMaximumPico(maxPrice, inputUpperTokens, maxOutputTokens) {
  const promptPicoPerToken = usdToPico(Number(maxPrice.prompt) / 1_000_000);
  const completionPicoPerToken = usdToPico(Number(maxPrice.completion) / 1_000_000);
  return usdToPico(maxPrice.request ?? 0) + BigInt(inputUpperTokens) * promptPicoPerToken + BigInt(maxOutputTokens) * completionPicoPerToken;
}

export function providerMaxPrice(endpoint) {
  const result = {};
  for (const key of ["prompt", "completion", "request"]) {
    const raw = endpoint.pricing?.[key] ?? "0";
    const catalogPico = pricePico(endpoint.pricing, key);
    if (!Number.isFinite(Number(raw)) || Number(raw) < 0) throw new Error(`invalid ${key} price on ${endpoint.name}`);
    result[key] = key === "request" ? Number(picoToUsd(catalogPico)) : Number(picoToUsd(catalogPico * 1_000_000n + 1_000n));
  }
  return result;
}

function endpointEligible(endpoint, roleConfig) {
  if (endpoint.provider_name !== roleConfig.providerName || endpoint.tag !== roleConfig.endpointTag || endpoint.status !== 0) return false;
  if (Number(endpoint.pricing?.prompt ?? 0) <= 0 || Number(endpoint.pricing?.completion ?? 0) <= 0) return false;
  if (Number(endpoint.max_prompt_tokens ?? endpoint.context_length ?? 0) < roleConfig.maxInputUpperTokens) return false;
  if (Number(endpoint.max_completion_tokens ?? 0) < roleConfig.maxTokens) return false;
  const supported = new Set(endpoint.supported_parameters ?? []);
  if (!roleConfig.requiredParameters.every((parameter) => supported.has(parameter))) return false;
  // Luna publishes a web-search tool price, but every request body in this
  // dependency-free harness is structurally tool-free. All other unknown
  // positive categories remain ineligible.
  const uncapped = Object.entries(endpoint.pricing ?? {}).filter(([key, value]) => !["prompt", "completion", "request", "input_cache_read", "input_cache_write", "discount", "web_search"].includes(key) && Number(value ?? 0) > 0);
  const cacheCharges = ["input_cache_read", "input_cache_write"].some((key) => Number(endpoint.pricing?.[key] ?? 0) > 0);
  if (uncapped.length || (cacheCharges && endpoint.supports_implicit_caching !== false)) return false;
  return true;
}

async function resolveRole(role, roleConfig, apiKey, rawDir) {
  if (roleConfig.model.endsWith(":free")) throw new Error(`${role} model must be a paid exact ID`);
  const [author, slug] = splitModelId(roleConfig.model);
  const modelUrl = `${CONFIG.apiBase}/model/${encodeURIComponent(author)}/${encodeURIComponent(slug)}`;
  const endpointsUrl = `${CONFIG.apiBase}/models/${encodeURIComponent(author)}/${encodeURIComponent(slug)}/endpoints`;
  const [modelEnvelope, endpointsEnvelope] = await Promise.all([fetchJson(modelUrl, apiKey), fetchJson(endpointsUrl, apiKey)]);
  await Promise.all([
    writeFile(path.join(rawDir, `${role}-model.json`), `${JSON.stringify(modelEnvelope, null, 2)}\n`),
    writeFile(path.join(rawDir, `${role}-endpoints.json`), `${JSON.stringify(endpointsEnvelope, null, 2)}\n`),
  ]);
  const model = modelEnvelope?.data;
  const endpointModel = endpointsEnvelope?.data;
  if (model?.id !== roleConfig.model || endpointModel?.id !== roleConfig.model) throw new Error(`${role}: OpenRouter did not resolve exact model ${roleConfig.model}`);
  const eligible = (endpointModel.endpoints ?? []).filter((endpoint) => endpointEligible(endpoint, roleConfig));
  if (eligible.length !== 1) {
    throw new Error(`${role}: expected exactly one healthy ${roleConfig.providerName} endpoint tagged ${roleConfig.endpointTag}; found ${eligible.length}`);
  }
  const selected = eligible[0];
  const supportedParameters = [...new Set(selected.supported_parameters ?? [])].sort();
  const resolution = {
    role,
    requestedModel: roleConfig.model,
    resolvedModel: model.id,
    canonicalSlug: model.canonical_slug ?? model.id,
    endpoint: {
      name: selected.name,
      providerName: selected.provider_name,
      tag: selected.tag,
      quantization: selected.quantization ?? null,
      contextLength: selected.context_length,
      maxPromptTokens: selected.max_prompt_tokens,
      maxCompletionTokens: selected.max_completion_tokens,
      pricing: selected.pricing,
      supportsImplicitCaching: selected.supports_implicit_caching ?? null,
      supportedParameters,
    },
    seedSupported: supportedParameters.includes("seed"),
    providerRouting: { only: [selected.tag], order: [selected.tag], allow_fallbacks: false, require_parameters: true, max_price: providerMaxPrice(selected) },
  };
  if (!resolution.seedSupported) throw new Error(`${role}: paired design requires endpoint seed support`);
  if (["candidate", "primaryJudge", "rejudge"].includes(role) && (selected.tag !== "openai" || roleConfig.requiredParameters.includes("temperature"))) {
    throw new Error(`${role}: Luna must use the standard openai endpoint without a temperature requirement`);
  }
  return resolution;
}

export function buildAblationPlan(inputs) {
  const calls = [];
  const candidateByKey = new Map();
  inputs.scenarios.forEach((scenario, scenarioIndex) => {
    for (const cell of deterministicCellOrder(scenarioIndex)) {
      const treatment = inputs.treatments.find((item) => item.id === cell.treatmentId);
      const messages = buildCandidateMessages(scenario, treatment.text);
      const inputUpperTokens = inputTokenUpperBound(messages);
      if (inputUpperTokens > CONFIG.roles.candidate.maxInputUpperTokens) throw new Error(`candidate prompt ${scenario.id}/${treatment.id} exceeds ${CONFIG.roles.candidate.maxInputUpperTokens}`);
      const id = `candidate:${scenario.id}:${treatment.id}:seed-${cell.replicateIndex + 1}`;
      const call = { id, stage: 1, phase: "candidate", role: "candidate", scenarioId: scenario.id, treatmentId: treatment.id, replicateIndex: cell.replicateIndex, inputUpperTokens, maxOutputTokens: CONFIG.roles.candidate.maxTokens, seed: candidateSeed(scenarioIndex, cell.replicateIndex) };
      calls.push(call);
      candidateByKey.set(`${scenario.id}:${treatment.id}:${cell.replicateIndex}`, id);
    }
  });
  inputs.scenarios.forEach((scenario, scenarioIndex) => {
    const blinded = deterministicCellOrder(scenarioIndex).map((cell, index) => ({
      blindId: `R${index + 1}`,
      candidateCallId: candidateByKey.get(`${scenario.id}:${cell.treatmentId}:${cell.replicateIndex}`),
      content: "\\".repeat(CONFIG.candidateReviewBytes),
      lengthLimited: false,
      truncated: false,
    }));
    const judgeMessages = buildJudgeMessages(scenario, blinded);
    const responseFormat = judgeResponseFormat(scenario, blinded.map((item) => item.blindId));
    const inputUpperTokens = requestInputTokenUpperBound(judgeMessages, responseFormat);
    if (inputUpperTokens > CONFIG.roles.primaryJudge.maxInputUpperTokens) throw new Error(`primary judge prompt ${scenario.id} upper bound ${inputUpperTokens} exceeds cap`);
    calls.push({
      id: `primary-judge:${scenario.id}`,
      stage: 2,
      phase: "primary-judge",
      role: "primaryJudge",
      scenarioId: scenario.id,
      blinded: blinded.map(({ blindId, candidateCallId }) => ({ blindId, candidateCallId })),
      inputUpperTokens,
      maxOutputTokens: CONFIG.roles.primaryJudge.maxTokens,
      seed: judgeSeed(scenarioIndex, "primaryJudge"),
    });
  });
  return calls;
}

export function buildRejudgePlan(source) {
  return source.scenarios.map(({ scenario, responses }, index) => {
    const blinded = responses.map((response) => ({ blindId: response.blindId, content: response.content, lengthLimited: response.finishReason === "length", truncated: false }));
    const judgeMessages = buildJudgeMessages(scenario, blinded);
    const responseFormat = judgeResponseFormat(scenario, blinded.map((item) => item.blindId));
    const inputUpperTokens = requestInputTokenUpperBound(judgeMessages, responseFormat);
    if (inputUpperTokens > CONFIG.roles.rejudge.maxInputUpperTokens) throw new Error(`archive rejudge prompt ${scenario.id} upper bound ${inputUpperTokens} exceeds cap`);
    return {
      id: `rejudge:${scenario.id}`,
      stage: 3,
      phase: "rejudge",
      role: "rejudge",
      scenarioId: scenario.id,
      rejudgePriority: scenario.rejudgePriority,
      sourceResponseDigests: responses.map((response) => ({ blindId: response.blindId, candidateCallId: response.candidateCallId, contentSha256: response.contentSha256, contentBytes: response.contentBytes, finishReason: response.finishReason })),
      inputUpperTokens,
      maxOutputTokens: CONFIG.roles.rejudge.maxTokens,
      seed: judgeSeed(index, "rejudge"),
    };
  });
}

function decorateCosts(calls, resolutions) {
  const byRole = Object.fromEntries(resolutions.map((resolution) => [resolution.role, resolution]));
  return calls.map((call) => {
    const resolution = byRole[call.role];
    if (!resolution) throw new Error(`missing model resolution for ${call.role}`);
    const maximum = routedCallMaximumPico(resolution.providerRouting.max_price, call.inputUpperTokens, call.maxOutputTokens);
    return { ...call, maximumCostPicoUsd: maximum.toString(), maximumCostUsd: picoToUsd(maximum) };
  });
}

export function buildStages(calls, budgetPico) {
  const definitions = [
    { id: "paired-candidates", stage: 1, admission: "admit full stage before its first call" },
    { id: "primary-judges", stage: 2, admission: "conditional: actual prior spend plus full stage maximum must fit" },
    { id: "archive-rejudge", stage: 3, admission: "conditional: largest fixed-priority prefix whose maximum plus actual prior spend fits" },
  ];
  const stages = definitions
    .map((definition) => {
      const stageCalls = calls.filter((call) => call.stage === definition.stage);
      const maximumPico = stageCalls.reduce((sum, call) => sum + BigInt(call.maximumCostPicoUsd), 0n);
      return { ...definition, callIds: stageCalls.map((call) => call.id), callCount: stageCalls.length, maximumCostPicoUsd: maximumPico.toString(), maximumCostUsd: picoToUsd(maximumPico) };
    })
    .filter((stage) => stage.callCount > 0);
  const errors = [];
  for (const stage of stages.filter((item) => item.stage < 3)) {
    if (BigInt(stage.maximumCostPicoUsd) > budgetPico) errors.push(`${stage.id} full-stage maximum $${stage.maximumCostUsd} exceeds effective budget $${picoToUsd(budgetPico)}`);
  }
  const archive = stages.find((item) => item.stage === 3);
  if (archive) {
    const first = calls.filter((call) => call.stage === 3).sort((left, right) => left.rejudgePriority - right.rejudgePriority)[0];
    if (!first || BigInt(first.maximumCostPicoUsd) > budgetPico) errors.push("effective budget cannot fit the highest-priority archive rejudge call");
  }
  return { stages, errors };
}

function renderPreflight(preflight) {
  const routes = preflight.modelResolutions.map((item) => `| ${item.role} | \`${item.resolvedModel}\` | ${item.endpoint.providerName} / \`${item.endpoint.tag}\` | ${item.endpoint.pricing.prompt} | ${item.endpoint.pricing.completion} |`).join("\n");
  return `# Agent OS follow-up preflight

- Status: **${preflight.status.toUpperCase()}**
- Mode: **${preflight.mode}**
- Calls enumerated: ${preflight.counts.candidates} paired candidates, ${preflight.counts.primaryJudges} blind Luna primary judges, ${preflight.counts.requestedRejudges} archive rejudges
- New-run actual hard ceiling: **$${preflight.effectiveBudgetUsd}**
- Prior paid experiment: **$${preflight.originalActualSpendUsd}**
- Prior follow-up spend supplied by caller: **$${preflight.priorNewSpendUsd}**
- Cumulative actual hard ceiling: **$${preflight.cumulativeActualHardCeilingUsd}** of **$${CONFIG.overallHardCapUsd}**

${preflight.stages.map((stage) => `- Stage ${stage.stage} (${stage.id}): ${stage.callCount} calls, full-stage maximum **$${stage.maximumCostUsd}**; ${stage.admission}.`).join("\n")}

| Role | Exact model | Exact pinned endpoint | Prompt $/token | Completion $/token |
|---|---|---|---:|---:|
${routes}

Later stage maxima are not summed with earlier maxima: the runner admits a later stage only against actual prior spend. The 24 paired candidates are stage 1, the six four-response blind Luna judgments are stage 2, and a fixed-priority prefix of immutable archive rejudges is stage 3. Every Luna request is pinned to endpoint tag \`openai\`; Flex and Fast are not eligible. Requests contain no tools, so the published web-search charge is structurally unreachable. No fallback or arbiter is allowed. Candidate and primary judge share a model family, so their errors may be correlated. Comparing Luna's archive judgments with the original Nemotron judgments tests judge-family sensitivity only on the old candidates; it does not cross-validate the new Luna/Luna ablation.
`;
}

export async function runPreflight(options = parseArgs(process.argv.slice(2))) {
  const inputs = await loadFollowUpInputs();
  const source = options.mode === "ablation" ? null : await loadSourceArtifact(options.source);
  const ablationWithoutCosts = options.mode === "rejudge" ? [] : buildAblationPlan(inputs);
  const rejudgeWithoutCosts = options.mode === "ablation" ? [] : buildRejudgePlan(source);
  if (options.validateOnly) {
    console.log(`validated follow-up ${options.mode}: ${ablationWithoutCosts.length} ablation slots, ${rejudgeWithoutCosts.length} immutable rejudge slots`);
    return { inputs, source, calls: [...ablationWithoutCosts, ...rejudgeWithoutCosts] };
  }
  const apiKey = process.env.OPENROUTER_API_KEY;
  if (!apiKey) throw new Error("OPENROUTER_API_KEY is required for live model resolution");
  await mkdir(options.out, { recursive: true });
  const rawDir = path.join(options.out, "raw", "model-resolution");
  await mkdir(rawDir, { recursive: true });
  const roles = options.mode === "ablation" ? ["candidate", "primaryJudge"] : options.mode === "rejudge" ? ["rejudge"] : ["candidate", "primaryJudge", "rejudge"];
  const modelResolutions = [];
  for (const role of roles) modelResolutions.push(await resolveRole(role, CONFIG.roles[role], apiKey, rawDir));
  const ablationCalls = decorateCosts(ablationWithoutCosts, modelResolutions);
  const rejudgeCalls = decorateCosts(rejudgeWithoutCosts, modelResolutions);
  const budget = effectiveNewBudgetPico();
  const calls = [...ablationCalls, ...rejudgeCalls];
  const stagePlan = buildStages(calls, budget.budgetPico);
  const originalPico = usdToPico(ORIGINAL_ACTUAL_SPEND_USD);
  const cumulativeActualHardCeilingPico = originalPico + budget.priorNewSpendPico + budget.budgetPico;
  const passed = stagePlan.errors.length === 0 && cumulativeActualHardCeilingPico <= usdToPico(CONFIG.overallHardCapUsd);
  const generatedAt = new Date().toISOString();
  const inputFingerprint = sha256(canonicalJson({ followUp: inputs.fingerprint, mode: options.mode, source: source?.lineage.importedDigest ?? null }));
  const core = {
    schemaVersion: CONFIG.schemaVersion,
    status: passed ? "pass" : "fail",
    mode: options.mode,
    inputFingerprint,
    followUpFingerprint: inputs.fingerprint,
    sourceLineage: source?.lineage ?? null,
    originalActualSpendUsd: ORIGINAL_ACTUAL_SPEND_USD,
    priorNewSpendPicoUsd: budget.priorNewSpendPico.toString(),
    priorNewSpendUsd: picoToUsd(budget.priorNewSpendPico),
    effectiveBudgetPicoUsd: budget.budgetPico.toString(),
    effectiveBudgetUsd: picoToUsd(budget.budgetPico),
    cumulativeActualHardCeilingPicoUsd: cumulativeActualHardCeilingPico.toString(),
    cumulativeActualHardCeilingUsd: picoToUsd(cumulativeActualHardCeilingPico),
    modelResolutions,
    calls,
    stages: stagePlan.stages,
    validationErrors: stagePlan.errors,
    counts: {
      candidates: calls.filter((call) => call.phase === "candidate").length,
      primaryJudges: calls.filter((call) => call.phase === "primary-judge").length,
      requestedRejudges: rejudgeCalls.length,
      maximumTotal: calls.length,
    },
    generatedAt,
  };
  const preflight = { ...core, integrity: sha256(canonicalJson(core)) };
  await Promise.all([
    writeFile(path.join(options.out, "preflight.json"), `${JSON.stringify(preflight, null, 2)}\n`),
    writeFile(path.join(options.out, "preflight.md"), renderPreflight(preflight)),
  ]);
  if (!passed) throw new Error(stagePlan.errors.join("; ") || `cumulative hard ceiling $${picoToUsd(cumulativeActualHardCeilingPico)} exceeds $${CONFIG.overallHardCapUsd}`);
  console.log(`follow-up preflight PASS: ${calls.length} calls priced; later stages are admitted against actual spend; cumulative hard ceiling $${preflight.cumulativeActualHardCeilingUsd}`);
  return preflight;
}

const isMain = process.argv[1] && path.resolve(process.argv[1]) === path.resolve(fileURLToPath(import.meta.url));
if (isMain) runPreflight().catch((error) => { console.error(`follow-up preflight FAIL: ${error.message}`); process.exitCode = 1; });
