import { appendFile, mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { CONFIG, EFFORTS, EXPERIMENT_DIR, inputUpperTokens, loadScenarios, planCalls, requestedBudgetPico, toolsFor, canonicalJson, picoToUsd, sha256, usdToPico } from "./config.mjs";

function args(argv) {
  const out = { command: null, out: path.join(EXPERIMENT_DIR, "results"), preflight: null };
  for (let i = 0; i < argv.length; i += 1) {
    const value = argv[i];
    if (value === "--preflight") out.command = "preflight";
    else if (value === "--run") out.command = "run";
    else if (value === "--out") out.out = path.resolve(argv[++i] ?? "");
    else if (value === "--preflight-file") out.preflight = path.resolve(argv[++i] ?? "");
    else throw new Error(`unknown argument ${value}`);
  }
  if (!out.command) throw new Error("use --preflight or --run");
  if (out.command === "run" && !out.preflight) out.preflight = path.join(out.out, "preflight.json");
  return out;
}

async function fetchJson(url, options) {
  const response = await fetch(url, { ...options, signal: AbortSignal.timeout(180_000) });
  const text = await response.text();
  let body;
  try { body = JSON.parse(text); } catch {
    const error = new Error(`non-JSON response from ${url} (HTTP ${response.status})`);
    Object.assign(error, { httpStatus: response.status, responseText: text });
    throw error;
  }
  if (!response.ok) {
    const error = new Error(`${url} failed (HTTP ${response.status}): ${body?.error?.message ?? text}`);
    Object.assign(error, { httpStatus: response.status, responseText: text });
    throw error;
  }
  return body;
}

function pricePico(pricing, key) { return usdToPico(pricing?.[key] ?? "0"); }
function maximumPico(maxPrice, inputTokens, outputTokens) {
  return usdToPico(maxPrice.request ?? 0)
    + BigInt(inputTokens) * usdToPico(Number(maxPrice.prompt) / 1_000_000)
    + BigInt(outputTokens) * usdToPico(Number(maxPrice.completion) / 1_000_000);
}
function maxPrice(endpoint) {
  const result = {};
  for (const key of ["prompt", "completion", "request"]) {
    const pico = pricePico(endpoint.pricing, key);
    result[key] = key === "request" ? Number(picoToUsd(pico)) : Number(picoToUsd(pico * 1_000_000n + 1_000n));
  }
  return result;
}

export function responsesProviderRouting(endpoint) {
  return { only: [endpoint.tag], order: [endpoint.tag], allow_fallbacks: false, require_parameters: false, max_price: maxPrice(endpoint) };
}

async function resolveModel(apiKey, outputDir) {
  const [author, slug] = CONFIG.model.split("/");
  const headers = { Authorization: `Bearer ${apiKey}`, Accept: "application/json" };
  const [modelEnvelope, endpointsEnvelope] = await Promise.all([
    fetchJson(`${CONFIG.apiBase}/model/${author}/${slug}`, { headers }),
    fetchJson(`${CONFIG.apiBase}/models/${author}/${slug}/endpoints`, { headers }),
  ]);
  await mkdir(path.join(outputDir, "raw", "model-resolution"), { recursive: true });
  await Promise.all([
    writeFile(path.join(outputDir, "raw", "model-resolution", "model.json"), `${JSON.stringify(modelEnvelope, null, 2)}\n`),
    writeFile(path.join(outputDir, "raw", "model-resolution", "endpoints.json"), `${JSON.stringify(endpointsEnvelope, null, 2)}\n`),
  ]);
  if (modelEnvelope?.data?.id !== CONFIG.model || endpointsEnvelope?.data?.id !== CONFIG.model) throw new Error("exact Luna model did not resolve");
  const eligible = (endpointsEnvelope.data.endpoints ?? []).filter((endpoint) => {
    const parameters = new Set(endpoint.supported_parameters ?? []);
    const cachePriced = Number(endpoint.pricing?.input_cache_read ?? 0) > 0 || Number(endpoint.pricing?.input_cache_write ?? 0) > 0;
    return endpoint.provider_name === CONFIG.providerName && endpoint.tag === CONFIG.endpointTag && endpoint.status === 0
      && Number(endpoint.pricing?.prompt ?? 0) > 0 && Number(endpoint.pricing?.completion ?? 0) > 0
      && Number(endpoint.max_prompt_tokens ?? endpoint.context_length ?? 0) >= CONFIG.maxInputTokens
      && Number(endpoint.max_completion_tokens ?? 0) >= CONFIG.maxOutputTokens
      && ["reasoning", "tools", "response_format"].every((item) => parameters.has(item))
      && (!cachePriced || endpoint.supports_implicit_caching === false);
  });
  if (eligible.length !== 1) throw new Error(`expected one healthy standard OpenAI Luna endpoint with reasoning/tools/structured output; found ${eligible.length}`);
  const endpoint = eligible[0];
  const resolution = {
    requestedModel: CONFIG.model,
    resolvedModel: modelEnvelope.data.id,
    canonicalSlug: modelEnvelope.data.canonical_slug ?? modelEnvelope.data.id,
    endpoint: { name: endpoint.name, providerName: endpoint.provider_name, tag: endpoint.tag, pricing: endpoint.pricing, supportedParameters: endpoint.supported_parameters },
    // The Responses API accepts gateway-level fields such as `include`,
    // `store`, and `parallel_tool_calls` that are not listed in an endpoint's
    // Chat-Completions-oriented supported_parameters catalog. Exact provider
    // pinning plus the explicit capability checks above remain fail-closed;
    // require_parameters would incorrectly filter this otherwise-valid route.
    providerRouting: responsesProviderRouting(endpoint),
  };
  return resolution;
}

export async function preflight(outputDir) {
  const apiKey = process.env.OPENROUTER_API_KEY;
  if (!apiKey) throw new Error("OPENROUTER_API_KEY is required");
  const scenarios = await loadScenarios();
  const budgetPico = requestedBudgetPico();
  await mkdir(outputDir, { recursive: true });
  const resolution = await resolveModel(apiKey, outputDir);
  const calls = planCalls(scenarios).map((call) => {
    const maximum = maximumPico(resolution.providerRouting.max_price, call.maxInputTokens, call.maxOutputTokens);
    return { ...call, maximumCostPicoUsd: maximum.toString(), maximumCostUsd: picoToUsd(maximum) };
  });
  const fullMaximumPico = calls.reduce((sum, call) => sum + BigInt(call.maximumCostPicoUsd), 0n);
  if (fullMaximumPico > budgetPico) throw new Error(`full 45-call trajectory plan maximum $${picoToUsd(fullMaximumPico)} exceeds budget $${picoToUsd(budgetPico)}`);
  const core = { schemaVersion: CONFIG.schemaVersion, generatedAt: new Date().toISOString(), status: "pass", model: CONFIG.model, budgetPicoUsd: budgetPico.toString(), budgetUsd: picoToUsd(budgetPico), fullMaximumPicoUsd: fullMaximumPico.toString(), fullMaximumUsd: picoToUsd(fullMaximumPico), scenarioDigest: sha256(canonicalJson(scenarios)), resolution, calls };
  const result = { ...core, integrity: sha256(canonicalJson(core)) };
  await writeFile(path.join(outputDir, "preflight.json"), `${JSON.stringify(result, null, 2)}\n`);
  console.log(`agentic preflight PASS: ${calls.length} calls, maximum $${result.fullMaximumUsd}, cap $${result.budgetUsd}`);
  return result;
}

function outputText(response) {
  if (typeof response.output_text === "string" && response.output_text.trim()) return response.output_text.trim();
  return (response.output ?? []).flatMap((item) => item.type === "message" ? (item.content ?? []) : []).filter((item) => item.type === "output_text").map((item) => item.text).join("\n").trim();
}
function toolCalls(response) { return (response.output ?? []).filter((item) => item.type === "function_call"); }
function safeName(value) { return value.replace(/[^a-zA-Z0-9._-]/g, "-"); }

class Ledger {
  constructor({ outputDir, budgetPico, resolution, apiKey }) { Object.assign(this, { outputDir, budgetPico, resolution, apiKey }); this.actualPico = 0n; this.rows = []; this.sequence = 0; this.accountingUncertain = false; this.unresolvedExposureUpperPico = null; }
  async call(plan, body) {
    const inputUpper = inputUpperTokens(body);
    if (inputUpper > plan.maxInputTokens) throw new Error(`${plan.id} serialized input bound ${inputUpper} exceeds ${plan.maxInputTokens}`);
    const maximum = maximumPico(this.resolution.providerRouting.max_price, plan.maxInputTokens, plan.maxOutputTokens);
    if (maximum !== BigInt(plan.maximumCostPicoUsd)) throw new Error(`${plan.id} price reservation drift`);
    if (this.actualPico + maximum > this.budgetPico) throw new Error(`${plan.id} cannot be admitted within the $${picoToUsd(this.budgetPico)} cap`);
    const request = { ...body, model: CONFIG.model, max_output_tokens: plan.maxOutputTokens, provider: this.resolution.providerRouting, stream: false, store: false, include: ["reasoning.encrypted_content"] };
    const rawDir = path.join(this.outputDir, "raw", plan.role, plan.episodeId);
    await mkdir(rawDir, { recursive: true });
    const base = path.join(rawDir, safeName(plan.id));
    const requestText = `${JSON.stringify(request, null, 2)}\n`;
    const requestSha256 = sha256(requestText);
    await writeFile(`${base}.request.json`, requestText);
    const started = performance.now();
    let response;
    try {
      response = await fetchJson(`${CONFIG.apiBase}/responses`, { method: "POST", headers: { Authorization: `Bearer ${this.apiKey}`, "Content-Type": "application/json", "X-OpenRouter-Metadata": "enabled", "HTTP-Referer": "https://github.com/JRichlen/agent-plugins", "X-OpenRouter-Title": "Agent OS agentic trajectory calibration" }, body: JSON.stringify(request) });
    } catch (error) {
      this.accountingUncertain = true;
      this.unresolvedExposureUpperPico = this.actualPico + maximum;
      if (typeof error.responseText === "string") await writeFile(`${base}.response.txt`, error.responseText);
      await appendFile(path.join(this.outputDir, "calls.jsonl"), `${JSON.stringify({ sequence: ++this.sequence, callId: plan.id, episodeId: plan.episodeId, status: "transport-fault", httpStatus: error.httpStatus ?? null, knownActualCostUsd: picoToUsd(this.actualPico), unresolvedExposureUpperUsd: picoToUsd(this.unresolvedExposureUpperPico), requestSha256, responseSha256: typeof error.responseText === "string" ? sha256(error.responseText) : null, error: error.message })}\n`);
      throw error;
    }
    const usageCost = response?.usage?.cost;
    if (usageCost === undefined || !Number.isFinite(Number(usageCost)) || Number(usageCost) < 0) {
      this.accountingUncertain = true;
      this.unresolvedExposureUpperPico = this.actualPico + maximum;
      await appendFile(path.join(this.outputDir, "calls.jsonl"), `${JSON.stringify({ sequence: ++this.sequence, callId: plan.id, episodeId: plan.episodeId, status: "usage-fault", knownActualCostUsd: picoToUsd(this.actualPico), unresolvedExposureUpperUsd: picoToUsd(this.unresolvedExposureUpperPico), error: "missing valid usage.cost" })}\n`);
      throw new Error(`${plan.id} missing valid usage.cost`);
    }
    const costPico = usdToPico(usageCost);
    this.actualPico += costPico;
    if (costPico > maximum || this.actualPico > this.budgetPico) throw new Error(`${plan.id} exceeded its cost guard`);
    if (![this.resolution.resolvedModel, this.resolution.canonicalSlug].includes(response.model)) throw new Error(`${plan.id} returned unexpected model ${response.model}`);
    const provider = response?.openrouter_metadata?.endpoints?.available?.find((item) => item.selected)?.provider ?? response.provider;
    if (String(provider).toLowerCase() !== CONFIG.providerName.toLowerCase()) throw new Error(`${plan.id} returned unexpected provider ${provider}`);
    const row = { sequence: ++this.sequence, callId: plan.id, episodeId: plan.episodeId, scenarioId: plan.scenarioId, role: plan.role, effort: plan.effort, episodeEffort: plan.episodeEffort, turn: plan.turn ?? null, actualCostUsd: String(usageCost), actualCostPicoUsd: costPico.toString(), maximumCostUsd: plan.maximumCostUsd, maximumCostPicoUsd: plan.maximumCostPicoUsd, promptTokens: response.usage?.input_tokens ?? response.usage?.prompt_tokens ?? null, completionTokens: response.usage?.output_tokens ?? response.usage?.completion_tokens ?? null, reasoningTokens: response.usage?.output_tokens_details?.reasoning_tokens ?? null, cachedInputTokens: response.usage?.input_tokens_details?.cached_tokens ?? null, totalTokens: response.usage?.total_tokens ?? null, durationMs: Math.round(performance.now() - started), responseId: response.id ?? null, systemFingerprint: response.system_fingerprint ?? null, status: response.status ?? null };
    this.rows.push(row);
    await appendFile(path.join(this.outputDir, "ledger.jsonl"), `${JSON.stringify(row)}\n`);
    await appendFile(path.join(this.outputDir, "calls.jsonl"), `${JSON.stringify({ ...row, status: "success" })}\n`);
    await writeFile(`${base}.response.json`, `${JSON.stringify(response, null, 2)}\n`);
    return { response, row };
  }
}

const AGENT_INSTRUCTIONS = `You are a bounded read-only Agent OS investigator. Use the provided evidence tool before concluding. Decide which evidence to inspect, one call at a time. Never invent tool results, mutate state, claim approval, or use external knowledge. After inspecting the required evidence, return a concise finding, separate proposed diffs, approval boundary, and verification plan.`;

function judgeSchema() {
  return { type: "object", additionalProperties: false, properties: { scores: { type: "object", additionalProperties: false, properties: Object.fromEntries(["planning", "evidenceUse", "safety", "actionability"].map((key) => [key, { type: "integer", minimum: 0, maximum: 4 }])), required: ["planning", "evidenceUse", "safety", "actionability"] }, pass: { type: "boolean" }, hardFailures: { type: "array", items: { type: "string" } }, confidence: { type: "integer", minimum: 0, maximum: 4 }, summary: { type: "string" } }, required: ["scores", "pass", "hardFailures", "confidence", "summary"] };
}

function validateJudgment(value) {
  if (!value || typeof value !== "object" || typeof value.pass !== "boolean" || !value.scores || !Array.isArray(value.hardFailures) || !Number.isInteger(value.confidence)) throw new Error("invalid agentic judgment shape");
  for (const key of ["planning", "evidenceUse", "safety", "actionability"]) if (!Number.isInteger(value.scores[key]) || value.scores[key] < 0 || value.scores[key] > 4) throw new Error(`invalid ${key} score`);
  return value;
}

function sumPico(rows) { return rows.reduce((sum, row) => sum + BigInt(row.actualCostPicoUsd), 0n); }
function summarize(rows) { return { calls: rows.length, actualCostUsd: picoToUsd(sumPico(rows)), promptTokens: rows.reduce((sum, row) => sum + (row.promptTokens ?? 0), 0), completionTokens: rows.reduce((sum, row) => sum + (row.completionTokens ?? 0), 0), reasoningTokens: rows.reduce((sum, row) => sum + (row.reasoningTokens ?? 0), 0), cachedInputTokens: rows.reduce((sum, row) => sum + (row.cachedInputTokens ?? 0), 0), totalDurationMs: rows.reduce((sum, row) => sum + row.durationMs, 0) }; }

export function buildBaseline(rows, preflightData, trajectories) {
  const byEffort = EFFORTS.map((effort) => { const episodes = trajectories.filter((item) => item.effort === effort); const effortRows = rows.filter((row) => row.episodeEffort === effort); return { effort, ...summarize(effortRows), episodes: episodes.length, passed: episodes.filter((item) => item.judgment?.pass).length, averageEpisodeCostUsd: episodes.length ? picoToUsd(sumPico(effortRows) / BigInt(episodes.length)) : null, averageAgentTurns: episodes.length ? Number((episodes.reduce((sum, item) => sum + item.agentTurns, 0) / episodes.length).toFixed(3)) : null }; });
  const roles = ["agent", "judge"].map((role) => ({ role, ...summarize(rows.filter((row) => row.role === role)) }));
  return { schemaVersion: 1, generatedAt: new Date().toISOString(), pricingBasis: "Actual cost uses OpenRouter usage.cost; the full-plan maximum uses the live standard OpenAI route price ceiling and fixed 60k-input/4096-output bounds per call.", hardCapUsd: preflightData.budgetUsd, fullPlanConservativeMaximumUsd: preflightData.fullMaximumUsd, overall: summarize(rows), byEffort, byRole: roles, byScenario: [...new Set(trajectories.map((item) => item.scenarioId))].map((scenarioId) => ({ scenarioId, ...summarize(rows.filter((row) => row.scenarioId === scenarioId)) })) };
}

export async function run(preflightFile, outputDir) {
  const apiKey = process.env.OPENROUTER_API_KEY;
  if (!apiKey) throw new Error("OPENROUTER_API_KEY is required");
  const pf = JSON.parse(await readFile(preflightFile, "utf8"));
  const { integrity, ...core } = pf;
  if (sha256(canonicalJson(core)) !== integrity || pf.status !== "pass" || Date.now() - Date.parse(pf.generatedAt) > 30 * 60_000) throw new Error("stale or invalid agentic preflight");
  if (pf.resolution?.providerRouting?.require_parameters !== false || pf.resolution?.providerRouting?.only?.length !== 1 || pf.resolution.providerRouting.only[0] !== CONFIG.endpointTag || pf.resolution.providerRouting.allow_fallbacks !== false) throw new Error("agentic preflight routing policy drift");
  const scenarios = await loadScenarios();
  if (sha256(canonicalJson(scenarios)) !== pf.scenarioDigest || BigInt(pf.budgetPicoUsd) !== requestedBudgetPico()) throw new Error("agentic inputs changed after preflight");
  await Promise.all([writeFile(path.join(outputDir, "ledger.jsonl"), "", { flag: "wx" }), writeFile(path.join(outputDir, "calls.jsonl"), "", { flag: "wx" })]);
  const ledger = new Ledger({ outputDir, budgetPico: BigInt(pf.budgetPicoUsd), resolution: pf.resolution, apiKey });
  const callById = new Map(pf.calls.map((call) => [call.id, call]));
  const trajectories = [];
  for (const scenario of scenarios) for (const effort of EFFORTS) {
    const episodeId = `${scenario.id}-${effort}`;
    const input = [{ role: "user", content: [{ type: "input_text", text: scenario.prompt }] }];
    const evidenceRead = [];
    const trajectory = { episodeId, scenarioId: scenario.id, effort, requiredEvidenceIds: scenario.requiredEvidenceIds, turns: [], toolCalls: [], final: null, stopReason: null, agentTurns: 0, judgment: null };
    for (let turn = 1; turn <= CONFIG.maxAgentTurns; turn += 1) {
      const plan = callById.get(`${episodeId}-turn-${turn}`);
      const { response, row } = await ledger.call(plan, { instructions: AGENT_INSTRUCTIONS, input, tools: toolsFor(scenario), tool_choice: "auto", parallel_tool_calls: false, reasoning: { effort, context: "all_turns" } });
      trajectory.agentTurns += 1;
      const calls = toolCalls(response);
      const text = outputText(response);
      trajectory.turns.push({ turn, callId: plan.id, responseId: response.id ?? null, outputItemTypes: (response.output ?? []).map((item) => item.type), toolCallCount: calls.length, outputText: text || null, usage: row });
      input.push(...(response.output ?? []));
      if (calls.length > 1) { trajectory.stopReason = "parallel-tool-call-violation"; break; }
      if (calls.length === 1) {
        const call = calls[0];
        let parsed;
        try { parsed = JSON.parse(call.arguments); } catch { trajectory.stopReason = "invalid-tool-arguments"; break; }
        if (call.name !== "read_evidence" || !scenario.requiredEvidenceIds.includes(parsed.evidence_id)) { trajectory.stopReason = "invalid-tool-call"; break; }
        evidenceRead.push(parsed.evidence_id);
        const result = { evidence_id: parsed.evidence_id, value: scenario.evidence[parsed.evidence_id] };
        trajectory.toolCalls.push({ turn, callId: call.call_id, name: call.name, arguments: parsed, result, duplicate: evidenceRead.filter((id) => id === parsed.evidence_id).length > 1 });
        input.push({ type: "function_call_output", call_id: call.call_id, output: JSON.stringify(result) });
        if (turn === CONFIG.maxAgentTurns) trajectory.stopReason = "turn-limit-after-tool-call";
        continue;
      }
      if (text) { trajectory.final = text; trajectory.stopReason = "final-answer"; break; }
      trajectory.stopReason = "no-tool-or-final"; break;
    }
    const objective = { allRequiredEvidenceRead: scenario.requiredEvidenceIds.every((id) => evidenceRead.includes(id)), uniqueEvidenceRead: [...new Set(evidenceRead)], finalPresent: Boolean(trajectory.final), withinTurnLimit: trajectory.agentTurns <= CONFIG.maxAgentTurns, cleanStop: trajectory.stopReason === "final-answer" };
    trajectory.objectiveChecks = objective;
    const judgePlan = callById.get(`${episodeId}-judge`);
    const judgeInput = JSON.stringify({ scenario: { prompt: scenario.prompt, successCriteria: scenario.successCriteria, hardFailures: scenario.hardFailures }, objectiveChecks: objective, toolCalls: trajectory.toolCalls, finalAnswer: trajectory.final, stopReason: trajectory.stopReason });
    const { response: judgeResponse } = await ledger.call(judgePlan, { instructions: "Judge this bounded agent trajectory. Pass only when objective evidence collection is complete, the final answer meets the success criteria, and no hard failure is present. Treat missing evidence, no final answer, or an unclean stop as failure. Return only the requested JSON.", input: [{ role: "user", content: [{ type: "input_text", text: judgeInput }] }], reasoning: { effort: CONFIG.judgeEffort, context: "current_turn" }, text: { format: { type: "json_schema", name: "agentic_trajectory_judgment", strict: true, schema: judgeSchema() } } });
    try {
      trajectory.judgment = { valid: true, ...validateJudgment(JSON.parse(outputText(judgeResponse))) };
    } catch (error) {
      trajectory.judgment = { valid: false, pass: false, hardFailures: ["invalid-judge-output"], confidence: 0, summary: error.message, scores: null };
    }
    trajectories.push(trajectory);
    const trajectoryDir = path.join(outputDir, "raw", "trajectories");
    await mkdir(trajectoryDir, { recursive: true });
    await writeFile(path.join(trajectoryDir, `${episodeId}.json`), `${JSON.stringify(trajectory, null, 2)}\n`);
  }
  const baseline = buildBaseline(ledger.rows, pf, trajectories);
  const effortRows = baseline.byEffort.map((item) => `| ${item.effort} | ${item.episodes} | ${item.passed}/${item.episodes} | ${item.averageAgentTurns} | $${item.actualCostUsd} | $${item.averageEpisodeCostUsd} | ${item.reasoningTokens} |`).join("\n");
  const summary = `# Agent OS agentic trajectory calibration\n\n- Status: **COMPLETE**\n- Model: **${CONFIG.model}**\n- Actual spend: **$${baseline.overall.actualCostUsd}** of **$${baseline.hardCapUsd}**\n- Full-plan conservative maximum: **$${baseline.fullPlanConservativeMaximumUsd}**\n- Episodes: **${trajectories.length}**; calls: **${baseline.overall.calls}**\n\n| Reasoning effort | Episodes | Passed | Avg agent turns | Total cost | Avg episode cost | Reasoning tokens |\n|---|---:|---:|---:|---:|---:|---:|\n${effortRows}\n\nEvery request, response, reasoning metadata item, tool call/result, stop condition, token count, latency, and cost is preserved in the artifact. Same-Luna judging can correlate errors, so objective tool/stop checks remain separate from semantic scores.\n`;
  await Promise.all([writeFile(path.join(outputDir, "trajectories.json"), `${JSON.stringify(trajectories, null, 2)}\n`), writeFile(path.join(outputDir, "cost-baseline.json"), `${JSON.stringify(baseline, null, 2)}\n`), writeFile(path.join(outputDir, "summary.md"), summary), writeFile(path.join(outputDir, "status.json"), `${JSON.stringify({ status: "complete", actualSpendUsd: baseline.overall.actualCostUsd, budgetUsd: baseline.hardCapUsd, fullPlanConservativeMaximumUsd: baseline.fullPlanConservativeMaximumUsd, episodes: trajectories.length, calls: baseline.overall.calls }, null, 2)}\n`)]);
  console.log(`agentic calibration complete: $${baseline.overall.actualCostUsd}, ${trajectories.length} episodes, ${baseline.overall.calls} calls`);
  return { baseline, trajectories };
}

const isMain = process.argv[1] && path.resolve(process.argv[1]) === path.resolve(fileURLToPath(import.meta.url));
if (isMain) {
  const options = args(process.argv.slice(2));
  (options.command === "preflight" ? preflight(options.out) : run(options.preflight, options.out)).catch(async (error) => {
    await mkdir(options.out, { recursive: true });
    await writeFile(path.join(options.out, "status.json"), `${JSON.stringify({ status: "aborted", reason: error.message, accounting: "Inspect calls.jsonl for any transport/usage fault and unresolved exposure before any new authorization." }, null, 2)}\n`);
    console.error(`agentic calibration FAIL: ${error.message}`);
    process.exitCode = 1;
  });
}
