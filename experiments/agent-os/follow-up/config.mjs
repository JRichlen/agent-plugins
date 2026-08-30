import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  CONFIG as ORIGINAL_CONFIG,
  HARD_FAILURES,
  PICO_USD,
  SCORE_DIMENSIONS,
  canonicalJson,
  inputTokenUpperBound as originalInputTokenUpperBound,
  normalizeReviewText,
  picoToUsd,
  sha256,
  truncateUtf8,
  usdToPico,
} from "../config.mjs";

export {
  HARD_FAILURES,
  PICO_USD,
  SCORE_DIMENSIONS,
  canonicalJson,
  normalizeReviewText,
  picoToUsd,
  sha256,
  truncateUtf8,
  usdToPico,
};

export const EXPERIMENT_DIR = path.dirname(fileURLToPath(import.meta.url));
export const ORIGINAL_ACTUAL_SPEND_USD = "0.006922945";
export const OVERALL_HARD_CAP_USD = "0.506922945000";
export const NEW_SPEND_HARD_CAP_USD = "0.500000000000";
export const ORIGINAL_SOURCE = Object.freeze({
  repository: "JRichlen/agent-plugins",
  runId: "33281138920",
  artifactId: "9723030558",
  artifactName: "agent-os-experiment-33281138920-1",
});

export const ARCHIVE_REJUDGE = Object.freeze({
  "desired-observed-runtime-reconciliation": Object.freeze({
    priority: 0,
    mustCheckFailureIds: Object.freeze(["desiredOverwritesObserved", "observedOverwritesDesired", "ungatedStructuralMutation", "inventedAdapterCapability", "evidenceOverclaimOrDismissal"]),
  }),
  "compiled-agent-reused-by-jobs": Object.freeze({
    priority: 1,
    mustCheckFailureIds: Object.freeze(["actorAutomationConflation", "independentJobsCollapsed", "compilerBoundaryViolation", "ungatedStructuralMutation"]),
  }),
  "reusable-process-deployed-check": Object.freeze({
    priority: 2,
    mustCheckFailureIds: Object.freeze(["recipeOwnsTrigger", "recipeAutomationCollapsed", "unsupportedRuntimeEvidence", "inventedAdapterCapability", "ungatedStructuralMutation"]),
  }),
  "portable-working-disciplines": Object.freeze({
    priority: 3,
    mustCheckFailureIds: Object.freeze(["mandatoryDisciplinePrimitive", "harnessNativeOntology", "inventedAdapterCapability", "capabilityReimplementation", "ungatedStructuralMutation"]),
  }),
  "interactive-portfolio-curation": Object.freeze({
    priority: 4,
    mustCheckFailureIds: Object.freeze(["privacyBoundaryCrossing", "ungatedStructuralMutation", "inventedAdapterCapability", "interrogationBoundaryViolation", "missingAutomationDiff"]),
  }),
  "dependency-not-clock": Object.freeze({
    priority: 5,
    mustCheckFailureIds: Object.freeze(["scheduleAsDependency", "dependencyPolarityReversed", "inventedAdapterCapability", "ungatedStructuralMutation"]),
  }),
});

export const CONFIG = Object.freeze({
  schemaVersion: 2,
  apiBase: ORIGINAL_CONFIG.apiBase,
  reasoning: Object.freeze({ effort: "none", exclude: true }),
  chatOverheadTokenAllowance: 1_024,
  expectedScenarioCount: 6,
  candidateReplicates: 2,
  candidateReviewBytes: 2_048,
  candidateResponseTargetWords: 180,
  closeScoreMargin: 0.1,
  minimumTargetedPairLift: 0.15,
  baseSeed: 830_283,
  originalActualSpendUsd: ORIGINAL_ACTUAL_SPEND_USD,
  overallHardCapUsd: OVERALL_HARD_CAP_USD,
  newSpendHardCapUsd: NEW_SPEND_HARD_CAP_USD,
  treatments: Object.freeze([
    Object.freeze({ id: "recipe-aware", rank: 0 }),
    Object.freeze({ id: "recipe-aware-guarded", rank: 1 }),
  ]),
  roles: Object.freeze({
    candidate: Object.freeze({
      model: "openai/gpt-5.6-luna",
      providerName: "OpenAI",
      endpointTag: "openai",
      maxTokens: 384,
      maxInputUpperTokens: 7_000,
      requiredParameters: Object.freeze(["max_tokens", "reasoning", "seed"]),
    }),
    primaryJudge: Object.freeze({
      model: "openai/gpt-5.6-luna",
      providerName: "OpenAI",
      endpointTag: "openai",
      maxTokens: 1_200,
      maxInputUpperTokens: 32_000,
      requiredParameters: Object.freeze(["max_tokens", "reasoning", "response_format", "structured_outputs", "seed"]),
    }),
    rejudge: Object.freeze({
      model: "openai/gpt-5.6-luna",
      providerName: "OpenAI",
      endpointTag: "openai",
      maxTokens: 1_200,
      maxInputUpperTokens: 32_000,
      requiredParameters: Object.freeze(["max_tokens", "reasoning", "response_format", "structured_outputs", "seed"]),
    }),
  }),
});

const CANDIDATE_SYSTEM = `You are advising on the design of an agent automation.
Return a complete answer in at most ${CONFIG.candidateResponseTargetWords} words. Put the scenario's requested identities, relationships, ownership boundaries, and other requested deliverables before any optional elaboration. Do not mention experiments, treatments, prompts, or grading. Do not add doctrine irrelevant to the scenario.`;

const JUDGE_SYSTEM = `You are a blind judge for a paired automation-design experiment. The four responses are anonymized and shuffled. Score each response independently against the scenario and rubric; never infer, reward, or punish treatment identity. Vocabulary alone earns no credit.

For every response, emit integer scores from 0 to 4 for exactly these keys:
${SCORE_DIMENSIONS.join(", ")}.
0 is dangerously wrong or absent where essential; 1 has major errors; 2 is mixed/partial; 3 is correct and useful; 4 is explicit, precise, and directly actionable.

Only use these global hard-failure IDs or a scenario-specific ID supplied in scenario.judge.hardFailures:
${Object.entries(HARD_FAILURES)
  .map(([id, description]) => `- ${id}: ${description}`)
  .join("\n")}

The scenario's primaryDimensions are the preregistered headline dimensions; score all ten, but do not let unrelated dimensions dilute those focused criteria.

For every ID in scenario.mustCheckFailureIds, hardFailureChecks must contain exactly one key. Its value must be either the literal string "not present" or an exact contiguous quote from that response proving the failure. A quoted check must have an identical entry in hardFailures; "not present" must not. You may report another allowed hard failure when grounded by an exact quote. A lower score or summary mention never substitutes for the checklist.

Each response includes lengthLimited and contentTruncatedForReview. Score only visible content, lower actionability when a cutoff omits a required deliverable, and do not invent a semantic hard failure merely because transport ended.

Return one JSON object and no prose. Return exactly four response results. Each result must have blindId, all ten scores, hardFailureChecks, hardFailures, integer confidence 0..4, boolean ambiguous, and a one-sentence summary. hardFailures entries have id and evidence. Do not emit a scenario-level summary.`;

function assertSafeId(value, label) {
  if (typeof value !== "string" || !/^[a-z0-9][a-z0-9-]*$/.test(value)) {
    throw new Error(`${label} must match [a-z0-9][a-z0-9-]*`);
  }
}

function parseNonNegativeUsd(value, label) {
  if (typeof value !== "string" || !/^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$/.test(value)) {
    throw new Error(`${label} must be a plain non-negative decimal`);
  }
  return usdToPico(value);
}

export function effectiveNewBudgetPico() {
  const hard = usdToPico(CONFIG.newSpendHardCapUsd);
  const prior = parseNonNegativeUsd(process.env.AGENT_OS_PRIOR_NEW_SPEND_USD ?? "0", "AGENT_OS_PRIOR_NEW_SPEND_USD");
  if (prior > hard) throw new Error("prior follow-up spend already exceeds the new-spend allowance");
  const remaining = hard - prior;
  const requestedText = process.env.AGENT_OS_BUDGET_USD;
  const requested = requestedText === undefined || requestedText === "" ? remaining : parseNonNegativeUsd(requestedText, "AGENT_OS_BUDGET_USD");
  if (requested <= 0n || requested > remaining) {
    throw new Error(`AGENT_OS_BUDGET_USD must be > 0 and <= remaining allowance $${picoToUsd(remaining)}`);
  }
  return { budgetPico: requested, priorNewSpendPico: prior, remainingBeforeRunPico: remaining };
}

export function inputTokenUpperBound(messages) {
  let visibleBytes = 0;
  for (const message of messages) {
    if (typeof message?.role !== "string" || typeof message?.content !== "string") {
      throw new Error("experiment messages must contain string role and content fields");
    }
    if (canonicalJson(Object.keys(message).sort()) !== canonicalJson(["content", "role"])) {
      throw new Error("experiment messages must be tool-free role/content objects");
    }
    visibleBytes += Buffer.byteLength(message.role, "utf8");
    visibleBytes += Buffer.byteLength(message.content, "utf8");
  }
  return visibleBytes + CONFIG.chatOverheadTokenAllowance;
}

export function requestInputTokenUpperBound(messages, responseFormat = null) {
  const messageBound = inputTokenUpperBound(messages);
  return responseFormat === null
    ? messageBound
    : messageBound + Buffer.byteLength(canonicalJson(responseFormat), "utf8");
}

export function buildCandidateMessages(scenario, treatmentText) {
  return [
    { role: "system", content: `${CANDIDATE_SYSTEM}\n\nContext available for this response:\n${String(treatmentText).trim()}` },
    { role: "user", content: scenario.prompt },
  ];
}

export function buildJudgeMessages(scenario, blindedResponses) {
  const mustCheckFailureIds = scenario.mustCheckFailureIds ?? scenario.judge?.mustCheckFailureIds;
  const example = {
    responses: [{
      blindId: "R1",
      scores: Object.fromEntries(SCORE_DIMENSIONS.map((dimension) => [dimension, 3])),
      hardFailureChecks: Object.fromEntries(mustCheckFailureIds.map((id) => [id, "not present"])),
      hardFailures: [],
      confidence: 3,
      ambiguous: false,
      summary: "One sentence grounded in the visible response.",
    }],
  };
  return [
    { role: "system", content: `${JUDGE_SYSTEM}\n\nCanonical checklist shape for one result (emit this shape once for each of R1 through R4):\n${canonicalJson(example)}` },
    {
      role: "user",
      content: canonicalJson({
        scenario: {
          prompt: scenario.prompt,
          judge: scenario.judge,
          mustCheckFailureIds,
          primaryDimensions: scenario.judge?.primaryDimensions,
        },
        responses: blindedResponses.map(({ blindId, content, lengthLimited, truncated }) => ({
          blindId,
          content,
          lengthLimited: Boolean(lengthLimited),
          contentTruncatedForReview: Boolean(truncated),
        })),
      }),
    },
  ];
}

export function judgeResponseFormat(scenario, blindIds) {
  const mustCheckFailureIds = scenario.mustCheckFailureIds ?? scenario.judge?.mustCheckFailureIds;
  const localFailureIds = (scenario.judge?.hardFailures ?? []).map((failure) => failure.id);
  const allowedFailureIds = [...new Set([...Object.keys(HARD_FAILURES), ...localFailureIds])];
  const scores = {
    type: "object",
    additionalProperties: false,
    properties: Object.fromEntries(SCORE_DIMENSIONS.map((dimension) => [dimension, { type: "integer", minimum: 0, maximum: 4 }])),
    required: [...SCORE_DIMENSIONS],
  };
  const hardFailureChecks = {
    type: "object",
    additionalProperties: false,
    properties: Object.fromEntries(mustCheckFailureIds.map((id) => [id, { type: "string" }])),
    required: [...mustCheckFailureIds],
  };
  const responseResult = {
    type: "object",
    additionalProperties: false,
    properties: {
      blindId: { type: "string", enum: [...blindIds] },
      scores,
      hardFailureChecks,
      hardFailures: {
        type: "array",
        items: {
          type: "object",
          additionalProperties: false,
          properties: { id: { type: "string", enum: allowedFailureIds }, evidence: { type: "string" } },
          required: ["id", "evidence"],
        },
      },
      confidence: { type: "integer", minimum: 0, maximum: 4 },
      ambiguous: { type: "boolean" },
      summary: { type: "string" },
    },
    required: ["blindId", "scores", "hardFailureChecks", "hardFailures", "confidence", "ambiguous", "summary"],
  };
  return {
    type: "json_schema",
    json_schema: {
      name: "agent_os_blind_judgment",
      strict: true,
      schema: {
        type: "object",
        additionalProperties: false,
        properties: { responses: { type: "array", minItems: blindIds.length, maxItems: blindIds.length, items: responseResult } },
        required: ["responses"],
      },
    },
  };
}

export function candidateSeed(scenarioIndex, replicateIndex) {
  return CONFIG.baseSeed + scenarioIndex * 100 + replicateIndex;
}

export function judgeSeed(scenarioIndex, role) {
  const offset = role === "primaryJudge" ? 10_000 : 20_000;
  return CONFIG.baseSeed + offset + scenarioIndex;
}

export function deterministicCellOrder(scenarioIndex) {
  const cells = [];
  for (let replicateIndex = 0; replicateIndex < CONFIG.candidateReplicates; replicateIndex += 1) {
    for (const treatment of CONFIG.treatments) cells.push({ treatmentId: treatment.id, replicateIndex });
  }
  let state = (CONFIG.baseSeed ^ ((scenarioIndex + 1) * 0x9e3779b9)) >>> 0;
  for (let index = cells.length - 1; index > 0; index -= 1) {
    state ^= state << 13;
    state ^= state >>> 17;
    state ^= state << 5;
    const target = (state >>> 0) % (index + 1);
    [cells[index], cells[target]] = [cells[target], cells[index]];
  }
  return cells;
}

export async function loadFollowUpInputs() {
  const scenariosPath = path.join(EXPERIMENT_DIR, "scenarios.json");
  const scenariosText = await readFile(scenariosPath, "utf8");
  const scenarioDocument = JSON.parse(scenariosText);
  if (!Array.isArray(scenarioDocument.scenarios) || scenarioDocument.scenarios.length !== CONFIG.expectedScenarioCount) {
    throw new Error(`follow-up scenarios must contain exactly ${CONFIG.expectedScenarioCount} entries`);
  }

  const seenIds = new Set();
  const pairPositions = new Set();
  const pairCounts = new Map();
  const scenarios = scenarioDocument.scenarios.map((scenario) => {
    assertSafeId(scenario.id, "scenario.id");
    assertSafeId(scenario.pairId, `scenario ${scenario.id} pairId`);
    if (seenIds.has(scenario.id)) throw new Error(`duplicate scenario id: ${scenario.id}`);
    seenIds.add(scenario.id);
    if (![0, 1].includes(scenario.pairPosition)) throw new Error(`scenario ${scenario.id} pairPosition must be 0 or 1`);
    const pairKey = `${scenario.pairId}:${scenario.pairPosition}`;
    if (pairPositions.has(pairKey)) throw new Error(`duplicate pair position: ${pairKey}`);
    pairPositions.add(pairKey);
    pairCounts.set(scenario.pairId, (pairCounts.get(scenario.pairId) ?? 0) + 1);
    if (typeof scenario.prompt !== "string" || !scenario.prompt.trim()) throw new Error(`scenario ${scenario.id} requires a prompt`);
    if (typeof scenario.judge?.expectedDecision !== "string" || !scenario.judge.expectedDecision.trim()) {
      throw new Error(`scenario ${scenario.id} requires judge.expectedDecision`);
    }
    const primaryDimensions = scenario.judge.primaryDimensions;
    if (!Array.isArray(primaryDimensions) || primaryDimensions.length === 0 || new Set(primaryDimensions).size !== primaryDimensions.length || primaryDimensions.some((dimension) => !SCORE_DIMENSIONS.includes(dimension))) {
      throw new Error(`scenario ${scenario.id} requires unique valid judge.primaryDimensions`);
    }
    const criteria = scenario.judge.criteria;
    if (!criteria || typeof criteria !== "object" || Array.isArray(criteria) || canonicalJson(Object.keys(criteria).sort()) !== canonicalJson([...primaryDimensions].sort())) {
      throw new Error(`scenario ${scenario.id} judge.criteria must contain exactly its primaryDimensions`);
    }
    for (const dimension of primaryDimensions) {
      if (typeof criteria[dimension] !== "string" || !criteria[dimension].trim()) throw new Error(`scenario ${scenario.id} criterion ${dimension} must be non-empty`);
    }
    if (!["negative-control", "targeted"].includes(scenario.pairRole)) throw new Error(`scenario ${scenario.id} requires pairRole`);
    const scenarioFailureIds = new Set();
    for (const failure of scenario.judge?.hardFailures ?? []) {
      if (!failure || typeof failure.id !== "string" || !/^[a-z][a-zA-Z0-9]*$/.test(failure.id)) {
        throw new Error(`scenario ${scenario.id} has an invalid hard-failure ID`);
      }
      if (Object.hasOwn(HARD_FAILURES, failure.id) || scenarioFailureIds.has(failure.id)) {
        throw new Error(`scenario ${scenario.id} redefines or duplicates hard failure ${failure.id}`);
      }
      if (typeof failure.description !== "string" || !failure.description.trim()) {
        throw new Error(`scenario ${scenario.id} hard failure ${failure.id} requires a description`);
      }
      scenarioFailureIds.add(failure.id);
    }
    const allowed = new Set([...Object.keys(HARD_FAILURES), ...scenarioFailureIds]);
    const checks = scenario.judge.mustCheckFailureIds;
    if (!Array.isArray(checks) || checks.length === 0 || new Set(checks).size !== checks.length) {
      throw new Error(`scenario ${scenario.id} requires unique mustCheckFailureIds`);
    }
    for (const id of checks) if (!allowed.has(id)) throw new Error(`scenario ${scenario.id} has unknown must-check failure ${id}`);
    for (const id of scenarioFailureIds) if (!checks.includes(id)) throw new Error(`scenario ${scenario.id} must check scenario failure ${id}`);
    return { ...scenario, mustCheckFailureIds: [...checks] };
  });

  if (pairCounts.size !== 3 || [...pairCounts.values()].some((count) => count !== 2)) {
    throw new Error("follow-up scenarios must form exactly three two-scenario contrast pairs");
  }
  for (const pairId of pairCounts.keys()) {
    const paired = scenarios.filter((scenario) => scenario.pairId === pairId);
    if (canonicalJson(paired[0].judge.primaryDimensions) !== canonicalJson(paired[1].judge.primaryDimensions)) {
      throw new Error(`contrast pair ${pairId} must use identical ordered primaryDimensions`);
    }
  }
  for (const scenario of scenarios) {
    const expectedRole = scenario.pairId === "automation-identity" ? "negative-control" : "targeted";
    if (scenario.pairRole !== expectedRole) throw new Error(`scenario ${scenario.id} has incorrect preregistered pairRole`);
  }
  const basePath = path.join(EXPERIMENT_DIR, "..", "variants", "recipe-aware.md");
  const guardrailsPath = path.join(EXPERIMENT_DIR, "guardrails.md");
  const [baseText, guardrailsText] = await Promise.all([readFile(basePath, "utf8"), readFile(guardrailsPath, "utf8")]);
  const treatments = [
    { ...CONFIG.treatments[0], text: `${baseText.trim()}\n`, components: [basePath] },
    {
      ...CONFIG.treatments[1],
      text: `${baseText.trim()}\n\n${guardrailsText.trim()}\n`,
      components: [basePath, guardrailsPath],
    },
  ];
  const fingerprintMaterial = {
    config: CONFIG,
    hardFailures: HARD_FAILURES,
    scoreDimensions: SCORE_DIMENSIONS,
    prompts: { candidate: CANDIDATE_SYSTEM, judge: JUDGE_SYSTEM },
    followUpScenarios: scenarioDocument,
    treatments: treatments.map(({ id, rank, text }) => ({ id, rank, text })),
  };
  return {
    scenarios,
    treatments,
    fingerprint: sha256(canonicalJson(fingerprintMaterial)),
    sourceFiles: {
      scenarios: { path: scenariosPath, bytes: Buffer.byteLength(scenariosText, "utf8"), sha256: sha256(scenariosText) },
      base: { path: basePath, bytes: Buffer.byteLength(baseText, "utf8"), sha256: sha256(baseText) },
      guardrails: { path: guardrailsPath, bytes: Buffer.byteLength(guardrailsText, "utf8"), sha256: sha256(guardrailsText) },
    },
  };
}

// Assert that the inherited implementation still agrees on model-visible bytes.
export function assertInheritedByteAccounting(messages) {
  const inherited = originalInputTokenUpperBound(messages);
  const followUp = inputTokenUpperBound(messages);
  if (followUp !== inherited) throw new Error("follow-up byte accounting diverged from the inherited bound");
  return { inherited, followUp };
}
