import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  CONFIG,
  EXPERIMENT_DIR,
  SCORE_DIMENSIONS,
  buildCandidateMessages,
  deterministicCellOrder,
  inputTokenUpperBound,
  loadFollowUpInputs,
  truncateUtf8,
} from "./config.mjs";
import { aggregatePaired, recommendPaired, validateJudgment } from "./judgment.mjs";
import { buildAblationPlan } from "./preflight.mjs";
import { buildRequestBody, compareArchiveJudgment } from "./run.mjs";
import { loadSourceArtifact } from "./source.mjs";

const inputs = await loadFollowUpInputs();
assert.deepEqual(inputs.scenarios.map((scenario) => scenario.id), [
  "shared-participant-independent-jobs",
  "single-automation-multiple-triggers",
  "observed-improvement-candidate",
  "stale-live-design-drift",
  "adapter-capability-unknown",
  "adapter-capability-evidenced",
]);
assert.equal(inputs.scenarios.filter((scenario) => scenario.pairRole === "negative-control").length, 2);
for (const scenario of inputs.scenarios) {
  assert.deepEqual(Object.keys(scenario.judge.criteria).sort(), [...scenario.judge.primaryDimensions].sort());
}
assert.ok(inputs.treatments[1].text.startsWith(inputs.treatments[0].text.trim()));
assert.match(inputs.treatments[1].text.slice(inputs.treatments[0].text.trim().length), /# Compact safety guardrails/);

const plan = buildAblationPlan(inputs);
assert.equal(plan.filter((call) => call.phase === "candidate").length, 24);
assert.equal(plan.filter((call) => call.phase === "primary-judge").length, 6);
for (const [scenarioIndex, scenario] of inputs.scenarios.entries()) {
  const cells = deterministicCellOrder(scenarioIndex);
  assert.equal(cells.length, 4);
  for (let replicateIndex = 0; replicateIndex < CONFIG.candidateReplicates; replicateIndex += 1) {
    const calls = plan.filter((call) => call.phase === "candidate" && call.scenarioId === scenario.id && call.replicateIndex === replicateIndex);
    assert.equal(calls.length, 2);
    assert.equal(calls[0].seed, calls[1].seed, "paired treatments must share the exact seed");
  }
}

const fixture = JSON.parse(await readFile(path.join(EXPERIMENT_DIR, "fixtures", "valid-judgment.json"), "utf8"));
const scenario = inputs.scenarios[0];
const expected = [{ blindId: "R1", content: "The response preserves separate automation identities." }];
assert.equal(validateJudgment(fixture, expected, scenario).valid, true);
const missingCheck = structuredClone(fixture);
delete missingCheck.responses[0].hardFailureChecks.recipeOwnsTrigger;
assert.equal(validateJudgment(missingCheck, expected, scenario).valid, false);
const inconsistent = structuredClone(fixture);
inconsistent.responses[0].hardFailureChecks.recipeOwnsTrigger = "preserves separate";
assert.equal(validateJudgment(inconsistent, expected, scenario).valid, false);
const grounded = structuredClone(fixture);
grounded.responses[0].hardFailureChecks.recipeOwnsTrigger = "preserves separate";
grounded.responses[0].hardFailures = [{ id: "recipeOwnsTrigger", evidence: "preserves separate" }];
const groundedValidation = validateJudgment(grounded, expected, scenario);
assert.equal(groundedValidation.valid, true);
assert.equal(groundedValidation.groundedHardFailures.length, 1);
const invalidGrounded = structuredClone(grounded);
delete invalidGrounded.responses[0].hardFailureChecks.recipeOwnsTrigger;
const invalidGroundedValidation = validateJudgment(invalidGrounded, expected, scenario);
assert.equal(invalidGroundedValidation.valid, false);
assert.equal(invalidGroundedValidation.groundedHardFailures.length, 0);
assert.equal(invalidGroundedValidation.untrustedHardFailureClaims.length, 1);

const fingerprintCandidates = new Map();
const fingerprintBlinded = [];
const fingerprintResponses = [];
for (let replicateIndex = 0; replicateIndex < CONFIG.candidateReplicates; replicateIndex += 1) {
  for (const treatmentId of ["recipe-aware", "recipe-aware-guarded"]) {
    const candidateCallId = `fingerprint-${replicateIndex}-${treatmentId}`;
    const blindId = `F${fingerprintBlinded.length + 1}`;
    fingerprintCandidates.set(candidateCallId, {
      treatmentId,
      replicateIndex,
      seed: 9_000 + replicateIndex,
      finishReason: "stop",
      systemFingerprint: replicateIndex === 0 ? (treatmentId === "recipe-aware" ? "fp-base" : "fp-guarded") : "fp-shared",
    });
    fingerprintBlinded.push({ blindId, candidateCallId, truncated: false });
    fingerprintResponses.push({ ...structuredClone(fixture.responses[0]), blindId });
  }
}
const fingerprintAggregate = aggregatePaired({
  inputs: { scenarios: [scenario] },
  judgePlans: new Map([[scenario.id, { blinded: fingerprintBlinded }]]),
  judgments: new Map([[scenario.id, { valid: true, value: { responses: fingerprintResponses } }]]),
  candidates: fingerprintCandidates,
});
assert.equal(fingerprintAggregate.diagnostics.some((item) => item.type === "systemFingerprintMismatch" && item.replicateIndex === 0), true);
assert.equal(fingerprintAggregate.comparisons.length, 1, "fingerprint-mismatched replicate must not enter the paired aggregate");
assert.equal(fingerprintAggregate.comparisons[0].replicateIndex, 1);

const cleanAggregate = {
  diagnostics: [],
  hardFailures: [],
  summary: { completePairs: 12, expectedPairs: 12 },
  scenarioDeltas: inputs.scenarios.map((item) => ({ scenarioId: item.id, pairId: item.pairId, pairRole: item.pairRole, meanDelta: item.pairRole === "negative-control" ? 0 : 0.2, minimumDelta: item.pairRole === "negative-control" ? 0 : 0.1 })),
  pairDeltas: [
    { pairId: "automation-identity", pairRole: "negative-control", meanDelta: 0, worstReplicateDelta: 0 },
    { pairId: "reconciliation", pairRole: "targeted", meanDelta: 0.2, worstReplicateDelta: 0.1 },
    { pairId: "adapter-evidence", pairRole: "targeted", meanDelta: 0.2, worstReplicateDelta: 0.1 },
  ],
};
assert.equal(recommendPaired(cleanAggregate).selectedTreatment, "recipe-aware-guarded");
assert.equal(recommendPaired(cleanAggregate, [{ type: "apiLengthCutoff" }]).selectedTreatment, null);
assert.equal(recommendPaired(cleanAggregate, [{ type: "systemFingerprintMismatch" }]).selectedTreatment, null);
const regressed = structuredClone(cleanAggregate);
regressed.pairDeltas[0].meanDelta = -0.01;
assert.equal(recommendPaired(regressed).selectedTreatment, "recipe-aware");
const weakEffect = structuredClone(cleanAggregate);
weakEffect.pairDeltas[1].meanDelta = 0.1499;
assert.equal(recommendPaired(weakEffect).selectedTreatment, "recipe-aware");
const unstableEffect = structuredClone(cleanAggregate);
unstableEffect.scenarioDeltas.find((item) => item.pairRole === "targeted").minimumDelta = -0.01;
assert.equal(recommendPaired(unstableEffect).selectedTreatment, "recipe-aware");

const candidateCall = plan.find((call) => call.phase === "candidate");
const judgeCall = plan.find((call) => call.phase === "primary-judge");
const resolution = (role) => ({ resolvedModel: CONFIG.roles[role].model, providerRouting: { only: ["openai"], order: ["openai"], allow_fallbacks: false, require_parameters: true, max_price: { prompt: 0.2, completion: 1.2, request: 0 } } });
const candidateBody = buildRequestBody(candidateCall, resolution("candidate"), buildCandidateMessages(inputs.scenarios[0], inputs.treatments[0].text));
assert.equal(Object.hasOwn(candidateBody, "temperature"), false);
assert.equal(Object.hasOwn(candidateBody, "tools"), false);
const judgeBody = buildRequestBody(judgeCall, resolution("primaryJudge"), [{ role: "system", content: "judge" }, { role: "user", content: "{}" }]);
assert.equal(Object.hasOwn(judgeBody, "temperature"), false);
assert.deepEqual(judgeBody.provider.only, ["openai"]);
assert.throws(() => inputTokenUpperBound([{ role: "user", content: "x", tools: [] }]));

const truncated = truncateUtf8("🙂".repeat(2_000), CONFIG.candidateReviewBytes);
assert.equal(truncated.truncated, true);
assert.ok(Buffer.byteLength(truncated.text, "utf8") <= CONFIG.candidateReviewBytes);
assert.deepEqual(SCORE_DIMENSIONS.length, 10);

if (process.env.AGENT_OS_TEST_SOURCE_DIR) {
  const source = await loadSourceArtifact(process.env.AGENT_OS_TEST_SOURCE_DIR);
  assert.equal(source.scenarios.length, 6);
  assert.equal(source.scenarios.flatMap((item) => item.responses).length, 24);
  for (const imported of source.scenarios.flatMap((item) => item.responses)) assert.equal(imported.contentSha256.length, 64);
  for (const importedScenario of source.scenarios) {
    assert.equal(importedScenario.originalJudgment.value.responses.length, 4);
    assert.equal(importedScenario.originalJudgment.reviewIssues.every((issue) => issue.type === "closeScoreMargin"), true);
    const equalComparison = compareArchiveJudgment(importedScenario, { valid: true, value: importedScenario.originalJudgment.value });
    assert.equal(equalComparison.status, "complete");
    assert.equal(equalComparison.comparedResponses, 4);
    assert.equal(equalComparison.summary.meanAggregateScoreDelta, 0);
    assert.equal(equalComparison.summary.changedHardFailureResponses, 0);
    assert.deepEqual(importedScenario.responses.map((item) => item.variantId), equalComparison.rows.map((item) => item.variantId));
    assert.deepEqual(importedScenario.originalJudgment.variantByBlind, Object.fromEntries(importedScenario.responses.map((item) => [item.blindId, item.variantId])));
  }
}

console.log("follow-up offline fixtures PASS");

const isMain = process.argv[1] && path.resolve(process.argv[1]) === path.resolve(fileURLToPath(import.meta.url));
assert.equal(isMain, true);
