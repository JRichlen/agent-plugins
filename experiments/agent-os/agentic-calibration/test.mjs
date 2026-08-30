import assert from "node:assert/strict";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { CONFIG, EFFORTS, loadScenarios, planCalls, toolsFor } from "./config.mjs";
import { buildBaseline, responsesProviderRouting } from "./calibration.mjs";

const scenarios = await loadScenarios();
assert.equal(scenarios.length, 3);
assert.deepEqual(EFFORTS, ["low", "medium", "high"]);
for (const scenario of scenarios) {
  assert.equal(scenario.requiredEvidenceIds.length, 3);
  assert.deepEqual(toolsFor(scenario)[0].parameters.properties.evidence_id.enum, scenario.requiredEvidenceIds);
}
const plan = planCalls(scenarios).map((call) => ({ ...call, maximumCostPicoUsd: "1000000", maximumCostUsd: "0.000001" }));
assert.equal(plan.length, 45);
assert.equal(plan.filter((call) => call.role === "agent").length, 36);
assert.equal(plan.filter((call) => call.role === "judge").length, 9);
for (const scenario of scenarios) for (const effort of EFFORTS) {
  const episode = `${scenario.id}-${effort}`;
  assert.equal(plan.filter((call) => call.episodeId === episode && call.role === "agent").length, CONFIG.maxAgentTurns);
  assert.equal(plan.filter((call) => call.episodeId === episode && call.role === "judge").length, 1);
}
const rows = [
  { episodeId: `${scenarios[0].id}-low`, scenarioId: scenarios[0].id, role: "agent", effort: "low", episodeEffort: "low", actualCostPicoUsd: "1000000", promptTokens: 10, completionTokens: 5, reasoningTokens: 2, cachedInputTokens: 0, durationMs: 20 },
  { episodeId: `${scenarios[0].id}-low`, scenarioId: scenarios[0].id, role: "judge", effort: "medium", episodeEffort: "low", actualCostPicoUsd: "2000000", promptTokens: 20, completionTokens: 6, reasoningTokens: 3, cachedInputTokens: 0, durationMs: 30 },
];
const trajectories = [{ episodeId: `${scenarios[0].id}-low`, scenarioId: scenarios[0].id, effort: "low", agentTurns: 1, judgment: { pass: true } }];
const baseline = buildBaseline(rows, { budgetUsd: "1", fullMaximumUsd: "0.75" }, trajectories);
assert.equal(baseline.overall.actualCostUsd, "0.000003");
assert.equal(baseline.byEffort.find((item) => item.effort === "low").passed, 1);
const routing = responsesProviderRouting({ tag: "openai", pricing: { prompt: "0.0000002", completion: "0.0000012" } });
assert.deepEqual(routing.only, ["openai"]);
assert.equal(routing.allow_fallbacks, false);
assert.equal(routing.require_parameters, false);

console.log("agentic calibration offline fixtures PASS");
const isMain = process.argv[1] && path.resolve(process.argv[1]) === path.resolve(fileURLToPath(import.meta.url));
assert.equal(isMain, true);
