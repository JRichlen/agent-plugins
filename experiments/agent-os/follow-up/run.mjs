import { appendFile, mkdir, readFile, readdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  CONFIG,
  EXPERIMENT_DIR,
  ORIGINAL_ACTUAL_SPEND_USD,
  SCORE_DIMENSIONS,
  buildCandidateMessages,
  buildJudgeMessages,
  canonicalJson,
  effectiveNewBudgetPico,
  inputTokenUpperBound,
  judgeResponseFormat,
  loadFollowUpInputs,
  normalizeReviewText,
  picoToUsd,
  requestInputTokenUpperBound,
  sha256,
  truncateUtf8,
  usdToPico,
} from "./config.mjs";
import { aggregatePaired, collectPairedDiagnostics, parseJsonResponse, recommendPaired, validateJudgment } from "./judgment.mjs";
import { buildAblationPlan, buildRejudgePlan, buildStages, providerMaxPrice, routedCallMaximumPico } from "./preflight.mjs";
import { loadSourceArtifact } from "./source.mjs";

function parseArgs(argv) {
  const options = { preflight: path.join(EXPERIMENT_DIR, "results", "preflight.json"), out: null, source: null };
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === "--preflight") options.preflight = path.resolve(argv[++index] ?? "");
    else if (argument === "--out") options.out = path.resolve(argv[++index] ?? "");
    else if (argument === "--source") options.source = path.resolve(argv[++index] ?? "");
    else if (argument === "--help") {
      console.log("usage: node experiments/agent-os/follow-up/run.mjs --preflight FILE [--source DIR] [--out DIR]");
      process.exit(0);
    } else throw new Error(`unknown argument: ${argument}`);
  }
  if (!options.preflight) throw new Error("--preflight requires a file");
  if (!options.out) options.out = path.dirname(options.preflight);
  return options;
}

function safeName(value) {
  return String(value).replace(/[^a-zA-Z0-9._-]+/g, "-");
}

async function assertFreshRunOutput(outputDir) {
  let entries;
  try {
    entries = await readdir(outputDir, { withFileTypes: true });
  } catch (error) {
    if (error.code === "ENOENT") return;
    throw error;
  }
  const allowed = new Set(["preflight.json", "preflight.md", "raw"]);
  const unexpected = entries.filter((entry) => !allowed.has(entry.name)).map((entry) => entry.name);
  const raw = entries.find((entry) => entry.name === "raw");
  if (raw) {
    if (!raw.isDirectory()) unexpected.push("raw (not a directory)");
    else {
      const rawEntries = await readdir(path.join(outputDir, "raw"), { withFileTypes: true });
      unexpected.push(...rawEntries.filter((entry) => entry.name !== "model-resolution").map((entry) => `raw/${entry.name}`));
    }
  }
  if (unexpected.length) throw new Error(`refusing nonempty/reused run output: ${unexpected.join(", ")}`);
}

function extractContent(envelope) {
  const content = envelope?.choices?.[0]?.message?.content;
  if (typeof content !== "string" || !content.trim()) throw new Error("response has no non-empty assistant content");
  return content;
}

function responseProvenance(envelope) {
  const available = envelope?.openrouter_metadata?.endpoints?.available;
  const selected = Array.isArray(available) ? available.filter((endpoint) => endpoint?.selected === true) : [];
  if (selected.length > 1) return { provider: null, model: null, error: `router metadata marked ${selected.length} endpoints selected` };
  const metadataProvider = selected[0]?.provider;
  const legacyProvider = envelope?.provider;
  if (typeof metadataProvider === "string" && typeof legacyProvider === "string" && metadataProvider.toLowerCase() !== legacyProvider.toLowerCase()) {
    return { provider: null, model: selected[0]?.model ?? null, error: "router metadata and legacy provider disagree" };
  }
  const provider = metadataProvider ?? legacyProvider ?? null;
  return { provider, model: selected[0]?.model ?? null, error: provider ? null : "response contains neither selected router metadata nor a legacy provider field" };
}

export function buildRequestBody(planCall, resolution, messages, responseFormat = null) {
  inputTokenUpperBound(messages); // also asserts tool-free role/content objects
  const roleConfig = CONFIG.roles[planCall.role];
  const body = {
    model: resolution.resolvedModel,
    messages,
    max_tokens: roleConfig.maxTokens,
    reasoning: CONFIG.reasoning,
    stream: false,
    usage: { include: true },
    provider: resolution.providerRouting,
    seed: planCall.seed,
  };
  if (planCall.role !== "candidate") {
    if (!responseFormat) throw new Error(`${planCall.role} requires a strict response format`);
    body.response_format = responseFormat;
  }
  for (const forbidden of ["tools", "tool_choice", "plugins", "web_search"]) {
    if (Object.hasOwn(body, forbidden)) throw new Error(`experiment request must not enable ${forbidden}`);
  }
  if (["candidate", "primaryJudge", "rejudge"].includes(planCall.role) && Object.hasOwn(body, "temperature")) {
    throw new Error("Luna requests must omit temperature for the pinned standard endpoint");
  }
  return body;
}

class SpendLedger {
  constructor({ outputDir, budgetPico, resolutions, apiKey }) {
    this.outputDir = outputDir;
    this.budgetPico = budgetPico;
    this.resolutions = Object.fromEntries(resolutions.map((item) => [item.role, item]));
    this.apiKey = apiKey;
    this.actualPico = 0n;
    this.sequence = 0;
    this.ledgerPath = path.join(outputDir, "ledger.jsonl");
    this.callsPath = path.join(outputDir, "calls.jsonl");
    this.accountingUncertain = false;
    this.unresolvedExposureUpperPico = null;
    this.stageAdmissions = [];
    this.rows = [];
  }

  admitFullStage(stage, calls) {
    const maximumPico = calls.reduce((sum, call) => sum + BigInt(call.maximumCostPicoUsd), 0n);
    const admitted = this.actualPico + maximumPico <= this.budgetPico;
    const row = { stage, policy: "full-stage", actualBeforeUsd: picoToUsd(this.actualPico), stageMaximumUsd: picoToUsd(maximumPico), admitted };
    this.stageAdmissions.push(row);
    if (!admitted) throw new Error(`stage ${stage} not admitted: $${picoToUsd(this.actualPico)} actual + $${picoToUsd(maximumPico)} full-stage maximum > $${picoToUsd(this.budgetPico)}`);
    return row;
  }

  assessConditionalFullStage(stage, calls) {
    const maximumPico = calls.reduce((sum, call) => sum + BigInt(call.maximumCostPicoUsd), 0n);
    const admitted = this.actualPico + maximumPico <= this.budgetPico;
    const row = { stage, policy: "conditional-full-stage", actualBeforeUsd: picoToUsd(this.actualPico), stageMaximumUsd: picoToUsd(maximumPico), admitted };
    this.stageAdmissions.push(row);
    return row;
  }

  admitPriorityPrefix(stage, calls) {
    const selected = [];
    let reserved = 0n;
    for (const call of [...calls].sort((left, right) => left.rejudgePriority - right.rejudgePriority)) {
      const next = reserved + BigInt(call.maximumCostPicoUsd);
      if (this.actualPico + next > this.budgetPico) break;
      selected.push(call);
      reserved = next;
    }
    this.stageAdmissions.push({ stage, policy: "fixed-priority-prefix", actualBeforeUsd: picoToUsd(this.actualPico), prefixMaximumUsd: picoToUsd(reserved), selectedCallIds: selected.map((call) => call.id), omittedCallIds: calls.filter((call) => !selected.includes(call)).map((call) => call.id) });
    return selected;
  }

  async execute(planCall, messages, responseFormat = null) {
    const maximumPico = BigInt(planCall.maximumCostPicoUsd);
    if (this.actualPico + maximumPico > this.budgetPico) throw new Error(`per-call guard stopped ${planCall.id}: actual plus call maximum exceeds budget`);
    const resolution = this.resolutions[planCall.role];
    if (!resolution) throw new Error(`missing resolution for ${planCall.role}`);
    const inputUpperTokens = requestInputTokenUpperBound(messages, responseFormat);
    if (inputUpperTokens > planCall.inputUpperTokens) throw new Error(`${planCall.id} input upper bound ${inputUpperTokens} exceeds reserved ${planCall.inputUpperTokens}`);
    const body = buildRequestBody(planCall, resolution, messages, responseFormat);
    const requestText = `${JSON.stringify(body, null, 2)}\n`;
    const rawDir = path.join(this.outputDir, "raw", planCall.role);
    await mkdir(rawDir, { recursive: true });
    const fileBase = path.join(rawDir, safeName(planCall.id));
    const startedAt = new Date().toISOString();
    const start = performance.now();
    let response;
    let responseText;
    let envelope;
    try {
      response = await fetch(`${CONFIG.apiBase}/chat/completions`, {
        method: "POST",
        headers: { Authorization: `Bearer ${this.apiKey}`, "Content-Type": "application/json", "X-OpenRouter-Metadata": "enabled", "HTTP-Referer": "https://github.com/JRichlen/agent-plugins", "X-OpenRouter-Title": "Agent OS paired follow-up" },
        body: JSON.stringify(body),
        signal: AbortSignal.timeout(180_000),
      });
      responseText = await response.text();
      try {
        envelope = JSON.parse(responseText);
      } catch {
        throw new Error(`${planCall.id} returned non-JSON (HTTP ${response.status})`);
      }
    } catch (error) {
      this.accountingUncertain = true;
      this.unresolvedExposureUpperPico = this.actualPico + maximumPico;
      const fault = { sequence: ++this.sequence, callId: planCall.id, phase: planCall.phase, status: "transport-fault", startedAt, knownActualCostUsd: "0", cumulativeKnownCostUsd: picoToUsd(this.actualPico), maximumCostExposureUsd: planCall.maximumCostUsd, cumulativeExposureUpperUsd: picoToUsd(this.actualPico + maximumPico), budgetUsd: picoToUsd(this.budgetPico), accountingUncertain: true, error: error.message, requestSha256: sha256(requestText), responseSha256: responseText === undefined ? null : sha256(responseText) };
      await appendFile(this.callsPath, `${JSON.stringify(fault)}\n`);
      await writeFile(`${fileBase}.request.json`, requestText);
      if (responseText !== undefined) await writeFile(`${fileBase}.response.txt`, responseText);
      throw error;
    }
    const formattedResponse = `${JSON.stringify(envelope, null, 2)}\n`;
    const requestSha256 = sha256(requestText);
    const responseSha256 = sha256(formattedResponse);
    const usageCost = envelope?.usage?.cost;
    if (usageCost === undefined || usageCost === null || !Number.isFinite(Number(usageCost)) || Number(usageCost) < 0) {
      this.accountingUncertain = true;
      this.unresolvedExposureUpperPico = this.actualPico + maximumPico;
      const fault = { sequence: ++this.sequence, callId: planCall.id, phase: planCall.phase, status: "usage-fault", httpStatus: response.status, startedAt, knownActualCostUsd: "0", cumulativeKnownCostUsd: picoToUsd(this.actualPico), maximumCostExposureUsd: planCall.maximumCostUsd, cumulativeExposureUpperUsd: picoToUsd(this.actualPico + maximumPico), budgetUsd: picoToUsd(this.budgetPico), accountingUncertain: true, error: "missing or invalid OpenRouter usage.cost", requestSha256, responseSha256 };
      await appendFile(this.callsPath, `${JSON.stringify(fault)}\n`);
      await Promise.all([writeFile(`${fileBase}.request.json`, requestText), writeFile(`${fileBase}.response.json`, formattedResponse)]);
      throw new Error(`${planCall.id} has no valid usage.cost; aborting fail-closed`);
    }
    // Encumber and record known spend before any raw-artifact write. If a
    // later filesystem write fails, the append-only accounting still survives.
    const costPico = usdToPico(usageCost);
    this.actualPico += costPico;
    const provenance = responseProvenance(envelope);
    const errors = [];
    if (!response.ok) errors.push(`HTTP ${response.status}: ${envelope?.error?.message ?? "unknown error"}`);
    if (![resolution.resolvedModel, resolution.canonicalSlug].includes(envelope.model)) errors.push(`unexpected model ${envelope.model}`);
    if (provenance.error) errors.push(provenance.error);
    if (typeof provenance.provider === "string" && provenance.provider.toLowerCase() !== resolution.endpoint.providerName.toLowerCase()) errors.push(`unexpected provider ${provenance.provider}`);
    if (provenance.model && ![resolution.resolvedModel, resolution.canonicalSlug, envelope.model].includes(provenance.model)) errors.push(`router selected unexpected model ${provenance.model}`);
    if (costPico > maximumPico) errors.push("actual usage.cost exceeded preflight call maximum");
    if (this.actualPico > this.budgetPico) errors.push("new-run hard budget exceeded");
    let content = null;
    try {
      content = extractContent(envelope);
    } catch (error) {
      errors.push(error.message);
    }
    const ledgerRow = {
      sequence: ++this.sequence,
      callId: planCall.id,
      stage: planCall.stage,
      phase: planCall.phase,
      role: planCall.role,
      scenarioId: planCall.scenarioId,
      treatmentId: planCall.treatmentId ?? null,
      replicateIndex: planCall.replicateIndex ?? null,
      seed: planCall.seed,
      requestedModel: resolution.requestedModel,
      returnedModel: envelope.model,
      requestedEndpoint: resolution.endpoint.tag,
      returnedProvider: provenance.provider,
      routerSelectedModel: provenance.model,
      routerAttempt: envelope?.openrouter_metadata?.attempt ?? null,
      generationId: envelope.id ?? null,
      systemFingerprint: envelope.system_fingerprint ?? null,
      promptTokens: envelope.usage.prompt_tokens ?? null,
      completionTokens: envelope.usage.completion_tokens ?? null,
      totalTokens: envelope.usage.total_tokens ?? null,
      actualCostUsd: String(usageCost),
      actualCostPicoUsd: costPico.toString(),
      cumulativeNewCostUsd: picoToUsd(this.actualPico),
      maximumCostUsd: planCall.maximumCostUsd,
      maximumCostPicoUsd: planCall.maximumCostPicoUsd,
      inputUpperTokens,
      finishReason: envelope.choices?.[0]?.finish_reason ?? null,
      nativeFinishReason: envelope.choices?.[0]?.native_finish_reason ?? null,
      requestSha256,
      responseSha256,
      startedAt,
      durationMs: Math.round(performance.now() - start),
    };
    await appendFile(this.ledgerPath, `${JSON.stringify(ledgerRow)}\n`);
    this.rows.push(ledgerRow);
    await appendFile(this.callsPath, `${JSON.stringify({ ...ledgerRow, status: errors.length ? "response-fault" : "success", errors })}\n`);
    await Promise.all([writeFile(`${fileBase}.request.json`, requestText), writeFile(`${fileBase}.response.json`, formattedResponse)]);
    if (errors.length) throw new Error(`${planCall.id}: ${errors.join("; ")}`);
    return { envelope, content, ledgerRow };
  }
}

function verifyPreflight(preflight, inputs, source) {
  const { integrity, ...core } = preflight;
  if (sha256(canonicalJson(core)) !== integrity) throw new Error("preflight integrity hash does not match");
  if (preflight.status !== "pass") throw new Error("preflight did not pass");
  const age = Date.now() - Date.parse(preflight.generatedAt);
  if (!Number.isFinite(age) || age < 0 || age > 30 * 60 * 1_000) throw new Error("preflight pricing must be no more than 30 minutes old");
  const expectedFingerprint = sha256(canonicalJson({ followUp: inputs.fingerprint, mode: preflight.mode, source: source?.lineage.importedDigest ?? null }));
  if (preflight.inputFingerprint !== expectedFingerprint || preflight.followUpFingerprint !== inputs.fingerprint) throw new Error("follow-up inputs changed after preflight");
  if ((preflight.mode !== "ablation") !== Boolean(source)) throw new Error("preflight source mode and runner source disagree");
  if (source && preflight.sourceLineage?.importedDigest !== source.lineage.importedDigest) throw new Error("downloaded source artifact changed after preflight");
  const budget = effectiveNewBudgetPico();
  if (BigInt(preflight.effectiveBudgetPicoUsd) !== budget.budgetPico || BigInt(preflight.priorNewSpendPicoUsd) !== budget.priorNewSpendPico) throw new Error("budget inputs changed after preflight");
  if (usdToPico(ORIGINAL_ACTUAL_SPEND_USD) + budget.priorNewSpendPico + budget.budgetPico > usdToPico(CONFIG.overallHardCapUsd)) throw new Error(`cumulative $${CONFIG.overallHardCapUsd} cap is not preserved`);
  const expectedCalls = [
    ...(preflight.mode === "rejudge" ? [] : buildAblationPlan(inputs)),
    ...(preflight.mode === "ablation" ? [] : buildRejudgePlan(source)),
  ];
  const expectedRoles = preflight.mode === "ablation" ? ["candidate", "primaryJudge"] : preflight.mode === "rejudge" ? ["rejudge"] : ["candidate", "primaryJudge", "rejudge"];
  if (canonicalJson(preflight.modelResolutions.map((item) => item.role)) !== canonicalJson(expectedRoles)) throw new Error("preflight model-resolution roles/order drifted");
  for (const resolution of preflight.modelResolutions) {
    const role = CONFIG.roles[resolution.role];
    if (!role || resolution.requestedModel !== role.model || resolution.resolvedModel !== role.model || resolution.endpoint?.providerName !== role.providerName || resolution.endpoint?.tag !== role.endpointTag) throw new Error(`model resolution drift for ${resolution.role}`);
    if (canonicalJson(resolution.providerRouting?.only) !== canonicalJson([role.endpointTag]) || resolution.providerRouting?.allow_fallbacks !== false) throw new Error(`routing is not exact for ${resolution.role}`);
    if (canonicalJson(resolution.providerRouting?.max_price) !== canonicalJson(providerMaxPrice(resolution.endpoint))) throw new Error(`router price ceiling drift for ${resolution.role}`);
    if (resolution.seedSupported !== true || !role.requiredParameters.every((parameter) => resolution.endpoint.supportedParameters?.includes(parameter))) throw new Error(`required parameter support drift for ${resolution.role}`);
    if (["candidate", "primaryJudge", "rejudge"].includes(resolution.role) && role.endpointTag !== "openai") throw new Error("Luna must be pinned to standard openai, never openai/flex");
  }
  const resolutionByRole = Object.fromEntries(preflight.modelResolutions.map((item) => [item.role, item]));
  const recomputedCalls = expectedCalls.map((call) => {
    const maximumPico = routedCallMaximumPico(resolutionByRole[call.role].providerRouting.max_price, call.inputUpperTokens, call.maxOutputTokens);
    return { ...call, maximumCostPicoUsd: maximumPico.toString(), maximumCostUsd: picoToUsd(maximumPico) };
  });
  if (canonicalJson(preflight.calls) !== canonicalJson(recomputedCalls)) throw new Error("stored call maxima or deterministic bounds do not recompute from verified resolution prices");
  const recomputedStages = buildStages(recomputedCalls, budget.budgetPico);
  if (recomputedStages.errors.length || canonicalJson(preflight.stages) !== canonicalJson(recomputedStages.stages)) throw new Error("stored stage summaries do not recompute from verified calls");
}

function validationFrom(result, expectedResponses, scenario) {
  try {
    return validateJudgment(parseJsonResponse(result.content), expectedResponses, scenario);
  } catch (error) {
    return { valid: false, errors: [error.message], value: null, groundedHardFailures: [], untrustedHardFailureClaims: [] };
  }
}

function rounded(value) {
  return value === null ? null : Number(value.toFixed(4));
}

function mean(values) {
  return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
}

function sumPico(rows, key) {
  return rows.reduce((sum, row) => sum + BigInt(row[key] ?? 0), 0n);
}

function averagePico(rows, key) {
  return rows.length ? picoToUsd(sumPico(rows, key) / BigInt(rows.length)) : null;
}

function tokenSummary(rows, key) {
  const known = rows.map((row) => row[key]).filter((value) => Number.isInteger(value) && value >= 0);
  return { total: known.reduce((sum, value) => sum + value, 0), reportedCalls: known.length, missingCalls: rows.length - known.length };
}

function summarizeCostGroup(executedRows, plannedCalls) {
  const actualPico = sumPico(executedRows, "actualCostPicoUsd");
  const executedMaximumPico = sumPico(executedRows, "maximumCostPicoUsd");
  const plannedMaximumPico = sumPico(plannedCalls, "maximumCostPicoUsd");
  const actualValues = executedRows.map((row) => BigInt(row.actualCostPicoUsd));
  return {
    completedCalls: executedRows.length,
    plannedCalls: plannedCalls.length,
    actualCostUsd: picoToUsd(actualPico),
    averageActualCostPerCompletedCallUsd: averagePico(executedRows, "actualCostPicoUsd"),
    minimumActualCallCostUsd: actualValues.length ? picoToUsd(actualValues.reduce((low, value) => value < low ? value : low)) : null,
    maximumActualCallCostUsd: actualValues.length ? picoToUsd(actualValues.reduce((high, value) => value > high ? value : high)) : null,
    executedCallsConservativeMaximumUsd: picoToUsd(executedMaximumPico),
    fullPlanConservativeMaximumUsd: picoToUsd(plannedMaximumPico),
    actualToFullPlanMaximumRatio: plannedMaximumPico ? rounded(Number(actualPico) / Number(plannedMaximumPico)) : null,
    promptTokens: tokenSummary(executedRows, "promptTokens"),
    completionTokens: tokenSummary(executedRows, "completionTokens"),
    totalTokens: tokenSummary(executedRows, "totalTokens"),
    totalDurationMs: executedRows.reduce((sum, row) => sum + (Number.isFinite(row.durationMs) ? row.durationMs : 0), 0),
  };
}

function groupCost(rows, plannedCalls, key, values) {
  return values.map((value) => ({
    [key]: value,
    ...summarizeCostGroup(rows.filter((row) => row[key] === value), plannedCalls.filter((call) => call[key] === value)),
  }));
}

export function buildCostBaseline({ rows, preflight, budgetPico, accountingUncertain }) {
  const plannedCalls = preflight.calls;
  const stages = [...new Set(plannedCalls.map((call) => call.stage))].sort((left, right) => left - right);
  const roles = [...new Set(plannedCalls.map((call) => call.role))];
  const scenarios = [...new Set(plannedCalls.map((call) => call.scenarioId))];
  const roleRows = Object.fromEntries(roles.map((role) => [role, rows.filter((row) => row.role === role)]));
  const pairedRows = rows.filter((row) => row.stage === 1 || row.stage === 2);
  return {
    schemaVersion: 1,
    generatedAt: new Date().toISOString(),
    accountingComplete: !accountingUncertain,
    pricingBasis: "Actual cost is OpenRouter usage.cost. Conservative maxima use the live, preflight-verified standard OpenAI route price ceiling and deterministic token bounds.",
    modelResolutions: preflight.modelResolutions.map((resolution) => ({
      role: resolution.role,
      requestedModel: resolution.requestedModel,
      resolvedModel: resolution.resolvedModel,
      providerName: resolution.endpoint.providerName,
      endpointTag: resolution.endpoint.tag,
      maxPrice: resolution.providerRouting.max_price,
    })),
    budget: {
      thisRunHardCapUsd: picoToUsd(budgetPico),
      originalActualSpendUsd: ORIGINAL_ACTUAL_SPEND_USD,
      priorFollowUpSpendUsd: preflight.priorNewSpendUsd,
      cumulativeExperimentHardCapUsd: CONFIG.overallHardCapUsd,
    },
    overall: summarizeCostGroup(rows, plannedCalls),
    byStage: groupCost(rows, plannedCalls, "stage", stages),
    byRole: groupCost(rows, plannedCalls, "role", roles),
    byScenario: groupCost(rows, plannedCalls, "scenarioId", scenarios),
    normalizedUnits: {
      pairedScenarioCount: CONFIG.expectedScenarioCount,
      pairedCoreActualCostUsd: picoToUsd(sumPico(pairedRows, "actualCostPicoUsd")),
      pairedCoreActualCostPerScenarioUsd: picoToUsd(sumPico(pairedRows, "actualCostPicoUsd") / BigInt(CONFIG.expectedScenarioCount)),
      candidateResponseActualCostUsd: averagePico(roleRows.candidate ?? [], "actualCostPicoUsd"),
      primaryScenarioJudgmentActualCostUsd: averagePico(roleRows.primaryJudge ?? [], "actualCostPicoUsd"),
      archiveScenarioRejudgmentActualCostUsd: averagePico(roleRows.rejudge ?? [], "actualCostPicoUsd"),
    },
  };
}

export function compareArchiveJudgment(imported, lunaValidation) {
  const original = imported.originalJudgment?.value;
  if (!original || !lunaValidation?.valid) {
    return {
      status: "unavailable",
      reason: lunaValidation?.errors?.join("; ") ?? "Luna rejudge is invalid",
      originalValidationSha256: imported.originalJudgment?.validationSha256 ?? null,
    };
  }
  const originalByBlind = new Map(original.responses.map((result) => [result.blindId, result]));
  const lunaByBlind = new Map(lunaValidation.value.responses.map((result) => [result.blindId, result]));
  const rows = imported.responses.map(({ blindId, candidateCallId, variantId }) => {
    const oldResult = originalByBlind.get(blindId);
    const lunaResult = lunaByBlind.get(blindId);
    if (!oldResult || !lunaResult) throw new Error(`archive judgment comparison missing ${imported.scenario.id}/${blindId}`);
    const scoreDelta = Object.fromEntries(SCORE_DIMENSIONS.map((dimension) => [dimension, lunaResult.scores[dimension] - oldResult.scores[dimension]]));
    const originalHardFailureIds = oldResult.hardFailures.map((failure) => failure.id).sort();
    const lunaHardFailureIds = lunaResult.hardFailures.map((failure) => failure.id).sort();
    const originalSet = new Set(originalHardFailureIds);
    const lunaSet = new Set(lunaHardFailureIds);
    return {
      blindId,
      candidateCallId,
      variantId,
      original: {
        scores: oldResult.scores,
        aggregateScore: rounded(mean(SCORE_DIMENSIONS.map((dimension) => oldResult.scores[dimension]))),
        hardFailures: oldResult.hardFailures,
        confidence: oldResult.confidence,
        ambiguous: oldResult.ambiguous,
      },
      luna: {
        scores: lunaResult.scores,
        aggregateScore: rounded(mean(SCORE_DIMENSIONS.map((dimension) => lunaResult.scores[dimension]))),
        hardFailures: lunaResult.hardFailures,
        confidence: lunaResult.confidence,
        ambiguous: lunaResult.ambiguous,
      },
      scoreDelta,
      aggregateScoreDelta: rounded(mean(Object.values(scoreDelta))),
      confidenceDelta: lunaResult.confidence - oldResult.confidence,
      hardFailuresAddedByLuna: lunaHardFailureIds.filter((id) => !originalSet.has(id)),
      hardFailuresRemovedByLuna: originalHardFailureIds.filter((id) => !lunaSet.has(id)),
    };
  });
  const scoreDeltaMeans = Object.fromEntries(SCORE_DIMENSIONS.map((dimension) => [dimension, rounded(mean(rows.map((row) => row.scoreDelta[dimension])))]));
  const changedHardFailureRows = rows.filter((row) => row.hardFailuresAddedByLuna.length || row.hardFailuresRemovedByLuna.length).length;
  return {
    status: "complete",
    originalValidationSha256: imported.originalJudgment.validationSha256,
    originalReviewIssues: imported.originalJudgment.reviewIssues,
    comparedResponses: rows.length,
    rows,
    summary: {
      scoreDeltaMeans,
      meanAggregateScoreDelta: rounded(mean(rows.map((row) => row.aggregateScoreDelta))),
      originalHardFailureResponses: rows.filter((row) => row.original.hardFailures.length).length,
      lunaHardFailureResponses: rows.filter((row) => row.luna.hardFailures.length).length,
      changedHardFailureResponses: changedHardFailureRows,
      meanConfidenceOriginal: rounded(mean(rows.map((row) => row.original.confidence))),
      meanConfidenceLuna: rounded(mean(rows.map((row) => row.luna.confidence))),
      meanConfidenceDelta: rounded(mean(rows.map((row) => row.confidenceDelta))),
      ambiguousOriginal: rows.filter((row) => row.original.ambiguous).length,
      ambiguousLuna: rows.filter((row) => row.luna.ambiguous).length,
    },
  };
}

function safeInline(value, maximum = 320) {
  const normalized = String(value ?? "").replace(/\s+/g, " ").trim();
  const bounded = normalized.length <= maximum ? normalized : `${normalized.slice(0, Math.max(0, maximum - 1))}…`;
  return bounded.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll("@", "@&#8203;");
}

function renderSummary({ status, mode, ledger, budgetPico, aggregate, recommendation, rejudge, omittedRejudge, costBaseline, untrustedHardFailureClaims = [], fault }) {
  if (status !== "complete") return `# Agent OS follow-up\n\n- Status: **ABORTED**\n- Mode: **${mode}**\n- Recorded known new spend: **$${picoToUsd(ledger.actualPico)}** of **$${picoToUsd(budgetPico)}**\n- Unresolved exposure upper bound: **${ledger.unresolvedExposureUpperPico === null ? "none" : `$${picoToUsd(ledger.unresolvedExposureUpperPico)}`}**\n- Accounting: **${ledger.accountingUncertain ? "UNCERTAIN FOR FINAL ATTEMPT" : "complete for recorded responses"}**\n- Reason: <code>${safeInline(fault)}</code>\n\nPartial raw requests, responses, stage admissions, and the append-only ledger are preserved.\n`;
  const pairRows = aggregate?.pairDeltas?.map((item) => `| ${item.pairId} | ${item.pairRole} | ${item.meanDelta === null ? "n/a" : `${item.meanDelta >= 0 ? "+" : ""}${item.meanDelta.toFixed(4)}`} | ${item.wins}/${item.ties}/${item.losses} | ${item.medianReplicateDelta ?? "n/a"} | ${item.worstReplicateDelta ?? "n/a"} |`).join("\n") ?? "";
  const suppressors = recommendation?.suppressors?.length ? recommendation.suppressors.map((item) => `- ${item.type}${item.scenarioId ? `: ${item.scenarioId}` : ""}${item.reason || item.detail ? ` — ${safeInline(item.reason ?? item.detail)}` : ""}`).join("\n") : "- None";
  const ordered = [...(aggregate?.comparisons ?? [])].sort((left, right) => right.delta - left.delta);
  const representative = (comparison, label) => {
    if (!comparison) return `- ${label}: n/a`;
    const base = aggregate.rows.find((row) => row.scenarioId === comparison.scenarioId && row.replicateIndex === comparison.replicateIndex && row.treatmentId === "recipe-aware");
    const guarded = aggregate.rows.find((row) => row.scenarioId === comparison.scenarioId && row.replicateIndex === comparison.replicateIndex && row.treatmentId === "recipe-aware-guarded");
    return `- ${label} — **${comparison.scenarioId}, seed ${comparison.replicateIndex + 1}, delta ${comparison.delta >= 0 ? "+" : ""}${comparison.delta.toFixed(4)}**\n  - recipe-aware ${comparison.recipeAwarePrimaryScore}: <code>${safeInline(base?.summary)}</code>; raw \`raw/candidates/${comparison.scenarioId}/recipe-aware-seed-${comparison.replicateIndex + 1}.md\`\n  - guarded ${comparison.guardedPrimaryScore}: <code>${safeInline(guarded?.summary)}</code>; raw \`raw/candidates/${comparison.scenarioId}/recipe-aware-guarded-seed-${comparison.replicateIndex + 1}.md\`\n  - judge: \`raw/primaryJudge/${comparison.scenarioId}.validation.json\``;
  };
  const strongest = ordered[0] ? `${ordered[0].scenarioId} seed ${ordered[0].replicateIndex + 1}: ${ordered[0].delta >= 0 ? "+" : ""}${ordered[0].delta.toFixed(4)}` : "n/a";
  const weakest = ordered.at(-1) ? `${ordered.at(-1).scenarioId} seed ${ordered.at(-1).replicateIndex + 1}: ${ordered.at(-1).delta >= 0 ? "+" : ""}${ordered.at(-1).delta.toFixed(4)}` : "n/a";
  const representativeRows = [representative(ordered[0], "Strongest gain"), representative(ordered.at(-1), "Worst case")].join("\n");
  const pairedFailureRows = (aggregate?.hardFailures ?? []).map((failure) => {
    const row = aggregate.rows.find((item) => item.scenarioId === failure.scenarioId && item.treatmentId === failure.treatmentId && item.replicateIndex === failure.replicateIndex);
    const rawPath = `raw/candidates/${failure.scenarioId}/${failure.treatmentId}-seed-${failure.replicateIndex + 1}.md`;
    return `- ${failure.scenarioId} / ${failure.treatmentId} / seed ${failure.replicateIndex + 1}: **${failure.id}** — <code>${safeInline(failure.evidence)}</code>; judge rationale: <code>${safeInline(row?.summary)}</code>; raw: \`${rawPath}\`, \`raw/primaryJudge/${failure.scenarioId}.validation.json\``;
  });
  const rejudgeFailureRows = rejudge.flatMap((result) => result.groundedHardFailures.map((failure) => `- archive ${result.scenarioId} / ${failure.blindId}: **${failure.id}** — <code>${safeInline(failure.evidence)}</code>; raw: \`raw/rejudge/${result.scenarioId}.validation.json\``));
  const untrustedRows = untrustedHardFailureClaims.map((item) => `- **UNTRUSTED (invalid judgment)** ${item.phase} / ${item.scenarioId} / ${item.blindId}: ${item.id} — <code>${safeInline(item.evidence)}</code>; raw: \`raw/${item.phase === "primary-judge" ? "primaryJudge" : "rejudge"}/${item.scenarioId}.validation.json\``);
  const cutoffRows = (aggregate?.diagnostics ?? []).filter((item) => item.type === "apiLengthCutoff" || item.type === "reviewTruncation").map((item) => `- ${item.type}: ${item.scenarioId} / ${item.treatmentId} / seed ${item.replicateIndex + 1}; raw: \`raw/candidates/${item.scenarioId}/${item.treatmentId}-seed-${item.replicateIndex + 1}.md\``);
  for (const item of recommendation?.suppressors ?? []) {
    if (item.type === "judgeLengthCutoff") cutoffRows.push(`- judgeLengthCutoff: ${item.scenarioId}; raw: \`raw/primaryJudge/${item.scenarioId}.validation.json\``);
    if (!aggregate && (item.type === "apiLengthCutoff" || item.type === "reviewTruncation")) cutoffRows.push(`- ${item.type}: ${item.scenarioId} / ${item.treatmentId} / seed ${item.replicateIndex + 1}; raw: \`raw/candidates/${item.scenarioId}/${item.treatmentId}-seed-${item.replicateIndex + 1}.md\``);
  }
  for (const result of rejudge) {
    if (result.judgmentFinishReason === "length") cutoffRows.push(`- archive judgeLengthCutoff: ${result.scenarioId}; raw: \`raw/rejudge/${result.scenarioId}.validation.json\``);
    for (const sourceResponse of result.sourceResponses.filter((item) => item.finishReason === "length")) cutoffRows.push(`- archive source apiLengthCutoff: ${result.scenarioId} / ${sourceResponse.candidateCallId}; exact imported response: \`imported-source-lineage.json\``);
  }
  const archiveRows = rejudge
    .filter((result) => result.comparison?.status === "complete")
    .map((result) => {
      const comparison = result.comparison.summary;
      const delta = comparison.meanAggregateScoreDelta;
      const confidenceDelta = comparison.meanConfidenceDelta;
      return `| ${result.scenarioId} | ${delta >= 0 ? "+" : ""}${delta.toFixed(4)} | ${comparison.originalHardFailureResponses} → ${comparison.lunaHardFailureResponses} | ${comparison.changedHardFailureResponses} | ${confidenceDelta >= 0 ? "+" : ""}${confidenceDelta.toFixed(4)} |`;
    })
    .join("\n");
  const archiveCaveat = mode === "ablation"
    ? "No archive rejudge ran in ablation-only mode."
    : "The archive comparison tests judge-family sensitivity only on old Nemotron candidates; it does not cross-validate the new Luna-candidate/Luna-judge ablation.";
  const stageLabels = { 1: "candidate generation", 2: "primary judging", 3: "archive rejudging" };
  const costRows = costBaseline.byStage.map((row) => `| ${row.stage}: ${stageLabels[row.stage] ?? "stage"} | ${row.completedCalls}/${row.plannedCalls} | ${row.promptTokens.total} | ${row.completionTokens.total} | $${row.actualCostUsd} | $${row.fullPlanConservativeMaximumUsd} |`).join("\n");
  return `# Agent OS follow-up

- Status: **COMPLETE**
- Mode: **${mode}**
- Actual new spend: **$${picoToUsd(ledger.actualPico)}** of **$${picoToUsd(budgetPico)}**
- Recommendation: **${recommendation?.selectedTreatment ?? "suppressed / diagnostic only"}**
- Archive rejudge: **${rejudge.length} completed; ${rejudge.filter((item) => item.comparison?.status === "complete").length} validated Luna-vs-Nemotron comparisons; ${omittedRejudge.length} omitted by fixed-prefix budget admission**
- Strongest paired gain: **${strongest}**
- Worst paired case: **${weakest}**

## Cost baseline

- Actual / full-plan conservative maximum: **$${costBaseline.overall.actualCostUsd} / $${costBaseline.overall.fullPlanConservativeMaximumUsd}**
- Paired core cost per scenario: **$${costBaseline.normalizedUnits.pairedCoreActualCostPerScenarioUsd}**
- Average candidate response: **$${costBaseline.normalizedUnits.candidateResponseActualCostUsd ?? "n/a"}**
- Average primary scenario judgment: **$${costBaseline.normalizedUnits.primaryScenarioJudgmentActualCostUsd ?? "n/a"}**
- Average archive scenario rejudgment: **$${costBaseline.normalizedUnits.archiveScenarioRejudgmentActualCostUsd ?? "n/a"}**

| Stage | Completed/planned calls | Prompt tokens | Completion tokens | Actual cost | Full-plan maximum |
|---|---:|---:|---:|---:|---:|
${costRows}

Detailed role- and scenario-level measurements are in \`cost-baseline.json\`.

| Contrast pair | Preregistered role | Mean delta | W/T/L | Median replicate | Worst replicate |
|---|---|---:|---:|---:|---:|
${pairRows || "| n/a | n/a | n/a | n/a | n/a | n/a |"}

## Representative paired evidence

${representativeRows}

## Recommendation rationale

${safeInline(recommendation?.rationale)}

## Suppressors

${suppressors}

## Grounded hard failures and judge rationale

${[...pairedFailureRows, ...rejudgeFailureRows, ...untrustedRows].join("\n") || "- None"}

## Cutoffs and review truncations

${cutoffRows.join("\n") || "- None"}

## Archive judge-family sensitivity (old candidates only)

| Scenario | Luna − original mean score | HF responses, original → Luna | HF responses changed | Confidence delta |
|---|---:|---:|---:|---:|
${archiveRows || "| n/a | n/a | n/a | n/a | n/a |"}

All ten rubric scores remain in the evidence artifact. Headline deltas use only each scenario's preregistered focused dimensions, averaged within scenario and then within contrast pair. Any grounded hard failure in either paired arm suppresses automated selection for manual audit; its direction remains diagnostic. Candidate and blind primary judge use the same Luna model family, so correlated errors are a limitation. ${archiveCaveat}
`;
}

export async function runExperiment(options = parseArgs(process.argv.slice(2))) {
  const preflight = JSON.parse(await readFile(options.preflight, "utf8"));
  await assertFreshRunOutput(options.out);
  const inputs = await loadFollowUpInputs();
  const source = preflight.mode === "ablation" ? null : await loadSourceArtifact(options.source ?? "");
  verifyPreflight(preflight, inputs, source);
  const apiKey = process.env.OPENROUTER_API_KEY;
  if (!apiKey) throw new Error("OPENROUTER_API_KEY is required");
  await mkdir(options.out, { recursive: true });
  const budgetPico = BigInt(preflight.effectiveBudgetPicoUsd);
  const ledger = new SpendLedger({ outputDir: options.out, budgetPico, resolutions: preflight.modelResolutions, apiKey });
  await Promise.all([writeFile(ledger.ledgerPath, "", { flag: "wx" }), writeFile(ledger.callsPath, "", { flag: "wx" })]);
  const manifestCore = {
    schemaVersion: CONFIG.schemaVersion,
    generatedAt: new Date().toISOString(),
    mode: preflight.mode,
    inputFingerprint: preflight.inputFingerprint,
    preflight: { integrity: preflight.integrity, generatedAt: preflight.generatedAt, effectiveBudgetUsd: preflight.effectiveBudgetUsd, stages: preflight.stages },
    provenance: { repository: process.env.GITHUB_REPOSITORY ?? null, sha: process.env.GITHUB_SHA ?? null, ref: process.env.GITHUB_REF ?? null, runId: process.env.GITHUB_RUN_ID ?? null, runAttempt: process.env.GITHUB_RUN_ATTEMPT ?? null },
    sourceLineage: source?.lineage ?? null,
    sourceFiles: inputs.sourceFiles,
    treatments: inputs.treatments.map((item) => ({ id: item.id, rank: item.rank, contextBytes: Buffer.byteLength(item.text, "utf8"), contextSha256: sha256(item.text) })),
    scenarioIds: inputs.scenarios.map((scenario) => scenario.id),
    callPlanDigest: sha256(canonicalJson(preflight.calls)),
  };
  const manifest = { ...manifestCore, integrity: sha256(canonicalJson(manifestCore)) };
  await writeFile(path.join(options.out, "manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`, { flag: "wx" });
  if (source) await writeFile(path.join(options.out, "imported-source-lineage.json"), `${JSON.stringify({ lineage: source.lineage, scenarios: source.scenarios }, null, 2)}\n`, { flag: "wx" });

  const candidates = new Map();
  const candidateOutputs = new Map();
  const judgePlans = new Map();
  const judgments = new Map();
  const rejudgeResults = [];
  const selectedRejudge = [];
  const omittedRejudge = [];
  try {
    const stage1 = preflight.calls.filter((call) => call.stage === 1);
    if (stage1.length) ledger.admitFullStage(1, stage1);
    for (const planCall of stage1) {
      const scenario = inputs.scenarios.find((item) => item.id === planCall.scenarioId);
      const treatment = inputs.treatments.find((item) => item.id === planCall.treatmentId);
      const result = await ledger.execute(planCall, buildCandidateMessages(scenario, treatment.text));
      candidates.set(planCall.id, { ...planCall, finishReason: result.ledgerRow.finishReason, systemFingerprint: result.ledgerRow.systemFingerprint });
      candidateOutputs.set(planCall.id, result.content);
      const readableDir = path.join(options.out, "raw", "candidates", scenario.id);
      await mkdir(readableDir, { recursive: true });
      await writeFile(path.join(readableDir, `${treatment.id}-seed-${planCall.replicateIndex + 1}.md`), `${result.content}\n`);
    }

    const staticStage2 = preflight.calls.filter((call) => call.stage === 2);
    const primaryResolution = preflight.modelResolutions.find((item) => item.role === "primaryJudge");
    const preparedStage2 = staticStage2.map((staticCall) => {
      const scenario = inputs.scenarios.find((item) => item.id === staticCall.scenarioId);
      const blinded = staticCall.blinded.map((item) => {
        const normalized = normalizeReviewText(candidateOutputs.get(item.candidateCallId));
        const review = truncateUtf8(normalized, CONFIG.candidateReviewBytes);
        return { ...item, content: review.text, truncated: review.truncated, originalBytes: review.originalBytes, lengthLimited: candidates.get(item.candidateCallId)?.finishReason === "length" };
      });
      const messages = buildJudgeMessages(scenario, blinded);
      const responseFormat = judgeResponseFormat(scenario, blinded.map((item) => item.blindId));
      const inputUpperTokens = requestInputTokenUpperBound(messages, responseFormat);
      if (inputUpperTokens > staticCall.inputUpperTokens || inputUpperTokens > CONFIG.roles.primaryJudge.maxInputUpperTokens) {
        throw new Error(`${staticCall.id} actual judge envelope exceeds its static preflight bound`);
      }
      const maximumPico = routedCallMaximumPico(primaryResolution.providerRouting.max_price, inputUpperTokens, staticCall.maxOutputTokens);
      if (maximumPico > BigInt(staticCall.maximumCostPicoUsd)) throw new Error(`${staticCall.id} dynamic maximum exceeds static preflight maximum`);
      return { scenario, blinded, messages, responseFormat, planCall: { ...staticCall, inputUpperTokens, maximumCostPicoUsd: maximumPico.toString(), maximumCostUsd: picoToUsd(maximumPico), staticMaximumCostUsd: staticCall.maximumCostUsd } };
    });
    const preparedJudgePlans = new Map(preparedStage2.map((prepared) => [prepared.scenario.id, { ...prepared.planCall, blinded: prepared.blinded }]));
    const stage2Admission = preparedStage2.length ? ledger.assessConditionalFullStage(2, preparedStage2.map((item) => item.planCall)) : null;
    const admittedStage2 = stage2Admission?.admitted ? preparedStage2 : [];
    for (const prepared of admittedStage2) {
      const { scenario, blinded, messages, responseFormat, planCall } = prepared;
      const result = await ledger.execute(planCall, messages, responseFormat);
      const validation = validationFrom(result, blinded, scenario);
      const record = { ...validation, finishReason: result.ledgerRow.finishReason, systemFingerprint: result.ledgerRow.systemFingerprint, raw: result.content };
      judgePlans.set(scenario.id, { ...planCall, blinded });
      judgments.set(scenario.id, record);
      const validationDir = path.join(options.out, "raw", "primaryJudge");
      await mkdir(validationDir, { recursive: true });
      await writeFile(path.join(validationDir, `${scenario.id}.validation.json`), `${JSON.stringify(record, null, 2)}\n`);
    }

    const stage3 = preflight.calls.filter((call) => call.stage === 3);
    const prefix = stage3.length ? ledger.admitPriorityPrefix(3, stage3) : [];
    selectedRejudge.push(...prefix);
    omittedRejudge.push(...stage3.filter((call) => !prefix.includes(call)));
    const sourceById = new Map((source?.scenarios ?? []).map((item) => [item.scenario.id, item]));
    for (const planCall of prefix) {
      const imported = sourceById.get(planCall.scenarioId);
      if (!imported) throw new Error(`missing imported source scenario ${planCall.scenarioId}`);
      const exactResponses = imported.responses.map((response) => ({ blindId: response.blindId, content: response.content, lengthLimited: response.finishReason === "length", truncated: false }));
      const responseFormat = judgeResponseFormat(imported.scenario, exactResponses.map((item) => item.blindId));
      const result = await ledger.execute(planCall, buildJudgeMessages(imported.scenario, exactResponses), responseFormat);
      const validation = validationFrom(result, exactResponses, imported.scenario);
      const comparison = compareArchiveJudgment(imported, validation);
      const record = {
        scenarioId: planCall.scenarioId,
        rejudgePriority: planCall.rejudgePriority,
        sourceResponses: imported.responses.map(({ blindId, candidateCallId, variantId, contentBytes, contentSha256, finishReason }) => ({ blindId, candidateCallId, variantId, contentBytes, contentSha256, finishReason })),
        judgmentFinishReason: result.ledgerRow.finishReason,
        judgmentSystemFingerprint: result.ledgerRow.systemFingerprint,
        ...validation,
        comparison,
        raw: result.content,
      };
      rejudgeResults.push(record);
      const validationDir = path.join(options.out, "raw", "rejudge");
      await mkdir(validationDir, { recursive: true });
      await writeFile(path.join(validationDir, `${planCall.scenarioId}.validation.json`), `${JSON.stringify(record, null, 2)}\n`);
    }

    let aggregate = null;
    let recommendation;
    const pairedDiagnostics = admittedStage2.length ? [] : collectPairedDiagnostics({ inputs, judgePlans: preparedJudgePlans, candidates });
    const rejudgeDiagnostics = [];
    if (stage2Admission && !stage2Admission.admitted) pairedDiagnostics.push({ type: "stageOmitted", stage: 2, reason: "actual stage-1 spend plus recomputed full stage-2 maximum exceeded the this-run budget" });
    for (const [scenarioId, judgment] of judgments) {
      if (judgment.finishReason === "length") pairedDiagnostics.push({ type: "judgeLengthCutoff", phase: "primary-judge", scenarioId });
    }
    for (const result of rejudgeResults) {
      if (!result.valid) rejudgeDiagnostics.push({ type: "invalidJudgment", phase: "rejudge", scenarioId: result.scenarioId, errors: result.errors });
      if (result.judgmentFinishReason === "length") rejudgeDiagnostics.push({ type: "judgeLengthCutoff", phase: "rejudge", scenarioId: result.scenarioId });
      if (result.groundedHardFailures.length) rejudgeDiagnostics.push({ type: "judgeDetectedGroundedHardFailure", phase: "rejudge", scenarioId: result.scenarioId, count: result.groundedHardFailures.length });
      for (const judged of result.value?.responses ?? []) {
        if (judged.ambiguous) rejudgeDiagnostics.push({ type: "judgeAmbiguous", phase: "rejudge", scenarioId: result.scenarioId, blindId: judged.blindId });
        if (judged.confidence <= 1) rejudgeDiagnostics.push({ type: "judgeLowConfidence", phase: "rejudge", scenarioId: result.scenarioId, blindId: judged.blindId, confidence: judged.confidence });
      }
      for (const sourceResponse of result.sourceResponses) if (sourceResponse.finishReason === "length") rejudgeDiagnostics.push({ type: "apiLengthCutoff", phase: "source-candidate", scenarioId: result.scenarioId, candidateCallId: sourceResponse.candidateCallId });
    }
    if (admittedStage2.length) {
      aggregate = aggregatePaired({ inputs, judgePlans, judgments, candidates });
      recommendation = recommendPaired(aggregate, pairedDiagnostics);
    } else if (staticStage2.length) {
      recommendation = { selectedTreatment: null, status: "suppressed", provisional: true, rationale: "Paired selection is suppressed because the full blind-judge stage was not admitted after actual candidate spend; no partial paired judgment was attempted.", suppressors: pairedDiagnostics };
    } else {
      const suppressors = [...rejudgeDiagnostics];
      if (!rejudgeResults.length) suppressors.push({ type: "incompletePairedEvidence", detail: "no archive rejudge call fit the budget" });
      recommendation = { selectedTreatment: null, status: "diagnostic-only", provisional: true, rationale: "Archive rejudging is diagnostic and cannot select an ablation treatment.", suppressors };
    }
    const untrustedHardFailureClaims = [
      ...[...judgments].flatMap(([scenarioId, judgment]) => (judgment.untrustedHardFailureClaims ?? []).map((claim) => ({ phase: "primary-judge", scenarioId, errors: judgment.errors, ...claim }))),
      ...rejudgeResults.flatMap((result) => (result.untrustedHardFailureClaims ?? []).map((claim) => ({ phase: "rejudge", scenarioId: result.scenarioId, errors: result.errors, ...claim }))),
    ];
    const costBaseline = buildCostBaseline({ rows: ledger.rows, preflight, budgetPico, accountingUncertain: ledger.accountingUncertain });
    const summary = renderSummary({ status: "complete", mode: preflight.mode, ledger, budgetPico, aggregate, recommendation, rejudge: rejudgeResults, omittedRejudge, costBaseline, untrustedHardFailureClaims });
    await Promise.all([
      writeFile(path.join(options.out, "cost-baseline.json"), `${JSON.stringify(costBaseline, null, 2)}\n`),
      writeFile(path.join(options.out, "paired-metrics.json"), `${JSON.stringify(aggregate, null, 2)}\n`),
      writeFile(path.join(options.out, "rejudge.json"), `${JSON.stringify({ sourceLineage: source?.lineage ?? null, diagnostics: rejudgeDiagnostics, results: rejudgeResults, selectedCallIds: selectedRejudge.map((call) => call.id), omittedCallIds: omittedRejudge.map((call) => call.id) }, null, 2)}\n`),
      writeFile(path.join(options.out, "recommendation.json"), `${JSON.stringify(recommendation, null, 2)}\n`),
      writeFile(path.join(options.out, "hard-failures.json"), `${JSON.stringify({ paired: aggregate?.hardFailures ?? [], rejudge: rejudgeResults.flatMap((result) => result.groundedHardFailures.map((failure) => ({ scenarioId: result.scenarioId, ...failure }))) }, null, 2)}\n`),
      writeFile(path.join(options.out, "untrusted-hard-failure-claims.json"), `${JSON.stringify(untrustedHardFailureClaims, null, 2)}\n`),
      writeFile(path.join(options.out, "blind-map.json"), `${JSON.stringify(Object.fromEntries([...judgePlans].map(([id, plan]) => [id, plan.blinded.map(({ blindId, candidateCallId }) => ({ blindId, candidateCallId }))])), null, 2)}\n`),
      writeFile(path.join(options.out, "stage-admissions.json"), `${JSON.stringify(ledger.stageAdmissions, null, 2)}\n`),
      writeFile(path.join(options.out, "summary.md"), summary),
      writeFile(path.join(options.out, "status.json"), `${JSON.stringify({ status: "complete", mode: preflight.mode, actualNewSpendUsd: picoToUsd(ledger.actualPico), fullPlanConservativeMaximumUsd: costBaseline.overall.fullPlanConservativeMaximumUsd, pairedCoreActualCostPerScenarioUsd: costBaseline.normalizedUnits.pairedCoreActualCostPerScenarioUsd, originalActualSpendUsd: ORIGINAL_ACTUAL_SPEND_USD, priorNewSpendUsd: preflight.priorNewSpendUsd, cumulativeActualSpendUsd: picoToUsd(usdToPico(ORIGINAL_ACTUAL_SPEND_USD) + BigInt(preflight.priorNewSpendPicoUsd) + ledger.actualPico), budgetUsd: picoToUsd(budgetPico), recommendation: recommendation.selectedTreatment, selectedRejudgeCalls: selectedRejudge.length, omittedRejudgeCalls: omittedRejudge.length }, null, 2)}\n`),
    ]);
    console.log(`follow-up complete: $${picoToUsd(ledger.actualPico)} new spend; recommendation ${recommendation.selectedTreatment ?? "suppressed"}; ${rejudgeResults.length} archive rejudges`);
    return { aggregate, recommendation, rejudge: rejudgeResults, actualNewSpendUsd: picoToUsd(ledger.actualPico) };
  } catch (error) {
    const costBaseline = buildCostBaseline({ rows: ledger.rows, preflight, budgetPico, accountingUncertain: ledger.accountingUncertain });
    const summary = renderSummary({ status: "aborted", mode: preflight.mode, ledger, budgetPico, fault: error.message, aggregate: null, recommendation: null, rejudge: rejudgeResults, omittedRejudge });
    await Promise.all([
      writeFile(path.join(options.out, "cost-baseline.json"), `${JSON.stringify(costBaseline, null, 2)}\n`),
      writeFile(path.join(options.out, "stage-admissions.json"), `${JSON.stringify(ledger.stageAdmissions, null, 2)}\n`),
      writeFile(path.join(options.out, "summary.md"), summary),
      writeFile(path.join(options.out, "status.json"), `${JSON.stringify({ status: "aborted", mode: preflight.mode, reason: error.message, recordedKnownNewSpendUsd: picoToUsd(ledger.actualPico), unresolvedExposureUpperUsd: ledger.unresolvedExposureUpperPico === null ? null : picoToUsd(ledger.unresolvedExposureUpperPico), cumulativeKnownSpendUsd: picoToUsd(usdToPico(ORIGINAL_ACTUAL_SPEND_USD) + BigInt(preflight.priorNewSpendPicoUsd) + ledger.actualPico), cumulativeExposureUpperUsd: ledger.unresolvedExposureUpperPico === null ? null : picoToUsd(usdToPico(ORIGINAL_ACTUAL_SPEND_USD) + BigInt(preflight.priorNewSpendPicoUsd) + ledger.unresolvedExposureUpperPico), budgetUsd: picoToUsd(budgetPico), accountingUncertain: ledger.accountingUncertain }, null, 2)}\n`),
    ]);
    throw error;
  }
}

const isMain = process.argv[1] && path.resolve(process.argv[1]) === path.resolve(fileURLToPath(import.meta.url));
if (isMain) runExperiment().catch((error) => { console.error(`follow-up aborted: ${error.message}`); process.exitCode = 1; });
