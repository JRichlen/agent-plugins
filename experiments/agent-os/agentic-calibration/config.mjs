import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { canonicalJson, picoToUsd, sha256, usdToPico } from "../follow-up/config.mjs";

export { canonicalJson, picoToUsd, sha256, usdToPico };
export const EXPERIMENT_DIR = path.dirname(fileURLToPath(import.meta.url));
export const MODEL = "openai/gpt-5.6-luna";
export const HARD_CAP_USD = "1.000000000000";
export const EFFORTS = Object.freeze(["low", "medium", "high"]);
export const MAX_AGENT_TURNS = 4;
export const MAX_OUTPUT_TOKENS = 4_096;
export const MAX_INPUT_TOKENS = 60_000;
export const BASE_SEED = 850_100;
export const CONFIG = Object.freeze({
  schemaVersion: 1,
  apiBase: "https://openrouter.ai/api/v1",
  providerName: "OpenAI",
  endpointTag: "openai",
  model: MODEL,
  hardCapUsd: HARD_CAP_USD,
  efforts: EFFORTS,
  maxAgentTurns: MAX_AGENT_TURNS,
  maxOutputTokens: MAX_OUTPUT_TOKENS,
  maxInputTokens: MAX_INPUT_TOKENS,
  judgeEffort: "medium",
});

function safeId(value, label) {
  if (typeof value !== "string" || !/^[a-z0-9][a-z0-9-]*$/.test(value)) throw new Error(`${label} is not a safe ID`);
}

export async function loadScenarios() {
  const parsed = JSON.parse(await readFile(path.join(EXPERIMENT_DIR, "scenarios.json"), "utf8"));
  if (parsed.schemaVersion !== 1 || !Array.isArray(parsed.scenarios) || parsed.scenarios.length !== 3) throw new Error("agentic scenarios must contain exactly three v1 scenarios");
  for (const scenario of parsed.scenarios) {
    safeId(scenario.id, "scenario.id");
    if (!scenario.prompt || !Array.isArray(scenario.requiredEvidenceIds) || scenario.requiredEvidenceIds.length !== 3) throw new Error(`${scenario.id}: invalid prompt/evidence requirements`);
    if (new Set(scenario.requiredEvidenceIds).size !== 3) throw new Error(`${scenario.id}: evidence IDs must be unique`);
    for (const id of scenario.requiredEvidenceIds) {
      safeId(id, `${scenario.id}.evidenceId`);
      if (!Object.hasOwn(scenario.evidence, id)) throw new Error(`${scenario.id}: missing evidence fixture ${id}`);
    }
    if (!Array.isArray(scenario.successCriteria) || !Array.isArray(scenario.hardFailures)) throw new Error(`${scenario.id}: missing rubric`);
  }
  return parsed.scenarios;
}

export function toolsFor(scenario) {
  return [{
    type: "function",
    name: "read_evidence",
    description: "Read one immutable, scenario-scoped evidence record. This tool is read-only and has no side effects.",
    strict: true,
    parameters: {
      type: "object",
      additionalProperties: false,
      properties: { evidence_id: { type: "string", enum: scenario.requiredEvidenceIds } },
      required: ["evidence_id"],
    },
  }];
}

export function planCalls(scenarios) {
  const calls = [];
  scenarios.forEach((scenario) => {
    EFFORTS.forEach((effort) => {
      const episodeId = `${scenario.id}-${effort}`;
      for (let turn = 1; turn <= MAX_AGENT_TURNS; turn += 1) calls.push({ id: `${episodeId}-turn-${turn}`, episodeId, scenarioId: scenario.id, role: "agent", effort, episodeEffort: effort, turn, maxInputTokens: MAX_INPUT_TOKENS, maxOutputTokens: MAX_OUTPUT_TOKENS });
      calls.push({ id: `${episodeId}-judge`, episodeId, scenarioId: scenario.id, role: "judge", effort: CONFIG.judgeEffort, episodeEffort: effort, maxInputTokens: MAX_INPUT_TOKENS, maxOutputTokens: MAX_OUTPUT_TOKENS });
    });
  });
  return calls;
}

export function requestedBudgetPico() {
  const raw = process.env.AGENT_OS_AGENTIC_BUDGET_USD ?? HARD_CAP_USD;
  if (!/^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$/.test(raw)) throw new Error("AGENT_OS_AGENTIC_BUDGET_USD must be a plain decimal");
  const value = usdToPico(raw);
  if (value <= 0n || value > usdToPico(HARD_CAP_USD)) throw new Error(`agentic budget must be > 0 and <= $${picoToUsd(usdToPico(HARD_CAP_USD))}`);
  return value;
}

export function inputUpperTokens(body) {
  return Buffer.byteLength(JSON.stringify({ instructions: body.instructions, input: body.input, tools: body.tools, text: body.text }), "utf8") + 2_048;
}
