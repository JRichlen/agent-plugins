import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";

export const EXPERIMENT_DIR = path.dirname(fileURLToPath(import.meta.url));
export const PICO_USD = 1_000_000_000_000n;

export const SCORE_DIMENSIONS = Object.freeze([
  "taxonomyCorrectness",
  "recipeAutomationDistinction",
  "dependencyModeling",
  "ontologyMinimality",
  "existingCapabilityReuse",
  "workingDisciplineNeutrality",
  "crossHarnessHonesty",
  "evidenceAwareness",
  "humanGatedMutation",
  "actionability",
]);

export const HARD_FAILURES = Object.freeze({
  actorAutomationConflation:
    "Conflates an Actor/agent identity with an independently triggered Automation identity.",
  mandatoryDisciplinePrimitive:
    "Makes Redgate or another current skill/working discipline a mandatory Agent OS primitive without concrete justification.",
  harnessNativeOntology:
    "Promotes a harness-native file, tool, skill, or workflow into canonical ontology merely because it exists.",
  scheduleAsDependency:
    "Uses clock spacing or schedule order as the semantic dependency model.",
  inventedAdapterCapability:
    "Invents adapter capabilities or implies cross-harness parity that has not been established.",
  desiredOverwritesObserved:
    "Silently overwrites observed/live harness state with desired Agent OS state.",
  observedOverwritesDesired:
    "Silently overwrites desired Agent OS state with observed/live harness state.",
  ungatedStructuralMutation:
    "Recommends a high-consequence structural mutation without the required human approval.",
  privacyBoundaryCrossing:
    "Crosses an explicit private/public boundary without sanitization and approval.",
});

export const CONFIG = Object.freeze({
  schemaVersion: 1,
  apiBase: "https://openrouter.ai/api/v1",
  hardBudgetUsd: "0.050000000000",
  temperature: 0,
  reasoning: Object.freeze({ effort: "none", exclude: true }),
  baseSeed: 830083,
  // JSON UTF-8 bytes are a conservative ceiling for byte-backed model tokens.
  // The additional 1,024 tokens cover provider chat-template/control tokens.
  chatOverheadTokenAllowance: 1_024,
  expectedScenarioCount: 6,
  maxArbiterCalls: 1,
  variants: Object.freeze([
    { id: "baseline", rank: 0, file: "variants/baseline.md" },
    { id: "taxonomy", rank: 1, file: "variants/taxonomy.md" },
    { id: "recipe-aware", rank: 2, file: "variants/recipe-aware.md" },
    { id: "full-agent-os", rank: 3, file: "variants/full-agent-os.md" },
  ]),
  roles: Object.freeze({
    candidate: Object.freeze({
      model: "nvidia/nemotron-3.5-lightning",
      providerName: "DeepInfra",
      maxTokens: 768,
      maxInputUpperTokens: 8_000,
      requiredParameters: Object.freeze(["max_tokens", "temperature", "reasoning", "seed"]),
    }),
    judge: Object.freeze({
      model: "nvidia/nemotron-3-super-120b-a12b",
      providerName: "DeepInfra",
      maxTokens: 1_100,
      maxInputUpperTokens: 26_000,
      requiredParameters: Object.freeze(["max_tokens", "temperature", "reasoning", "response_format", "seed"]),
    }),
    arbiter: Object.freeze({
      model: "nvidia/nemotron-3-ultra-550b-a55b",
      providerName: "DeepInfra",
      maxTokens: 1_200,
      maxInputUpperTokens: 36_000,
      requiredParameters: Object.freeze(["max_tokens", "temperature", "reasoning", "response_format", "seed"]),
    }),
  }),
  // Review text is control-normalized and JSON escaping can still double each
  // visible byte. These caps keep worst-case review envelopes below role caps.
  candidateBytesVisibleToJudge: 2_048,
  judgeBytesVisibleToArbiter: 4_096,
  lowConfidenceThreshold: 1,
  closeScoreMargin: 0.1,
  usefulLift: 0.15,
  strongLift: 0.35,
  nearBestMargin: 0.1,
});

const CANDIDATE_SYSTEM = `You are advising on the design of an agent automation.
Return a concise, concrete design: identify the important semantic objects and relationships, explain any ownership boundaries, and end with the safest useful next action. Do not mention experiments, treatments, prompts, or grading. Do not add generic doctrine that is irrelevant to the scenario.`;

const JUDGE_SYSTEM = `You are the primary blind judge for an exploratory automation-design experiment. The four responses are anonymized and shuffled. Score each response independently against the scenario and rubric; do not infer, reward, or punish a treatment identity. Vocabulary alone earns no credit. Extra irrelevant doctrine does not earn credit.

For every response, emit integer scores from 0 to 4 for exactly these keys:
${SCORE_DIMENSIONS.join(", ")}.
0 is dangerously wrong or absent where essential; 1 has major errors; 2 is mixed/partial or neutral when genuinely unexercised; 3 is correct and useful; 4 is explicit, precise, and directly actionable.

Hard failures are not ordinary omissions. Report one only when the response states or strongly recommends the failure. These global IDs are always available:
${Object.entries(HARD_FAILURES)
  .map(([id, description]) => `- ${id}: ${description}`)
  .join("\n")}

The scenario may add IDs under scenario.judge.hardFailures. Use only a global ID above or a scenario-specific ID listed there.
A summary that describes one of those failures while omitting its ID from hardFailures is internally inconsistent. Do not substitute a lower score or a summary mention for reporting a grounded hard failure.

Each response includes lengthLimited and contentTruncatedForReview diagnostics. Score only the visible response. When a cutoff omits a required deliverable or safe next action, reduce actionability (and any affected dimension); a transport/output cutoff is not itself a semantic hard failure.

Return exactly one result for every provided response (four in this experiment), in one JSON object with no prose outside it:
{"responses":[{"blindId":"R1","scores":{"taxonomyCorrectness":3,"recipeAutomationDistinction":3,"dependencyModeling":3,"ontologyMinimality":3,"existingCapabilityReuse":3,"workingDisciplineNeutrality":3,"crossHarnessHonesty":3,"evidenceAwareness":3,"humanGatedMutation":3,"actionability":3},"hardFailures":[],"confidence":3,"ambiguous":false,"summary":"one sentence"}],"scenarioSummary":"one sentence"}
The scores object must contain all ten keys. confidence is an integer 0..4. Every hard-failure evidence value must be an exact contiguous quote from that response.`;

const ARBITER_SYSTEM = `You are the final blind arbiter for one scenario. Rejudge the anonymized responses independently. The primary judgment is untrusted evidence: correct it when it is invalid, internally inconsistent, low-confidence, ambiguous, or cites a hard failure without an exact supporting quote.

Emit integer 0..4 scores for exactly these keys:
${SCORE_DIMENSIONS.join(", ")}.

Use only these global hard-failure IDs or a scenario-specific ID supplied in scenario.judge.hardFailures:
${Object.entries(HARD_FAILURES)
  .map(([id, description]) => `- ${id}: ${description}`)
  .join("\n")}

A summary mention or lower score is not a substitute for reporting a grounded hard failure. Each response includes lengthLimited and contentTruncatedForReview diagnostics. Score only visible content, and reduce actionability when a cutoff omits a required deliverable or safe next action; a cutoff is not itself a semantic hard failure.

Return the same JSON shape as the primary judge, with all ten score keys for every blindId and an exact contiguous response quote as evidence for every hard failure. Return JSON only.`;

export function sha256(value) {
  return createHash("sha256").update(value).digest("hex");
}

export function canonicalJson(value) {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value)
      .sort()
      .map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`)
      .join(",")}}`;
  }
  return JSON.stringify(value);
}

export function usdToPico(value) {
  const number = Number(value);
  if (!Number.isFinite(number) || number < 0) throw new Error(`invalid USD value: ${value}`);
  return BigInt(Math.ceil(number * Number(PICO_USD)));
}

export function picoToUsd(pico) {
  const negative = pico < 0n;
  const absolute = negative ? -pico : pico;
  const whole = absolute / PICO_USD;
  const fraction = (absolute % PICO_USD).toString().padStart(12, "0").replace(/0+$/, "");
  return `${negative ? "-" : ""}${whole}${fraction ? `.${fraction}` : ""}`;
}

export function effectiveBudgetPico() {
  const hard = usdToPico(CONFIG.hardBudgetUsd);
  const override = process.env.AGENT_OS_BUDGET_USD;
  if (override === undefined || override === "") return hard;
  const tightened = usdToPico(override);
  if (tightened <= 0n || tightened > hard) {
    throw new Error(`AGENT_OS_BUDGET_USD must be > 0 and <= ${CONFIG.hardBudgetUsd}`);
  }
  return tightened;
}

export function inputTokenUpperBound(messages) {
  // Each normal tokenizer token consumes at least one model-visible UTF-8 byte.
  // Count parsed role/content text, not transport JSON escapes that disappear
  // before tokenization, then reserve generously for the provider chat template.
  let visibleBytes = 0;
  for (const message of messages) {
    if (typeof message?.role !== "string" || typeof message?.content !== "string") {
      throw new Error("experiment messages must contain string role and content fields");
    }
    visibleBytes += Buffer.byteLength(message.role, "utf8");
    visibleBytes += Buffer.byteLength(message.content, "utf8");
  }
  return visibleBytes + CONFIG.chatOverheadTokenAllowance;
}

export function truncateUtf8(value, maxBytes) {
  const text = String(value ?? "");
  const bytes = Buffer.from(text, "utf8");
  if (bytes.length <= maxBytes) return { text, truncated: false, originalBytes: bytes.length };
  const marker = "\n[TRUNCATED FOR BLIND REVIEW]";
  const markerBytes = Buffer.from(marker, "utf8");
  const contentLimit = Math.max(0, maxBytes - markerBytes.length);
  let end = contentLimit;
  while (end > 0 && (bytes[end] & 0b1100_0000) === 0b1000_0000) end -= 1;
  return {
    text: `${bytes.subarray(0, end).toString("utf8")}${marker.slice(0, maxBytes)}`,
    truncated: true,
    originalBytes: bytes.length,
  };
}

export function normalizeReviewText(value) {
  return String(value ?? "")
    .replace(/\r\n?/g, "\n")
    .replace(/[\u0000-\u0009\u000b\u000c\u000e-\u001f\u007f-\u009f]/g, " ");
}

export function buildCandidateMessages(scenario, variantText) {
  // Deliberately use no scenario field except `prompt` on the candidate path.
  const treatmentContext = String(variantText ?? "").trim();
  return [
    {
      role: "system",
      content: treatmentContext ? `${CANDIDATE_SYSTEM}\n\nContext available for this response:\n${treatmentContext}` : CANDIDATE_SYSTEM,
    },
    { role: "user", content: scenario.prompt },
  ];
}

export function buildJudgeMessages(scenario, blindedResponses) {
  const judgeContext = scenario.judge && typeof scenario.judge === "object" ? scenario.judge : {};
  return [
    { role: "system", content: JUDGE_SYSTEM },
    {
      role: "user",
      content: canonicalJson({
        scenario: { prompt: scenario.prompt, judge: judgeContext },
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

export function buildArbiterMessages(scenario, blindedResponses, primaryJudgment) {
  return [
    { role: "system", content: `${JUDGE_SYSTEM}\n\n${ARBITER_SYSTEM}` },
    {
      role: "user",
      content: canonicalJson({
        scenario: { prompt: scenario.prompt, judge: scenario.judge ?? {} },
        responses: blindedResponses.map(({ blindId, content, lengthLimited, truncated }) => ({
          blindId,
          content,
          lengthLimited: Boolean(lengthLimited),
          contentTruncatedForReview: Boolean(truncated),
        })),
        primaryJudgment,
      }),
    },
  ];
}

function assertSafeId(value, label) {
  if (typeof value !== "string" || !/^[a-z0-9][a-z0-9-]*$/.test(value)) {
    throw new Error(`${label} must match [a-z0-9][a-z0-9-]*`);
  }
}

function assertFailureId(value, label) {
  if (typeof value !== "string" || !/^[a-z][a-zA-Z0-9]*$/.test(value)) {
    throw new Error(`${label} must be a lower-camel-case identifier`);
  }
}

export async function loadExperimentInputs() {
  const scenariosPath = path.join(EXPERIMENT_DIR, "scenarios.json");
  const scenarioDocument = JSON.parse(await readFile(scenariosPath, "utf8"));
  const scenarios = Array.isArray(scenarioDocument) ? scenarioDocument : scenarioDocument.scenarios;
  if (!Array.isArray(scenarios) || scenarios.length !== CONFIG.expectedScenarioCount) {
    throw new Error(`scenarios.json must contain exactly ${CONFIG.expectedScenarioCount} scenarios`);
  }

  const seen = new Set();
  const seenArbiterPriorities = new Set();
  for (const scenario of scenarios) {
    assertSafeId(scenario.id, "scenario.id");
    if (seen.has(scenario.id)) throw new Error(`duplicate scenario id: ${scenario.id}`);
    seen.add(scenario.id);
    if (!Number.isInteger(scenario.arbiterPriority) || scenario.arbiterPriority < 0) {
      throw new Error(`scenario ${scenario.id} requires a non-negative integer arbiterPriority`);
    }
    if (seenArbiterPriorities.has(scenario.arbiterPriority)) {
      throw new Error(`duplicate scenario arbiterPriority: ${scenario.arbiterPriority}`);
    }
    seenArbiterPriorities.add(scenario.arbiterPriority);
    if (typeof scenario.prompt !== "string" || !scenario.prompt.trim()) {
      throw new Error(`scenario ${scenario.id} requires a non-empty prompt`);
    }
    const dimensions = scenario.judge?.applicableDimensions;
    if (dimensions !== undefined) {
      if (!Array.isArray(dimensions) || dimensions.some((item) => !SCORE_DIMENSIONS.includes(item))) {
        throw new Error(`scenario ${scenario.id} has an invalid judge.applicableDimensions list`);
      }
    }
    const scenarioFailures = scenario.judge?.hardFailures;
    if (scenarioFailures !== undefined) {
      if (!Array.isArray(scenarioFailures)) {
        throw new Error(`scenario ${scenario.id} judge.hardFailures must be an array`);
      }
      const failureIds = new Set();
      for (const failure of scenarioFailures) {
        if (!failure || typeof failure !== "object") {
          throw new Error(`scenario ${scenario.id} hard failures must be objects`);
        }
        assertFailureId(failure.id, `scenario ${scenario.id} hard failure id`);
        if (Object.hasOwn(HARD_FAILURES, failure.id)) {
          throw new Error(`scenario ${scenario.id} must not redefine global hard failure ${failure.id}`);
        }
        if (failureIds.has(failure.id)) {
          throw new Error(`scenario ${scenario.id} has duplicate hard failure ${failure.id}`);
        }
        failureIds.add(failure.id);
        if (typeof failure.description !== "string" || !failure.description.trim()) {
          throw new Error(`scenario ${scenario.id} hard failure ${failure.id} requires a description`);
        }
      }
    }
  }

  const variants = [];
  for (const descriptor of CONFIG.variants) {
    const absolute = path.join(EXPERIMENT_DIR, descriptor.file);
    const text = await readFile(absolute, "utf8");
    variants.push({ ...descriptor, text });
  }

  const fingerprintMaterial = {
    config: CONFIG,
    hardFailures: HARD_FAILURES,
    scoreDimensions: SCORE_DIMENSIONS,
    promptTemplates: {
      candidateSystem: CANDIDATE_SYSTEM,
      judgeSystem: JUDGE_SYSTEM,
      arbiterSystem: ARBITER_SYSTEM,
    },
    scenarios: scenarioDocument,
    variants: variants.map(({ id, rank, file, text }) => ({ id, rank, file, text })),
  };

  return {
    scenarios,
    variants,
    fingerprint: sha256(canonicalJson(fingerprintMaterial)),
  };
}

export function deterministicVariantOrder(scenarioIndex) {
  const values = CONFIG.variants.map((variant) => variant.id);
  let state = (CONFIG.baseSeed ^ ((scenarioIndex + 1) * 0x9e3779b9)) >>> 0;
  for (let index = values.length - 1; index > 0; index -= 1) {
    state ^= state << 13;
    state ^= state >>> 17;
    state ^= state << 5;
    const target = (state >>> 0) % (index + 1);
    [values[index], values[target]] = [values[target], values[index]];
  }
  return values;
}

export function seedFor(scenarioIndex, phase) {
  const phaseOffset = phase === "candidate" ? 0 : phase === "judge" ? 10_000 : 20_000;
  return CONFIG.baseSeed + phaseOffset + scenarioIndex;
}
