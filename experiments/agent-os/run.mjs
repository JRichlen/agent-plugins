import { appendFile, mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  CONFIG,
  EXPERIMENT_DIR,
  HARD_FAILURES,
  SCORE_DIMENSIONS,
  buildArbiterMessages,
  buildCandidateMessages,
  buildJudgeMessages,
  canonicalJson,
  inputTokenUpperBound,
  loadExperimentInputs,
  normalizeReviewText,
  picoToUsd,
  seedFor,
  sha256,
  truncateUtf8,
  usdToPico,
} from "./config.mjs";

function parseArgs(argv) {
  const options = { preflight: path.join(EXPERIMENT_DIR, "results", "preflight.json"), out: null };
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === "--preflight") options.preflight = path.resolve(argv[++index] ?? "");
    else if (argument === "--out") options.out = path.resolve(argv[++index] ?? "");
    else if (argument === "--help") {
      console.log("usage: node experiments/agent-os/run.mjs [--preflight FILE] [--out DIR]");
      process.exit(0);
    } else throw new Error(`unknown argument: ${argument}`);
  }
  if (!options.preflight) throw new Error("--preflight requires a file");
  options.out ??= path.dirname(options.preflight);
  return options;
}

function safeName(value) {
  return value.replace(/[^a-zA-Z0-9._-]+/g, "-");
}

function extractContent(envelope) {
  const content = envelope?.choices?.[0]?.message?.content;
  if (typeof content === "string") return content;
  if (Array.isArray(content)) return content.map((part) => part?.text ?? "").join("");
  return "";
}

function responseProvenance(envelope) {
  const available = envelope?.openrouter_metadata?.endpoints?.available;
  const selected = Array.isArray(available) ? available.filter((endpoint) => endpoint?.selected === true) : [];
  if (selected.length > 1) {
    return { provider: null, model: null, error: `router metadata marked ${selected.length} endpoints selected` };
  }
  const metadataProvider = selected[0]?.provider;
  const legacyProvider = envelope?.provider;
  if (
    typeof metadataProvider === "string" &&
    typeof legacyProvider === "string" &&
    metadataProvider.toLowerCase() !== legacyProvider.toLowerCase()
  ) {
    return { provider: null, model: selected[0]?.model ?? null, error: "router metadata and legacy provider disagree" };
  }
  const provider = metadataProvider ?? legacyProvider ?? null;
  return {
    provider,
    model: selected[0]?.model ?? null,
    error: provider ? null : "response contains neither selected router metadata nor a legacy provider field",
  };
}

function parseJsonResponse(text) {
  const trimmed = String(text ?? "").trim();
  const withoutFence = trimmed
    .replace(/^```(?:json)?\s*/i, "")
    .replace(/\s*```$/, "")
    .trim();
  return JSON.parse(withoutFence);
}

function mean(values) {
  return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
}

function rounded(value) {
  return value === null ? null : Number(value.toFixed(4));
}

const FAILURE_SCORE_CONFLICTS = Object.freeze({
  actorAutomationConflation: ["taxonomyCorrectness"],
  mandatoryDisciplinePrimitive: ["ontologyMinimality", "workingDisciplineNeutrality"],
  harnessNativeOntology: ["taxonomyCorrectness", "ontologyMinimality"],
  scheduleAsDependency: ["dependencyModeling"],
  inventedAdapterCapability: ["crossHarnessHonesty"],
  desiredOverwritesObserved: ["evidenceAwareness", "humanGatedMutation"],
  observedOverwritesDesired: ["evidenceAwareness", "humanGatedMutation"],
  ungatedStructuralMutation: ["humanGatedMutation"],
  privacyBoundaryCrossing: ["humanGatedMutation"],
  recipeOwnsTrigger: ["taxonomyCorrectness", "recipeAutomationDistinction"],
  recipeAutomationCollapsed: ["taxonomyCorrectness", "recipeAutomationDistinction"],
  unsupportedRuntimeEvidence: ["evidenceAwareness"],
  dependencyPolarityReversed: ["dependencyModeling"],
  independentJobsCollapsed: ["taxonomyCorrectness"],
  compilerBoundaryViolation: ["existingCapabilityReuse"],
  capabilityReimplementation: ["existingCapabilityReuse"],
  evidenceOverclaimOrDismissal: ["evidenceAwareness"],
  interrogationBoundaryViolation: ["existingCapabilityReuse"],
  missingAutomationDiff: ["actionability"],
});

function validateJudgment(value, expectedResponses, scenario) {
  const schemaErrors = [];
  const reviewIssues = [];
  const allowedHardFailures = new Set([
    ...Object.keys(HARD_FAILURES),
    ...(scenario.judge?.hardFailures ?? []).map((failure) => failure.id),
  ]);
  if (!value || typeof value !== "object" || !Array.isArray(value.responses)) {
    return { valid: false, schemaErrors: ["top-level responses must be an array"], reviewIssues, value: null };
  }
  if (value.responses.length !== expectedResponses.length) {
    schemaErrors.push(`expected ${expectedResponses.length} judged responses, got ${value.responses.length}`);
  }
  const expected = new Map(expectedResponses.map((item) => [item.blindId, item.content]));
  const seen = new Set();
  for (const result of value.responses) {
    if (!result || typeof result !== "object" || !expected.has(result.blindId) || seen.has(result.blindId)) {
      schemaErrors.push(`invalid or duplicate blindId ${result?.blindId}`);
      continue;
    }
    seen.add(result.blindId);
    const keys = result.scores && typeof result.scores === "object" ? Object.keys(result.scores).sort() : [];
    if (canonicalJson(keys) !== canonicalJson([...SCORE_DIMENSIONS].sort())) {
      schemaErrors.push(`${result.blindId} scores must contain exactly all ten rubric keys`);
    } else {
      for (const dimension of SCORE_DIMENSIONS) {
        const score = result.scores[dimension];
        if (!Number.isInteger(score) || score < 0 || score > 4) {
          schemaErrors.push(`${result.blindId}.${dimension} must be an integer 0..4`);
        }
      }
    }
    if (!Array.isArray(result.hardFailures)) schemaErrors.push(`${result.blindId}.hardFailures must be an array`);
    else {
      const seenFailureIds = new Set();
      for (const failure of result.hardFailures) {
        if (!failure || !allowedHardFailures.has(failure.id)) {
          schemaErrors.push(`${result.blindId} has unknown hard failure ${failure?.id}`);
          continue;
        }
        if (seenFailureIds.has(failure.id)) {
          schemaErrors.push(`${result.blindId} repeats hard failure ${failure.id}`);
          continue;
        }
        seenFailureIds.add(failure.id);
        if (typeof failure.evidence !== "string" || !failure.evidence.trim()) {
          schemaErrors.push(`${result.blindId}.${failure.id} requires evidence`);
        } else if (!expected.get(result.blindId).includes(failure.evidence)) {
          reviewIssues.push({ type: "ungroundedHardFailure", blindId: result.blindId, failureId: failure.id });
        }
        for (const dimension of FAILURE_SCORE_CONFLICTS[failure.id] ?? []) {
          if (Number.isInteger(result.scores?.[dimension]) && result.scores[dimension] >= 3) {
            reviewIssues.push({ type: "scoreHardFailureConflict", blindId: result.blindId, failureId: failure.id, dimension });
          }
        }
      }
    }
    if (!Number.isInteger(result.confidence) || result.confidence < 0 || result.confidence > 4) {
      schemaErrors.push(`${result.blindId}.confidence must be an integer 0..4`);
    } else if (result.confidence <= CONFIG.lowConfidenceThreshold) {
      reviewIssues.push({ type: "lowConfidence", blindId: result.blindId, confidence: result.confidence });
    }
    if (typeof result.ambiguous !== "boolean") schemaErrors.push(`${result.blindId}.ambiguous must be boolean`);
    else if (result.ambiguous) reviewIssues.push({ type: "judgeAmbiguous", blindId: result.blindId });
    if (typeof result.summary !== "string") schemaErrors.push(`${result.blindId}.summary must be a string`);
  }
  for (const blindId of expected.keys()) if (!seen.has(blindId)) schemaErrors.push(`missing blindId ${blindId}`);
  if (schemaErrors.length === 0) {
    const ranked = value.responses
      .map((result) => ({
        blindId: result.blindId,
        scoreTotal: SCORE_DIMENSIONS.reduce((sum, key) => sum + result.scores[key], 0),
      }))
      .sort((left, right) => right.scoreTotal - left.scoreTotal);
    const scoreGap = ranked.length > 1 ? ranked[0].scoreTotal - ranked[1].scoreTotal : null;
    const closeScoreTotal = CONFIG.closeScoreMargin * SCORE_DIMENSIONS.length;
    if (scoreGap !== null && scoreGap <= closeScoreTotal) {
      reviewIssues.push({
        type: "closeScoreMargin",
        blindIds: [ranked[0].blindId, ranked[1].blindId],
        margin: rounded(scoreGap / SCORE_DIMENSIONS.length),
      });
    }
  }
  return { valid: schemaErrors.length === 0, schemaErrors, reviewIssues, value };
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
  }

  async execute(planCall, messages, actualCallId = planCall.id, seed = planCall.seed) {
    const maximumPico = BigInt(planCall.maximumCostPicoUsd);
    if (this.actualPico + maximumPico > this.budgetPico) {
      throw new Error(
        `budget guard stopped ${actualCallId}: $${picoToUsd(this.actualPico)} spent + $${picoToUsd(maximumPico)} call maximum > $${picoToUsd(this.budgetPico)}`,
      );
    }
    const roleConfig = CONFIG.roles[planCall.role];
    const resolution = this.resolutions[planCall.role];
    const inputUpperTokens = inputTokenUpperBound(messages);
    if (inputUpperTokens > planCall.inputUpperTokens) {
      throw new Error(`${actualCallId} input upper bound ${inputUpperTokens} exceeds reserved ${planCall.inputUpperTokens}`);
    }

    const body = {
      model: resolution.resolvedModel,
      messages,
      max_tokens: roleConfig.maxTokens,
      temperature: CONFIG.temperature,
      reasoning: CONFIG.reasoning,
      stream: false,
      usage: { include: true },
      provider: resolution.providerRouting,
    };
    if (resolution.seedSupported) body.seed = seed;
    if (planCall.role !== "candidate") body.response_format = { type: "json_object" };

    const rawDir = path.join(this.outputDir, "raw", planCall.role);
    await mkdir(rawDir, { recursive: true });
    const fileBase = path.join(rawDir, safeName(actualCallId));
    const startedAt = new Date().toISOString();
    const start = performance.now();
    let response;
    let responseText;
    let envelope;
    try {
      response = await fetch(`${CONFIG.apiBase}/chat/completions`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${this.apiKey}`,
          "Content-Type": "application/json",
          "X-OpenRouter-Metadata": "enabled",
          "HTTP-Referer": "https://github.com/JRichlen/agent-plugins",
          "X-OpenRouter-Title": "Agent OS design experiment",
        },
        body: JSON.stringify(body),
        signal: AbortSignal.timeout(180_000),
      });
      responseText = await response.text();
      try {
        envelope = JSON.parse(responseText);
      } catch {
        throw new Error(`${actualCallId} returned non-JSON (HTTP ${response.status})`);
      }
    } catch (error) {
      this.accountingUncertain = true;
      const evidenceWrites = [writeFile(`${fileBase}.request.json`, `${JSON.stringify(body, null, 2)}\n`)];
      if (responseText !== undefined) evidenceWrites.push(writeFile(`${fileBase}.response.txt`, responseText));
      await Promise.all(evidenceWrites);
      await appendFile(
        this.callsPath,
        `${JSON.stringify({ sequence: ++this.sequence, callId: actualCallId, phase: planCall.phase, status: "transport-fault", startedAt, maximumCostExposureUsd: planCall.maximumCostUsd, accountingUncertain: true, error: error.message })}\n`,
      );
      throw error;
    }

    await Promise.all([
      writeFile(`${fileBase}.request.json`, `${JSON.stringify(body, null, 2)}\n`),
      writeFile(`${fileBase}.response.json`, `${JSON.stringify(envelope, null, 2)}\n`),
    ]);

    if (!response.ok) {
      this.accountingUncertain = true;
      await appendFile(
        this.callsPath,
        `${JSON.stringify({ sequence: ++this.sequence, callId: actualCallId, phase: planCall.phase, status: "http-fault", httpStatus: response.status, startedAt, maximumCostExposureUsd: planCall.maximumCostUsd, accountingUncertain: true, error: envelope?.error?.message ?? responseText })}\n`,
      );
      throw new Error(`${actualCallId} failed HTTP ${response.status}: ${envelope?.error?.message ?? "unknown error"}`);
    }
    const usageCost = envelope?.usage?.cost;
    if (usageCost === undefined || usageCost === null || !Number.isFinite(Number(usageCost)) || Number(usageCost) < 0) {
      this.accountingUncertain = true;
      await appendFile(
        this.callsPath,
        `${JSON.stringify({ sequence: ++this.sequence, callId: actualCallId, phase: planCall.phase, status: "usage-fault", startedAt, maximumCostExposureUsd: planCall.maximumCostUsd, accountingUncertain: true, error: "missing or invalid OpenRouter usage.cost" })}\n`,
      );
      throw new Error(`${actualCallId} has no valid OpenRouter usage.cost; aborting fail-closed`);
    }
    const costPico = usdToPico(usageCost);
    this.actualPico += costPico;
    const responseErrors = [];
    const provenance = responseProvenance(envelope);
    if (![resolution.resolvedModel, resolution.canonicalSlug].includes(envelope.model)) {
      responseErrors.push(`returned unexpected model ${envelope.model}`);
    }
    if (provenance.error) responseErrors.push(provenance.error);
    if (
      typeof provenance.provider === "string" &&
      provenance.provider.toLowerCase() !== resolution.endpoint.providerName.toLowerCase()
    ) {
      responseErrors.push(`returned unexpected provider ${provenance.provider}`);
    }
    if (
      provenance.model &&
      ![resolution.resolvedModel, resolution.canonicalSlug, envelope.model].includes(provenance.model)
    ) {
      responseErrors.push(`router metadata selected unexpected model ${provenance.model}`);
    }
    if (costPico > maximumPico) responseErrors.push("actual usage.cost exceeded its conservative preflight maximum");
    if (this.actualPico > this.budgetPico) responseErrors.push("hard budget exceeded after the response");

    const durationMs = Math.round(performance.now() - start);
    const ledgerRow = {
      sequence: ++this.sequence,
      callId: actualCallId,
      phase: planCall.phase,
      scenarioId: planCall.scenarioId,
      variantId: planCall.variantId ?? null,
      requestedModel: resolution.requestedModel,
      returnedModel: envelope.model,
      requestedEndpoint: resolution.endpoint.tag,
      returnedProvider: provenance.provider,
      routerSelectedModel: provenance.model,
      routerAttempt: envelope?.openrouter_metadata?.attempt ?? null,
      generationId: envelope.id ?? null,
      promptTokens: envelope.usage.prompt_tokens ?? null,
      completionTokens: envelope.usage.completion_tokens ?? null,
      totalTokens: envelope.usage.total_tokens ?? null,
      actualCostUsd: String(usageCost),
      actualCostPicoUsd: costPico.toString(),
      cumulativeCostUsd: picoToUsd(this.actualPico),
      maximumCostUsd: planCall.maximumCostUsd,
      startedAt,
      durationMs,
      finishReason: envelope.choices?.[0]?.finish_reason ?? null,
    };
    await Promise.all([
      appendFile(this.ledgerPath, `${JSON.stringify(ledgerRow)}\n`),
      appendFile(
        this.callsPath,
        `${JSON.stringify({ ...ledgerRow, status: responseErrors.length ? "response-fault" : "success", errors: responseErrors })}\n`,
      ),
    ]);
    if (responseErrors.length) throw new Error(`${actualCallId} ${responseErrors.join("; ")}`);
    return { envelope, content: extractContent(envelope), inputUpperTokens, ledgerRow };
  }
}

function verifyPreflight(preflight, inputFingerprint) {
  const { integrity, ...core } = preflight;
  if (sha256(canonicalJson(core)) !== integrity) throw new Error("preflight integrity hash does not match");
  if (preflight.status !== "pass") throw new Error("preflight did not pass");
  const preflightAgeMs = Date.now() - Date.parse(preflight.generatedAt);
  if (!Number.isFinite(preflightAgeMs) || preflightAgeMs < 0 || preflightAgeMs > 30 * 60 * 1_000) {
    throw new Error("preflight pricing snapshot must be valid and no more than 30 minutes old");
  }
  if (preflight.inputFingerprint !== inputFingerprint) {
    throw new Error("scenarios, variants, or config changed after preflight; rerun preflight");
  }
  if (preflight.counts?.candidates !== 24 || preflight.counts?.judges !== 6 || preflight.counts?.arbiters !== 1) {
    throw new Error("preflight must reserve exactly 24 candidates, 6 judges, and at most 1 arbiter");
  }
  if (BigInt(preflight.maximumCostPicoUsd) > BigInt(preflight.effectiveBudgetPicoUsd)) {
    throw new Error("preflight maximum exceeds its effective budget");
  }
  if (BigInt(preflight.effectiveBudgetPicoUsd) > usdToPico(CONFIG.hardBudgetUsd)) {
    throw new Error("preflight effective budget exceeds the immutable $0.05 cap");
  }
}

function aggregateEvidence({ inputs, judgePlans, finalJudgments, candidates }) {
  const rows = [];
  const hardFailures = [];
  for (const scenario of inputs.scenarios) {
    const plan = judgePlans.get(scenario.id);
    const judgment = finalJudgments.get(scenario.id);
    if (!plan || !judgment?.valid) continue;
    const byBlindId = new Map(judgment.value.responses.map((item) => [item.blindId, item]));
    for (const blind of plan.blinded) {
      const result = byBlindId.get(blind.blindId);
      const candidatePlan = candidates.get(blind.candidateCallId);
      if (!result || !candidatePlan) continue;
      const scores = Object.fromEntries(SCORE_DIMENSIONS.map((dimension) => [dimension, result.scores[dimension]]));
      const aggregateScore = mean(Object.values(scores));
      const row = {
        scenarioId: scenario.id,
        variantId: candidatePlan.variantId,
        blindId: blind.blindId,
        scores,
        aggregateScore: rounded(aggregateScore),
        hardFailureCount: result.hardFailures.length,
        hardFailureIds: [...new Set(result.hardFailures.map((failure) => failure.id))].sort(),
        confidence: result.confidence,
        ambiguous: result.ambiguous,
        finishReason: candidatePlan.finishReason ?? null,
        contentTruncatedForReview: Boolean(blind.truncated),
        summary: result.summary,
      };
      rows.push(row);
      for (const failure of result.hardFailures) {
        hardFailures.push({ scenarioId: scenario.id, variantId: candidatePlan.variantId, blindId: blind.blindId, ...failure });
      }
    }
  }

  const treatments = inputs.variants.map((variant) => {
    const treatmentRows = rows.filter((row) => row.variantId === variant.id);
    const dimensionMeans = Object.fromEntries(
      SCORE_DIMENSIONS.map((dimension) => [dimension, rounded(mean(treatmentRows.map((row) => row.scores[dimension])))]),
    );
    return {
      variantId: variant.id,
      rank: variant.rank,
      contextBytes: Buffer.byteLength(variant.text, "utf8"),
      contextSha256: sha256(variant.text),
      scoredScenarios: treatmentRows.length,
      complete: treatmentRows.length === inputs.scenarios.length,
      meanScore: rounded(mean(treatmentRows.map((row) => row.aggregateScore))),
      dimensionMeans,
      hardFailureCount: hardFailures.filter((failure) => failure.variantId === variant.id).length,
      hardFailureResponses: treatmentRows.filter((row) => row.hardFailureCount > 0).length,
      lengthLimitedResponses: treatmentRows.filter((row) => row.finishReason === "length").length,
      reviewTruncatedResponses: treatmentRows.filter((row) => row.contentTruncatedForReview).length,
    };
  });
  const baseline = treatments.find((item) => item.variantId === "baseline");
  for (const treatment of treatments) {
    treatment.liftVsBaseline =
      treatment.meanScore === null || baseline?.meanScore === null
        ? null
        : rounded(treatment.meanScore - baseline.meanScore);
  }

  const scenarioDeltas = [];
  for (const scenario of inputs.scenarios) {
    const scenarioRows = rows.filter((row) => row.scenarioId === scenario.id);
    const baselineRow = scenarioRows.find((row) => row.variantId === "baseline");
    for (const row of scenarioRows) {
      const baselineFailureIds = new Set(baselineRow?.hardFailureIds ?? []);
      const newHardFailureIds = row.hardFailureIds.filter((id) => !baselineFailureIds.has(id));
      scenarioDeltas.push({
        scenarioId: scenario.id,
        variantId: row.variantId,
        score: row.aggregateScore,
        deltaVsBaseline: baselineRow ? rounded(row.aggregateScore - baselineRow.aggregateScore) : null,
        hardFailureCount: row.hardFailureCount,
        baselineHardFailureCount: baselineRow?.hardFailureCount ?? null,
        newHardFailureIds,
        newHardFailure: Boolean(baselineRow && newHardFailureIds.length > 0),
      });
    }
  }
  return { rows, treatments, scenarioDeltas, hardFailures };
}

function recommend(aggregate) {
  const baseline = aggregate.treatments.find((item) => item.variantId === "baseline");
  const candidates = aggregate.treatments.filter(
    (item) =>
      item.variantId !== "baseline" &&
      item.complete &&
      item.liftVsBaseline >= CONFIG.usefulLift &&
      item.hardFailureCount <= (baseline?.hardFailureCount ?? 0) &&
      !aggregate.scenarioDeltas.some((delta) => delta.variantId === item.variantId && delta.newHardFailure),
  );
  if (!candidates.length) {
    return {
      selectedVariant: "baseline",
      evidenceBand: "weak",
      rationale: "No larger treatment earned at least +0.15 mean lift without adding a hard failure; keep the default context minimal and inspect raw examples.",
      provisional: true,
    };
  }
  const bestScore = Math.max(...candidates.map((item) => item.meanScore));
  const selected = candidates
    .filter((item) => rounded(bestScore - item.meanScore) <= CONFIG.nearBestMargin)
    .sort((left, right) => left.rank - right.rank)[0];
  return {
    selectedVariant: selected.variantId,
    evidenceBand: selected.liftVsBaseline > CONFIG.strongLift ? "strong-signal-unreplicated" : "useful",
    rationale: `${selected.variantId} is the smallest treatment within ${CONFIG.nearBestMargin.toFixed(2)} of the best qualifying score, with ${selected.liftVsBaseline >= 0 ? "+" : ""}${selected.liftVsBaseline.toFixed(2)} mean lift and no new hard failure.${selected.liftVsBaseline > CONFIG.strongLift ? " The magnitude is a strong signal, but one smoke run is not repeatability evidence." : ""}`,
    provisional: true,
  };
}

function excerpt(value, maximum = 600) {
  const normalized = String(value ?? "").replace(/\s+/g, " ").trim();
  return normalized.length <= maximum ? normalized : `${normalized.slice(0, maximum - 1)}…`;
}

function safeInline(value, maximum = 600) {
  return excerpt(value, maximum)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;")
    .replaceAll("@", "@&#8203;");
}

function renderSummary({ status, spendPico, budgetPico, aggregate, recommendation, arbitration, representative, fault, accountingUncertain = false }) {
  if (status !== "complete") {
    return `# Agent OS experiment summary\n\n- Status: **ABORTED**\n- Recorded OpenRouter spend: **$${picoToUsd(spendPico)}** of **$${picoToUsd(budgetPico)}**\n- Cost accounting: **${accountingUncertain ? "UNRESOLVED FOR THE FINAL ATTEMPT" : "COMPLETE FOR ALL RESPONSES"}**\n- Reason: ${safeInline(fault)}\n\nPartial raw evidence and the append-only call log are preserved. The pre-spend reservation keeps even an unresolved final attempt inside the hard budget. Do not interpret incomplete aggregates.\n`;
  }
  const rows = aggregate.treatments
    .map(
      (item) =>
        `| ${item.variantId} | ${item.contextBytes} | ${item.meanScore?.toFixed(3) ?? "n/a"} | ${item.liftVsBaseline === null ? "n/a" : `${item.liftVsBaseline >= 0 ? "+" : ""}${item.liftVsBaseline.toFixed(3)}`} | ${item.hardFailureCount} | ${item.lengthLimitedResponses} | ${item.reviewTruncatedResponses} | ${item.scoredScenarios}/${CONFIG.expectedScenarioCount} |`,
    )
    .join("\n");
  const strongest = [...aggregate.scenarioDeltas]
    .filter((item) => item.variantId !== "baseline" && item.deltaVsBaseline !== null)
    .sort((left, right) => Math.abs(right.deltaVsBaseline) - Math.abs(left.deltaVsBaseline))
    .slice(0, 5)
    .map((item) => `- ${item.scenarioId} / ${item.variantId}: ${item.deltaVsBaseline >= 0 ? "+" : ""}${item.deltaVsBaseline.toFixed(3)}`)
    .join("\n");
  const failures = aggregate.hardFailures.length
    ? aggregate.hardFailures
        .slice(0, 8)
        .map((item) => `- ${item.scenarioId} / ${item.variantId}: ${item.id} — <code>${safeInline(item.evidence, 180)}</code>`)
        .join("\n")
    : "- None judged.";
  const success = representative?.strongestSuccess;
  const weakness = representative?.representativeWeakness;
  const representativeRows = [
    success
      ? `- Largest treatment delta — ${success.scenarioId} / ${success.variantId} (${success.deltaVsBaseline >= 0 ? "+" : ""}${success.deltaVsBaseline.toFixed(3)}): <code>${safeInline(success.rawCandidateResponse, 240)}</code>`
      : "- Largest treatment delta: unavailable.",
    weakness
      ? `- Representative weakness — ${weakness.scenarioId} / ${weakness.variantId} (${weakness.hardFailureId ?? `delta ${weakness.deltaVsBaseline >= 0 ? "+" : ""}${weakness.deltaVsBaseline.toFixed(3)}`}): <code>${safeInline(weakness.rawCandidateResponse, 240)}</code>`
      : "- Representative weakness: unavailable.",
  ].join("\n");
  return `# Agent OS experiment summary

- Status: **COMPLETE**
- Actual OpenRouter spend: **$${picoToUsd(spendPico)}** of **$${picoToUsd(budgetPico)}**
- Arbitration: ${arbitration}
- Recommendation: **${recommendation.selectedVariant}** (${recommendation.evidenceBand}, provisional)
- Candidate cutoffs: **${aggregate.rows.filter((item) => item.finishReason === "length").length}/${aggregate.rows.length} API length-limited; ${aggregate.rows.filter((item) => item.contentTruncatedForReview).length}/${aggregate.rows.length} truncated for blind review**

| Treatment | Context bytes | Mean score (all 10 dimensions) | Lift vs baseline | Hard failures | API length-limited | Review-truncated | Scored scenarios |
|---|---:|---:|---:|---:|---:|---:|---:|
${rows}

## Strongest scenario deltas

${strongest || "- No scored deltas."}

## Hard failures

${failures}

## Representative raw excerpts

${representativeRows}

## Recommendation

${recommendation.rationale}

This is exploratory n=1 design evidence. Inspect representative raw responses and judgments before changing implementation direction.
`;
}

export async function runExperiment(options = parseArgs(process.argv.slice(2))) {
  const outputDir = options.out;
  await mkdir(outputDir, { recursive: true });
  const preflight = JSON.parse(await readFile(options.preflight, "utf8"));
  const inputs = await loadExperimentInputs();
  verifyPreflight(preflight, inputs.fingerprint);
  const apiKey = process.env.OPENROUTER_API_KEY;
  if (!apiKey) throw new Error("OPENROUTER_API_KEY is required");
  const budgetPico = BigInt(preflight.effectiveBudgetPicoUsd);
  const ledger = new SpendLedger({ outputDir, budgetPico, resolutions: preflight.modelResolutions, apiKey });
  const scenarioSource = await readFile(path.join(EXPERIMENT_DIR, "scenarios.json"), "utf8");
  const manifestCore = {
    schemaVersion: CONFIG.schemaVersion,
    generatedAt: new Date().toISOString(),
    inputFingerprint: inputs.fingerprint,
    preflight: {
      integrity: preflight.integrity,
      generatedAt: preflight.generatedAt,
      maximumCostUsd: preflight.maximumCostUsd,
      effectiveBudgetUsd: preflight.effectiveBudgetUsd,
    },
    provenance: {
      repository: process.env.GITHUB_REPOSITORY ?? null,
      sha: process.env.GITHUB_SHA ?? null,
      ref: process.env.GITHUB_REF ?? null,
      runId: process.env.GITHUB_RUN_ID ?? null,
      runAttempt: process.env.GITHUB_RUN_ATTEMPT ?? null,
    },
    scenarioSource: {
      file: "experiments/agent-os/scenarios.json",
      bytes: Buffer.byteLength(scenarioSource, "utf8"),
      sha256: sha256(scenarioSource),
    },
    modelResolutions: preflight.modelResolutions,
    variants: inputs.variants.map((variant) => ({
      id: variant.id,
      rank: variant.rank,
      file: `experiments/agent-os/${variant.file}`,
      contextBytes: Buffer.byteLength(variant.text, "utf8"),
      contextSha256: sha256(variant.text),
    })),
    candidatePrompts: inputs.scenarios.flatMap((scenario) =>
      inputs.variants.map((variant) => {
        const messages = buildCandidateMessages(scenario, variant.text);
        const serialized = canonicalJson(messages);
        return {
          scenarioId: scenario.id,
          variantId: variant.id,
          scenarioPromptSha256: sha256(scenario.prompt),
          renderedMessagesBytes: Buffer.byteLength(serialized, "utf8"),
          renderedMessagesSha256: sha256(serialized),
          inputUpperTokens: inputTokenUpperBound(messages),
        };
      }),
    ),
  };
  const manifest = { ...manifestCore, integrity: sha256(canonicalJson(manifestCore)) };
  await Promise.all([
    writeFile(path.join(outputDir, "ledger.jsonl"), ""),
    writeFile(path.join(outputDir, "calls.jsonl"), ""),
    writeFile(path.join(outputDir, "manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`),
  ]);
  const plannedCalls = new Map(preflight.calls.map((call) => [call.id, call]));
  const candidatePlans = new Map();
  const candidateOutputs = new Map();
  const judgePlans = new Map();
  const primaryJudgments = new Map();
  const finalJudgments = new Map();
  let arbitration = "not needed";

  try {
    for (const planCall of preflight.calls.filter((call) => call.phase === "candidate")) {
      const scenario = inputs.scenarios.find((item) => item.id === planCall.scenarioId);
      const variant = inputs.variants.find((item) => item.id === planCall.variantId);
      const messages = buildCandidateMessages(scenario, variant.text);
      const result = await ledger.execute(planCall, messages);
      candidatePlans.set(planCall.id, { ...planCall, finishReason: result.ledgerRow.finishReason });
      candidateOutputs.set(planCall.id, result.content);
      const candidateDir = path.join(outputDir, "raw", "candidates", scenario.id);
      await mkdir(candidateDir, { recursive: true });
      await writeFile(path.join(candidateDir, `${variant.id}.md`), `${result.content}\n`);
    }

    for (const planCall of preflight.calls.filter((call) => call.phase === "judge")) {
      const scenario = inputs.scenarios.find((item) => item.id === planCall.scenarioId);
      const blinded = planCall.blinded.map((item) => {
        const reviewText = normalizeReviewText(candidateOutputs.get(item.candidateCallId));
        const truncated = truncateUtf8(reviewText, CONFIG.candidateBytesVisibleToJudge);
        return {
          ...item,
          content: truncated.text,
          truncated: truncated.truncated,
          originalBytes: truncated.originalBytes,
          lengthLimited: candidatePlans.get(item.candidateCallId)?.finishReason === "length",
        };
      });
      const messages = buildJudgeMessages(scenario, blinded);
      const result = await ledger.execute(planCall, messages);
      let parsed;
      let validation;
      try {
        parsed = parseJsonResponse(result.content);
        validation = validateJudgment(parsed, blinded, scenario);
      } catch (error) {
        validation = { valid: false, schemaErrors: [error.message], reviewIssues: [], value: null };
      }
      judgePlans.set(scenario.id, { ...planCall, blinded });
      primaryJudgments.set(scenario.id, { ...validation, raw: result.content });
      finalJudgments.set(scenario.id, validation);
      await writeFile(
        path.join(outputDir, "raw", "judge", `${scenario.id}.validation.json`),
        `${JSON.stringify(validation, null, 2)}\n`,
      );
    }

    const arbitrationCandidates = inputs.scenarios
      .map((scenario, index) => {
        const judgment = primaryJudgments.get(scenario.id);
        const blockingIssues = judgment.reviewIssues.filter((issue) => issue.type !== "closeScoreMargin");
        const hasCloseScore = judgment.reviewIssues.some((issue) => issue.type === "closeScoreMargin");
        const priority = !judgment.valid
          ? 0
          : blockingIssues.some((issue) => issue.type === "ungroundedHardFailure")
            ? 1
            : blockingIssues.length
              ? 2
              : hasCloseScore
                ? 3
                : 99;
        return { scenario, index, judgment, priority, arbiterPriority: scenario.arbiterPriority };
      })
      .filter((item) => item.priority < 99)
      .sort(
        (left, right) =>
          left.priority - right.priority ||
          left.arbiterPriority - right.arbiterPriority ||
          left.index - right.index,
      );

    if (arbitrationCandidates.length && CONFIG.maxArbiterCalls > 0) {
      const target = arbitrationCandidates[0];
      const judgePlan = judgePlans.get(target.scenario.id);
      const primaryText = truncateUtf8(
        normalizeReviewText(target.judgment.raw),
        CONFIG.judgeBytesVisibleToArbiter,
      ).text;
      const messages = buildArbiterMessages(target.scenario, judgePlan.blinded, primaryText);
      const reserve = plannedCalls.get("arbiter:reserve");
      const arbiterCall = { ...reserve, scenarioId: target.scenario.id, seed: seedFor(target.index, "arbiter") };
      const result = await ledger.execute(arbiterCall, messages, `arbiter:${target.scenario.id}`, arbiterCall.seed);
      let validation;
      try {
        validation = validateJudgment(parseJsonResponse(result.content), judgePlan.blinded, target.scenario);
      } catch (error) {
        validation = { valid: false, schemaErrors: [error.message], reviewIssues: [], value: null };
      }
      await writeFile(
        path.join(outputDir, "raw", "arbiter", `${target.scenario.id}.validation.json`),
        `${JSON.stringify(validation, null, 2)}\n`,
      );
      const blockingArbiterIssues = validation.reviewIssues.filter((issue) => issue.type !== "closeScoreMargin");
      if (validation.valid && blockingArbiterIssues.length === 0) {
        finalJudgments.set(target.scenario.id, validation);
        arbitration = `used for ${target.scenario.id}`;
      } else arbitration = `attempted for ${target.scenario.id}, but arbiter output remained invalid or conflicted`;
      if (arbitrationCandidates.length > 1) arbitration += `; ${arbitrationCandidates.length - 1} additional flagged scenario(s) remain unarbitrated`;
    } else if (arbitrationCandidates.length) {
      arbitration = `${arbitrationCandidates.length} flagged scenario(s), no arbiter budget reserved`;
    }

    const unresolvedJudgments = inputs.scenarios
      .map((scenario) => ({ scenarioId: scenario.id, judgment: finalJudgments.get(scenario.id) }))
      .filter(({ judgment }) => !judgment?.valid || judgment.reviewIssues.some((issue) => issue.type !== "closeScoreMargin"));
    if (unresolvedJudgments.length) {
      throw new Error(
        `cannot publish complete aggregates: unresolved judgments for ${unresolvedJudgments.map((item) => item.scenarioId).join(", ")}`,
      );
    }

    const aggregate = aggregateEvidence({
      inputs,
      judgePlans,
      finalJudgments,
      candidates: candidatePlans,
    });
    const recommendation = recommend(aggregate);
    const strongestSuccessDelta = [...aggregate.scenarioDeltas]
        .filter((item) => item.variantId !== "baseline" && item.deltaVsBaseline > 0)
        .sort((left, right) => right.deltaVsBaseline - left.deltaVsBaseline)[0] ?? null;
    const representativeFailure = aggregate.hardFailures[0] ?? null;
    const weakestDelta = [...aggregate.scenarioDeltas]
      .filter((item) => item.variantId !== "baseline" && item.deltaVsBaseline !== null)
      .sort((left, right) => left.deltaVsBaseline - right.deltaVsBaseline)[0] ?? null;
    const responseFor = (scenarioId, variantId) => {
      const plan = [...candidatePlans.values()].find(
        (item) => item.scenarioId === scenarioId && item.variantId === variantId,
      );
      return plan ? candidateOutputs.get(plan.id) ?? null : null;
    };
    const representative = {
      strongestSuccess: strongestSuccessDelta
        ? {
            ...strongestSuccessDelta,
            rawCandidateResponse: responseFor(strongestSuccessDelta.scenarioId, strongestSuccessDelta.variantId),
            judgment: aggregate.rows.find(
              (item) =>
                item.scenarioId === strongestSuccessDelta.scenarioId &&
                item.variantId === strongestSuccessDelta.variantId,
            ),
          }
        : null,
      representativeWeakness: representativeFailure
        ? {
            ...representativeFailure,
            hardFailureId: representativeFailure.id,
            deltaVsBaseline:
              aggregate.scenarioDeltas.find(
                (item) =>
                  item.scenarioId === representativeFailure.scenarioId &&
                  item.variantId === representativeFailure.variantId,
              )?.deltaVsBaseline ?? null,
            rawCandidateResponse: responseFor(representativeFailure.scenarioId, representativeFailure.variantId),
            judgment: aggregate.rows.find(
              (item) =>
                item.scenarioId === representativeFailure.scenarioId &&
                item.variantId === representativeFailure.variantId,
            ),
          }
        : weakestDelta
          ? {
              ...weakestDelta,
              hardFailureId: null,
              rawCandidateResponse: responseFor(weakestDelta.scenarioId, weakestDelta.variantId),
              judgment: aggregate.rows.find(
                (item) => item.scenarioId === weakestDelta.scenarioId && item.variantId === weakestDelta.variantId,
              ),
            }
          : null,
    };
    const summary = renderSummary({
      status: "complete",
      spendPico: ledger.actualPico,
      budgetPico,
      aggregate,
      recommendation,
      arbitration,
      representative,
    });
    await Promise.all([
      writeFile(path.join(outputDir, "aggregate.json"), `${JSON.stringify({ rows: aggregate.rows, treatments: aggregate.treatments }, null, 2)}\n`),
      writeFile(path.join(outputDir, "scenario-deltas.json"), `${JSON.stringify(aggregate.scenarioDeltas, null, 2)}\n`),
      writeFile(path.join(outputDir, "hard-failures.json"), `${JSON.stringify(aggregate.hardFailures, null, 2)}\n`),
      writeFile(path.join(outputDir, "recommendation.json"), `${JSON.stringify(recommendation, null, 2)}\n`),
      writeFile(path.join(outputDir, "representative-examples.json"), `${JSON.stringify(representative, null, 2)}\n`),
      writeFile(path.join(outputDir, "summary.md"), summary),
      writeFile(
        path.join(outputDir, "status.json"),
        `${JSON.stringify({ status: "complete", actualSpendUsd: picoToUsd(ledger.actualPico), budgetUsd: picoToUsd(budgetPico), arbitration, lengthLimitedCandidates: aggregate.rows.filter((item) => item.finishReason === "length").length, reviewTruncatedCandidates: aggregate.rows.filter((item) => item.contentTruncatedForReview).length }, null, 2)}\n`,
      ),
      writeFile(
        path.join(outputDir, "blind-map.json"),
        `${JSON.stringify(Object.fromEntries([...judgePlans].map(([id, plan]) => [id, plan.blinded.map(({ blindId, candidateCallId }) => ({ blindId, candidateCallId }))])), null, 2)}\n`,
      ),
    ]);
    console.log(`experiment complete: actual spend $${picoToUsd(ledger.actualPico)}; recommendation ${recommendation.selectedVariant}`);
    return { aggregate, recommendation, actualSpendUsd: picoToUsd(ledger.actualPico) };
  } catch (error) {
    const summary = renderSummary({
      status: "aborted",
      spendPico: ledger.actualPico,
      budgetPico,
      aggregate: null,
      recommendation: null,
      arbitration,
      fault: error.message,
      accountingUncertain: ledger.accountingUncertain,
    });
    await Promise.all([
      writeFile(path.join(outputDir, "summary.md"), summary),
      writeFile(
        path.join(outputDir, "status.json"),
        `${JSON.stringify({ status: "aborted", reason: error.message, recordedSpendUsd: picoToUsd(ledger.actualPico), accountingUncertain: ledger.accountingUncertain, budgetUsd: picoToUsd(budgetPico) }, null, 2)}\n`,
      ),
    ]);
    throw error;
  }
}

const isMain = process.argv[1] && path.resolve(process.argv[1]) === path.resolve(fileURLToPath(import.meta.url));
if (isMain) {
  runExperiment().catch((error) => {
    console.error(`experiment aborted: ${error.message}`);
    process.exitCode = 1;
  });
}
