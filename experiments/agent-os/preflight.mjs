import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  CONFIG,
  EXPERIMENT_DIR,
  buildArbiterMessages,
  buildCandidateMessages,
  buildJudgeMessages,
  canonicalJson,
  deterministicVariantOrder,
  effectiveBudgetPico,
  inputTokenUpperBound,
  loadExperimentInputs,
  picoToUsd,
  seedFor,
  sha256,
  usdToPico,
} from "./config.mjs";

function parseArgs(argv) {
  const options = { out: path.join(EXPERIMENT_DIR, "results"), validateOnly: false };
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === "--out") options.out = path.resolve(argv[++index] ?? "");
    else if (argument === "--validate-only") options.validateOnly = true;
    else if (argument === "--help") {
      console.log("usage: node experiments/agent-os/preflight.mjs [--out DIR] [--validate-only]");
      process.exit(0);
    } else throw new Error(`unknown argument: ${argument}`);
  }
  if (!options.out) throw new Error("--out requires a directory");
  return options;
}

async function fetchJson(url, apiKey) {
  const response = await fetch(url, {
    headers: { Authorization: `Bearer ${apiKey}`, Accept: "application/json" },
    signal: AbortSignal.timeout(45_000),
  });
  const text = await response.text();
  let body;
  try {
    body = JSON.parse(text);
  } catch {
    throw new Error(`OpenRouter returned non-JSON for ${url} (HTTP ${response.status})`);
  }
  if (!response.ok) {
    throw new Error(`OpenRouter resolution failed for ${url} (HTTP ${response.status}): ${body?.error?.message ?? text}`);
  }
  return body;
}

function splitModelId(model) {
  const slash = model.indexOf("/");
  if (slash <= 0 || slash === model.length - 1) throw new Error(`invalid exact model id: ${model}`);
  return [model.slice(0, slash), model.slice(slash + 1)];
}

function pricePico(pricing, key) {
  const value = pricing?.[key] ?? "0";
  return usdToPico(value);
}

function maximumInputUnitPrice(pricing) {
  return ["prompt", "input_cache_read", "input_cache_write"]
    .map((key) => pricePico(pricing, key))
    .reduce((maximum, value) => (value > maximum ? value : maximum), 0n);
}

function maximumOutputUnitPrice(pricing) {
  return pricePico(pricing, "completion");
}

function callMaximumPico(endpoint, inputUpperTokens, maxOutputTokens) {
  return (
    pricePico(endpoint.pricing, "request") +
    BigInt(inputUpperTokens) * maximumInputUnitPrice(endpoint.pricing) +
    BigInt(maxOutputTokens) * maximumOutputUnitPrice(endpoint.pricing)
  );
}

function routedCallMaximumPico(maxPrice, inputUpperTokens, maxOutputTokens) {
  // max_price token fields are USD per million tokens. Convert each routed
  // ceiling back to a per-token pico-USD value and round upward.
  const promptPicoPerToken = usdToPico(Number(maxPrice.prompt) / 1_000_000);
  const completionPicoPerToken = usdToPico(Number(maxPrice.completion) / 1_000_000);
  return (
    usdToPico(maxPrice.request ?? 0) +
    BigInt(inputUpperTokens) * promptPicoPerToken +
    BigInt(maxOutputTokens) * completionPicoPerToken
  );
}

function providerMaxPrice(endpoint) {
  const result = {};
  for (const key of ["prompt", "completion", "request"]) {
    const raw = endpoint.pricing?.[key] ?? "0";
    const catalogPico = pricePico(endpoint.pricing, key);
    if (!Number.isFinite(Number(raw)) || Number(raw) < 0) throw new Error(`invalid ${key} price on ${endpoint.name}`);
    if (key === "request") {
      result.request = Number(picoToUsd(catalogPico));
    } else {
      // Converting a tiny per-token price with Number(raw) * 1e6 can serialize
      // below the catalog decimal (for example 0.085 -> 0.08499999...). Build
      // from integer pico-USD and add a one-nanodollar-per-million serialization
      // cushion. The call envelope below is calculated from this sent ceiling.
      const routedCeilingPicoPerMillion = catalogPico * 1_000_000n + 1_000n;
      result[key] = Number(picoToUsd(routedCeilingPicoPerMillion));
    }
  }
  return result;
}

function endpointEligible(endpoint, roleConfig) {
  if (endpoint.provider_name !== roleConfig.providerName || endpoint.status !== 0) return false;
  if (typeof endpoint.tag !== "string" || !endpoint.tag) return false;
  if (Number(endpoint.pricing?.prompt ?? 0) <= 0 || Number(endpoint.pricing?.completion ?? 0) <= 0) return false;
  if (Number(endpoint.max_prompt_tokens ?? endpoint.context_length ?? 0) < roleConfig.maxInputUpperTokens) return false;
  if (Number(endpoint.max_completion_tokens ?? 0) < roleConfig.maxTokens) return false;
  const parameters = new Set(endpoint.supported_parameters ?? []);
  if (!roleConfig.requiredParameters.every((parameter) => parameters.has(parameter))) return false;
  // OpenRouter's max_price routing guard covers prompt, completion, and request
  // prices. Reject any endpoint with another positive billable category so the
  // preflight envelope and router price ceiling cover every possible charge.
  const uncappedCharges = Object.entries(endpoint.pricing ?? {}).filter(
    ([key, value]) =>
      !["prompt", "completion", "request", "input_cache_read", "input_cache_write"].includes(key) &&
      Number(value ?? 0) > 0,
  );
  const cacheCharges = ["input_cache_read", "input_cache_write"].some(
    (key) => Number(endpoint.pricing?.[key] ?? 0) > 0,
  );
  // We send no cache directives. A published cache price is acceptable only
  // when the route explicitly says it does not cache implicitly.
  if (cacheCharges && endpoint.supports_implicit_caching !== false) return false;
  return uncappedCharges.length === 0;
}

async function resolveRole(role, roleConfig, apiKey, rawDir) {
  if (roleConfig.model.endsWith(":free")) throw new Error(`${role} model must be a paid exact id`);
  const [author, slug] = splitModelId(roleConfig.model);
  const modelUrl = `${CONFIG.apiBase}/model/${encodeURIComponent(author)}/${encodeURIComponent(slug)}`;
  const endpointsUrl = `${CONFIG.apiBase}/models/${encodeURIComponent(author)}/${encodeURIComponent(slug)}/endpoints`;
  const [modelEnvelope, endpointsEnvelope] = await Promise.all([
    fetchJson(modelUrl, apiKey),
    fetchJson(endpointsUrl, apiKey),
  ]);

  await Promise.all([
    writeFile(path.join(rawDir, `${role}-model.json`), `${JSON.stringify(modelEnvelope, null, 2)}\n`),
    writeFile(path.join(rawDir, `${role}-endpoints.json`), `${JSON.stringify(endpointsEnvelope, null, 2)}\n`),
  ]);

  const model = modelEnvelope?.data;
  const endpointModel = endpointsEnvelope?.data;
  if (model?.id !== roleConfig.model || endpointModel?.id !== roleConfig.model) {
    throw new Error(`${role}: OpenRouter did not resolve the exact configured id ${roleConfig.model}`);
  }
  const endpoints = (endpointModel.endpoints ?? []).filter((endpoint) => endpointEligible(endpoint, roleConfig));
  if (!endpoints.length) {
    throw new Error(
      `${role}: no healthy paid ${roleConfig.providerName} endpoint supports ${roleConfig.requiredParameters.join(", ")}`,
    );
  }
  endpoints.sort((left, right) => {
    const leftCost = callMaximumPico(left, roleConfig.maxInputUpperTokens, roleConfig.maxTokens);
    const rightCost = callMaximumPico(right, roleConfig.maxInputUpperTokens, roleConfig.maxTokens);
    if (leftCost !== rightCost) return leftCost < rightCost ? -1 : 1;
    return left.tag < right.tag ? -1 : left.tag > right.tag ? 1 : 0;
  });
  const selected = endpoints[0];
  const supportedParameters = [...new Set(selected.supported_parameters ?? [])].sort();
  return {
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
    providerRouting: {
      only: [selected.tag],
      order: [selected.tag],
      allow_fallbacks: false,
      require_parameters: true,
      max_price: providerMaxPrice(selected),
    },
  };
}

function buildCallPlan(inputs) {
  const calls = [];
  const candidateByKey = new Map();

  inputs.scenarios.forEach((scenario, scenarioIndex) => {
    const order = deterministicVariantOrder(scenarioIndex);
    for (const variantId of order) {
      const variant = inputs.variants.find((item) => item.id === variantId);
      const messages = buildCandidateMessages(scenario, variant.text);
      const inputUpperTokens = inputTokenUpperBound(messages);
      if (inputUpperTokens > CONFIG.roles.candidate.maxInputUpperTokens) {
        throw new Error(
          `candidate prompt ${scenario.id}/${variant.id} upper bound ${inputUpperTokens} exceeds cap ${CONFIG.roles.candidate.maxInputUpperTokens}`,
        );
      }
      const call = {
        id: `candidate:${scenario.id}:${variant.id}`,
        phase: "candidate",
        role: "candidate",
        scenarioId: scenario.id,
        variantId: variant.id,
        inputUpperTokens,
        maxOutputTokens: CONFIG.roles.candidate.maxTokens,
        seed: seedFor(scenarioIndex, "candidate"),
      };
      calls.push(call);
      candidateByKey.set(`${scenario.id}:${variant.id}`, call.id);
    }
  });

  inputs.scenarios.forEach((scenario, scenarioIndex) => {
    const order = deterministicVariantOrder(scenarioIndex);
    const blinded = order.map((variantId, index) => ({
      blindId: `R${index + 1}`,
      candidateCallId: candidateByKey.get(`${scenario.id}:${variantId}`),
      content: "x".repeat(CONFIG.candidateBytesVisibleToJudge),
    }));
    const messages = buildJudgeMessages(scenario, blinded);
    const inputUpperTokens = inputTokenUpperBound(messages);
    if (inputUpperTokens > CONFIG.roles.judge.maxInputUpperTokens) {
      throw new Error(
        `judge prompt ${scenario.id} upper bound ${inputUpperTokens} exceeds cap ${CONFIG.roles.judge.maxInputUpperTokens}`,
      );
    }
    calls.push({
      id: `judge:${scenario.id}`,
      phase: "judge",
      role: "judge",
      scenarioId: scenario.id,
      blinded: blinded.map(({ blindId, candidateCallId }) => ({ blindId, candidateCallId })),
      inputUpperTokens,
      maxOutputTokens: CONFIG.roles.judge.maxTokens,
      seed: seedFor(scenarioIndex, "judge"),
    });
  });

  const arbiterInputUpperTokens = Math.max(
    ...inputs.scenarios.map((scenario, scenarioIndex) => {
      const blinded = deterministicVariantOrder(scenarioIndex).map((_variantId, index) => ({
        blindId: `R${index + 1}`,
        content: "x".repeat(CONFIG.candidateBytesVisibleToJudge),
      }));
      return inputTokenUpperBound(
        buildArbiterMessages(scenario, blinded, "x".repeat(CONFIG.judgeBytesVisibleToArbiter)),
      );
    }),
  );
  if (arbiterInputUpperTokens > CONFIG.roles.arbiter.maxInputUpperTokens) {
    throw new Error(
      `arbiter prompt upper bound ${arbiterInputUpperTokens} exceeds cap ${CONFIG.roles.arbiter.maxInputUpperTokens}`,
    );
  }
  calls.push({
    id: "arbiter:reserve",
    phase: "arbiter-reserve",
    role: "arbiter",
    scenarioId: null,
    inputUpperTokens: arbiterInputUpperTokens,
    maxOutputTokens: CONFIG.roles.arbiter.maxTokens,
    seed: CONFIG.baseSeed + 20_000,
    optional: true,
  });

  return calls;
}

function decorateCosts(calls, resolutions) {
  const byRole = Object.fromEntries(resolutions.map((resolution) => [resolution.role, resolution]));
  return calls.map((call) => {
    const resolution = byRole[call.role];
    const maximumPico = routedCallMaximumPico(
      resolution.providerRouting.max_price,
      call.inputUpperTokens,
      call.maxOutputTokens,
    );
    return { ...call, maximumCostPicoUsd: maximumPico.toString(), maximumCostUsd: picoToUsd(maximumPico) };
  });
}

function renderPreflight(preflight) {
  const rows = preflight.modelResolutions
    .map(
      (item) =>
        `| ${item.role} | \`${item.resolvedModel}\` | ${item.endpoint.providerName} (\`${item.endpoint.tag}\`) | ${item.endpoint.pricing.prompt} | ${item.endpoint.pricing.completion} |`,
    )
    .join("\n");
  return `# Agent OS experiment preflight

- Status: **${preflight.status.toUpperCase()}**
- Input fingerprint: \`${preflight.inputFingerprint}\`
- Plan integrity: \`${preflight.integrity}\`
- Planned calls: ${preflight.counts.candidates} candidates + ${preflight.counts.judges} batched blind judges + at most ${preflight.counts.arbiters} arbiter
- Conservative maximum: **$${preflight.maximumCostUsd}**
- Effective hard budget: **$${preflight.effectiveBudgetUsd}**

| Role | Exact model | Pinned paid endpoint | Input $/token | Output $/token |
|---|---|---|---:|---:|
${rows}

The run must consume this exact preflight. Each request is pinned to the resolved endpoint with fallbacks disabled. The conservative maximum is calculated from the serialized router price ceilings, which are rounded slightly upward from captured catalog decimals so floating-point serialization cannot exclude the intended endpoint.
`;
}

export async function runPreflight(options = parseArgs(process.argv.slice(2))) {
  const inputs = await loadExperimentInputs();
  const callsWithoutCosts = buildCallPlan(inputs);
  if (options.validateOnly) {
    console.log(
      `validated ${inputs.scenarios.length} scenarios, ${inputs.variants.length} variants, ${callsWithoutCosts.length} planned call slots`,
    );
    return null;
  }

  const apiKey = process.env.OPENROUTER_API_KEY;
  if (!apiKey) throw new Error("OPENROUTER_API_KEY is required for live model resolution");
  const outputDir = options.out;
  const rawDir = path.join(outputDir, "raw", "model-resolution");
  await mkdir(rawDir, { recursive: true });

  const modelResolutions = [];
  for (const role of ["candidate", "judge", "arbiter"]) {
    modelResolutions.push(await resolveRole(role, CONFIG.roles[role], apiKey, rawDir));
  }
  const calls = decorateCosts(callsWithoutCosts, modelResolutions);
  const maximumCostPico = calls.reduce((total, call) => total + BigInt(call.maximumCostPicoUsd), 0n);
  const effectiveBudget = effectiveBudgetPico();
  const passed = maximumCostPico <= effectiveBudget;

  const generatedAt = new Date().toISOString();
  const core = {
    schemaVersion: CONFIG.schemaVersion,
    status: passed ? "pass" : "fail",
    inputFingerprint: inputs.fingerprint,
    effectiveBudgetPicoUsd: effectiveBudget.toString(),
    effectiveBudgetUsd: picoToUsd(effectiveBudget),
    maximumCostPicoUsd: maximumCostPico.toString(),
    maximumCostUsd: picoToUsd(maximumCostPico),
    modelResolutions,
    calls,
    counts: {
      candidates: calls.filter((call) => call.phase === "candidate").length,
      judges: calls.filter((call) => call.phase === "judge").length,
      arbiters: CONFIG.maxArbiterCalls,
      maximumTotal: calls.length,
    },
    generatedAt,
  };
  const preflight = {
    ...core,
    integrity: sha256(canonicalJson(core)),
  };

  await Promise.all([
    writeFile(path.join(outputDir, "preflight.json"), `${JSON.stringify(preflight, null, 2)}\n`),
    writeFile(path.join(outputDir, "preflight.md"), renderPreflight(preflight)),
  ]);
  if (!passed) {
    throw new Error(
      `conservative maximum $${picoToUsd(maximumCostPico)} exceeds effective budget $${picoToUsd(effectiveBudget)}`,
    );
  }
  console.log(
    `preflight PASS: ${preflight.counts.maximumTotal} maximum calls, $${preflight.maximumCostUsd} <= $${preflight.effectiveBudgetUsd}`,
  );
  return preflight;
}

const isMain = process.argv[1] && path.resolve(process.argv[1]) === path.resolve(fileURLToPath(import.meta.url));
if (isMain) {
  runPreflight().catch((error) => {
    console.error(`preflight FAIL: ${error.message}`);
    process.exitCode = 1;
  });
}
