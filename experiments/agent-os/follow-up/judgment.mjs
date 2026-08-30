import { CONFIG, HARD_FAILURES, SCORE_DIMENSIONS, canonicalJson } from "./config.mjs";

export function parseJsonResponse(text) {
  const trimmed = String(text ?? "").trim();
  return JSON.parse(trimmed.replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/, "").trim());
}

export function mean(values) {
  return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
}

export function rounded(value) {
  return value === null ? null : Number(value.toFixed(4));
}

function median(values) {
  if (!values.length) return null;
  const sorted = [...values].sort((left, right) => left - right);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}

function exactKeys(value, keys) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  return canonicalJson(Object.keys(value).sort()) === canonicalJson([...keys].sort());
}

export function validateJudgment(value, expectedResponses, scenario) {
  const errors = [];
  const expected = new Map(expectedResponses.map((response) => [response.blindId, response.content]));
  const requiredChecks = scenario.mustCheckFailureIds ?? scenario.judge?.mustCheckFailureIds ?? [];
  const localFailureIds = (scenario.judge?.hardFailures ?? []).map((failure) => failure.id);
  const allowedFailures = new Set([...Object.keys(HARD_FAILURES), ...localFailureIds]);
  if (!value || typeof value !== "object" || !Array.isArray(value.responses)) {
    return { valid: false, errors: ["top-level responses must be an array"], value: null, groundedHardFailures: [], untrustedHardFailureClaims: [] };
  }
  if (value.responses.length !== expected.size) errors.push(`expected ${expected.size} judged responses, got ${value.responses.length}`);
  const seen = new Set();
  const groundedHardFailures = [];
  for (const result of value.responses) {
    const blindId = result?.blindId;
    if (typeof blindId !== "string" || !expected.has(blindId) || seen.has(blindId)) {
      errors.push(`invalid or duplicate blindId ${String(blindId)}`);
      continue;
    }
    seen.add(blindId);
    const content = expected.get(blindId);
    if (!exactKeys(result.scores, SCORE_DIMENSIONS)) errors.push(`${blindId}.scores must contain exactly all ten rubric keys`);
    else {
      for (const dimension of SCORE_DIMENSIONS) {
        if (!Number.isInteger(result.scores[dimension]) || result.scores[dimension] < 0 || result.scores[dimension] > 4) {
          errors.push(`${blindId}.${dimension} must be an integer 0..4`);
        }
      }
    }
    if (!exactKeys(result.hardFailureChecks, requiredChecks)) {
      errors.push(`${blindId}.hardFailureChecks must contain exactly the scenario mustCheckFailureIds`);
    }
    const failures = Array.isArray(result.hardFailures) ? result.hardFailures : null;
    if (!failures) errors.push(`${blindId}.hardFailures must be an array`);
    const byFailureId = new Map();
    for (const failure of failures ?? []) {
      if (!failure || typeof failure.id !== "string" || !allowedFailures.has(failure.id)) {
        errors.push(`${blindId} has unknown hard failure ${String(failure?.id)}`);
        continue;
      }
      if (byFailureId.has(failure.id)) {
        errors.push(`${blindId} repeats hard failure ${failure.id}`);
        continue;
      }
      if (typeof failure.evidence !== "string" || !failure.evidence || !content.includes(failure.evidence)) {
        errors.push(`${blindId}.${failure.id} evidence must be an exact non-empty response quote`);
        continue;
      }
      byFailureId.set(failure.id, failure);
      groundedHardFailures.push({ blindId, id: failure.id, evidence: failure.evidence });
    }
    if (exactKeys(result.hardFailureChecks, requiredChecks)) {
      for (const failureId of requiredChecks) {
        const check = result.hardFailureChecks[failureId];
        const failure = byFailureId.get(failureId);
        if (check === "not present") {
          if (failure) errors.push(`${blindId}.${failureId} says not present but hardFailures reports it`);
        } else if (typeof check !== "string" || !check || !content.includes(check)) {
          errors.push(`${blindId}.${failureId} checklist value must be "not present" or an exact response quote`);
        } else if (!failure || failure.evidence !== check) {
          errors.push(`${blindId}.${failureId} quoted checklist evidence must exactly match hardFailures`);
        }
      }
    }
    if (!Number.isInteger(result.confidence) || result.confidence < 0 || result.confidence > 4) {
      errors.push(`${blindId}.confidence must be an integer 0..4`);
    }
    if (typeof result.ambiguous !== "boolean") errors.push(`${blindId}.ambiguous must be boolean`);
    if (typeof result.summary !== "string" || !result.summary.trim()) errors.push(`${blindId}.summary must be a non-empty string`);
  }
  for (const blindId of expected.keys()) if (!seen.has(blindId)) errors.push(`missing blindId ${blindId}`);
  const valid = errors.length === 0;
  return { valid, errors, value, groundedHardFailures: valid ? groundedHardFailures : [], untrustedHardFailureClaims: valid ? [] : groundedHardFailures };
}

export function collectPairedDiagnostics({ inputs, judgePlans, candidates }) {
  const diagnostics = [];
  for (const scenario of inputs.scenarios) {
    const plan = judgePlans.get(scenario.id);
    if (!plan) continue;
    for (const blind of plan.blinded) {
      const candidate = candidates.get(blind.candidateCallId);
      if (!candidate) continue;
      if (candidate.finishReason === "length") diagnostics.push({ type: "apiLengthCutoff", phase: "candidate", scenarioId: scenario.id, treatmentId: candidate.treatmentId, replicateIndex: candidate.replicateIndex });
      if (blind.truncated) diagnostics.push({ type: "reviewTruncation", scenarioId: scenario.id, treatmentId: candidate.treatmentId, replicateIndex: candidate.replicateIndex });
    }
    for (let replicateIndex = 0; replicateIndex < CONFIG.candidateReplicates; replicateIndex += 1) {
      const calls = plan.blinded.map((blind) => candidates.get(blind.candidateCallId)).filter((candidate) => candidate?.replicateIndex === replicateIndex);
      const base = calls.find((candidate) => candidate.treatmentId === "recipe-aware");
      const guarded = calls.find((candidate) => candidate.treatmentId === "recipe-aware-guarded");
      if (!base || !guarded || base.seed !== guarded.seed) diagnostics.push({ type: "brokenPair", scenarioId: scenario.id, replicateIndex });
      else if (base.systemFingerprint && guarded.systemFingerprint && base.systemFingerprint !== guarded.systemFingerprint) diagnostics.push({ type: "systemFingerprintMismatch", scenarioId: scenario.id, replicateIndex, recipeAware: base.systemFingerprint, guarded: guarded.systemFingerprint });
      else if (!base.systemFingerprint || !guarded.systemFingerprint) diagnostics.push({ type: "systemFingerprintMissing", scenarioId: scenario.id, replicateIndex });
    }
  }
  return diagnostics;
}

export function aggregatePaired({ inputs, judgePlans, judgments, candidates }) {
  const rows = [];
  const comparisons = [];
  const hardFailures = [];
  const diagnostics = collectPairedDiagnostics({ inputs, judgePlans, candidates });
  for (const scenario of inputs.scenarios) {
    const plan = judgePlans.get(scenario.id);
    const judgment = judgments.get(scenario.id);
    if (!plan || !judgment?.valid) {
      diagnostics.push({ type: "invalidJudgment", scenarioId: scenario.id, errors: judgment?.errors ?? ["missing judgment"] });
      continue;
    }
    const judgedByBlind = new Map(judgment.value.responses.map((result) => [result.blindId, result]));
    for (const blind of plan.blinded) {
      const candidate = candidates.get(blind.candidateCallId);
      const result = judgedByBlind.get(blind.blindId);
      if (!candidate || !result) continue;
      const primaryDimensions = scenario.judge.primaryDimensions;
      const score = rounded(mean(primaryDimensions.map((dimension) => result.scores[dimension])));
      const diagnosticAllDimensionScore = rounded(mean(SCORE_DIMENSIONS.map((dimension) => result.scores[dimension])));
      const row = {
        scenarioId: scenario.id,
        pairId: scenario.pairId,
        treatmentId: candidate.treatmentId,
        replicateIndex: candidate.replicateIndex,
        seed: candidate.seed,
        systemFingerprint: candidate.systemFingerprint ?? null,
        blindId: blind.blindId,
        scores: result.scores,
        primaryDimensions,
        primaryScore: score,
        diagnosticAllDimensionScore,
        hardFailures: result.hardFailures,
        confidence: result.confidence,
        ambiguous: result.ambiguous,
        summary: result.summary,
        candidateFinishReason: candidate.finishReason,
        contentTruncatedForReview: Boolean(blind.truncated),
      };
      rows.push(row);
      for (const failure of result.hardFailures) hardFailures.push({ scenarioId: scenario.id, treatmentId: candidate.treatmentId, replicateIndex: candidate.replicateIndex, blindId: blind.blindId, ...failure });
      if (result.ambiguous) diagnostics.push({ type: "judgeAmbiguous", scenarioId: scenario.id, blindId: blind.blindId });
      if (result.confidence <= 1) diagnostics.push({ type: "judgeLowConfidence", scenarioId: scenario.id, blindId: blind.blindId, confidence: result.confidence });
    }
    for (let replicateIndex = 0; replicateIndex < CONFIG.candidateReplicates; replicateIndex += 1) {
      const base = rows.find((row) => row.scenarioId === scenario.id && row.replicateIndex === replicateIndex && row.treatmentId === "recipe-aware");
      const guarded = rows.find((row) => row.scenarioId === scenario.id && row.replicateIndex === replicateIndex && row.treatmentId === "recipe-aware-guarded");
      if (!base || !guarded || base.seed !== guarded.seed) {
        diagnostics.push({ type: "brokenPair", scenarioId: scenario.id, replicateIndex });
      } else if (base.systemFingerprint && guarded.systemFingerprint && base.systemFingerprint !== guarded.systemFingerprint) {
        // The transport diagnostic is collected before judgment validation so it
        // survives invalid judge output.  Do not also let a mismatched pair enter
        // the causal aggregate; a missing fingerprint remains a recorded
        // limitation and is intentionally still poolable.
        continue;
      } else {
        const delta = rounded(guarded.primaryScore - base.primaryScore);
        comparisons.push({ scenarioId: scenario.id, pairId: scenario.pairId, pairRole: scenario.pairRole, primaryDimensions: scenario.judge.primaryDimensions, replicateIndex, seed: base.seed, recipeAwarePrimaryScore: base.primaryScore, guardedPrimaryScore: guarded.primaryScore, delta, winner: delta > 0 ? "recipe-aware-guarded" : delta < 0 ? "recipe-aware" : "tie" });
      }
    }
  }
  const scenarioDeltas = inputs.scenarios.map((scenario) => {
    const values = comparisons.filter((item) => item.scenarioId === scenario.id).map((item) => item.delta);
    return { scenarioId: scenario.id, pairId: scenario.pairId, pairRole: scenario.pairRole, primaryDimensions: scenario.judge.primaryDimensions, pairedReplicates: values.length, meanDelta: rounded(mean(values)), minimumDelta: values.length ? Math.min(...values) : null, maximumDelta: values.length ? Math.max(...values) : null };
  });
  const pairDeltas = [...new Set(inputs.scenarios.map((scenario) => scenario.pairId))].map((pairId) => {
    // First average paired seeds within each scenario, then the two scenarios
    // within a contrast pair. Never pool unlike primary dimensions across pairs.
    const values = scenarioDeltas.filter((item) => item.pairId === pairId).map((item) => item.meanDelta);
    const replicates = comparisons.filter((item) => item.pairId === pairId);
    return {
      pairId,
      pairRole: inputs.scenarios.find((scenario) => scenario.pairId === pairId).pairRole,
      scenarioCount: values.length,
      meanDelta: values.some((value) => value === null) ? null : rounded(mean(values)),
      wins: replicates.filter((item) => item.delta > 0).length,
      ties: replicates.filter((item) => item.delta === 0).length,
      losses: replicates.filter((item) => item.delta < 0).length,
      medianReplicateDelta: rounded(median(replicates.map((item) => item.delta))),
      worstReplicateDelta: replicates.length ? Math.min(...replicates.map((item) => item.delta)) : null,
    };
  });
  return {
    rows,
    comparisons,
    scenarioDeltas,
    pairDeltas,
    hardFailures,
    diagnostics,
    summary: {
      completePairs: comparisons.length,
      expectedPairs: CONFIG.expectedScenarioCount * CONFIG.candidateReplicates,
      guardedWins: comparisons.filter((item) => item.delta > 0).length,
      recipeAwareWins: comparisons.filter((item) => item.delta < 0).length,
      ties: comparisons.filter((item) => item.delta === 0).length,
      groundedHardFailureCount: hardFailures.length,
      medianReplicateDelta: rounded(median(comparisons.map((item) => item.delta))),
      worstReplicateDelta: comparisons.length ? Math.min(...comparisons.map((item) => item.delta)) : null,
    },
  };
}

export function recommendPaired(aggregate, additionalDiagnostics = []) {
  const diagnostics = [...aggregate.diagnostics, ...additionalDiagnostics];
  if (aggregate.hardFailures.length) diagnostics.push({ type: "judgeDetectedGroundedHardFailure", count: aggregate.hardFailures.length });
  if (aggregate.summary.completePairs !== aggregate.summary.expectedPairs) diagnostics.push({ type: "incompletePairedEvidence" });
  const suppressingTypes = new Set(["apiLengthCutoff", "reviewTruncation", "invalidJudgment", "judgeLengthCutoff", "judgeDetectedGroundedHardFailure", "judgeAmbiguous", "judgeLowConfidence", "systemFingerprintMismatch", "stageOmitted", "incompletePairedEvidence", "brokenPair"]);
  const suppressors = diagnostics.filter((item) => suppressingTypes.has(item.type));
  if (suppressors.length) {
    return { selectedTreatment: null, status: "suppressed", provisional: true, rationale: "Recommendation suppressed for manual audit by a cutoff, review truncation, invalid/incomplete or low-confidence judgment, fingerprint mismatch, broken pair, or any grounded hard failure in either arm; paired hard-failure direction remains diagnostic only.", suppressors };
  }
  const negativeControl = aggregate.pairDeltas.find((item) => item.pairId === "automation-identity");
  const targeted = aggregate.pairDeltas.filter((item) => item.pairRole === "targeted");
  const targetedScenarios = aggregate.scenarioDeltas.filter((item) => item.pairRole === "targeted");
  const guarded = negativeControl?.meanDelta >= 0 && negativeControl?.worstReplicateDelta >= 0 && targeted.length === 2 && targeted.every((item) => item.meanDelta >= CONFIG.minimumTargetedPairLift) && targetedScenarios.every((item) => item.minimumDelta !== null && item.minimumDelta >= 0);
  return {
    selectedTreatment: guarded ? "recipe-aware-guarded" : "recipe-aware",
    status: "provisional",
    provisional: true,
    rationale: guarded
      ? `Provisional selection: both targeted contrast-pair means reach +${CONFIG.minimumTargetedPairLift.toFixed(2)}, every targeted scenario replicate is nonnegative, and the identity negative-control mean and worst replicate are nonnegative. This is narrow follow-up evidence, not a broad effect claim.`
      : `At least one targeted pair was below +${CONFIG.minimumTargetedPairLift.toFixed(2)}, a targeted scenario replicate regressed, or the identity negative control mean/worst replicate regressed; retain recipe-aware context. This is provisional and supports no broad effect claim.`,
    suppressors: [],
  };
}
