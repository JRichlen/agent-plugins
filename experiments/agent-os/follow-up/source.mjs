import { readFile } from "node:fs/promises";
import path from "node:path";
import {
  ARCHIVE_REJUDGE,
  HARD_FAILURES,
  ORIGINAL_ACTUAL_SPEND_USD,
  ORIGINAL_SOURCE,
  SCORE_DIMENSIONS,
  canonicalJson,
  sha256,
  usdToPico,
} from "./config.mjs";

async function readText(file) {
  try {
    return await readFile(file, "utf8");
  } catch (error) {
    throw new Error(`cannot read required source artifact file ${file}: ${error.message}`);
  }
}

async function readJson(file) {
  const text = await readText(file);
  try {
    return { text, value: JSON.parse(text) };
  } catch (error) {
    throw new Error(`invalid JSON in source artifact file ${file}: ${error.message}`);
  }
}

function verifyIntegrity(value, label) {
  if (!value || typeof value !== "object" || typeof value.integrity !== "string") {
    throw new Error(`${label} lacks an integrity digest`);
  }
  const { integrity, ...core } = value;
  const actual = sha256(canonicalJson(core));
  if (actual !== integrity) throw new Error(`${label} integrity digest does not match`);
  return integrity;
}

function safeName(value) {
  return String(value).replace(/[^a-zA-Z0-9._-]+/g, "-");
}

function extractCandidateContent(envelope, callId) {
  const choice = envelope?.choices?.[0];
  if (!choice || typeof choice.message?.content !== "string") {
    throw new Error(`${callId} source response has no assistant text`);
  }
  return choice.message.content;
}

function extractJudgeContent(envelope, scenarioId) {
  const choice = envelope?.choices?.[0];
  if (!choice || typeof choice.message?.content !== "string") {
    throw new Error(`source judge response ${scenarioId} has no assistant text`);
  }
  return choice.message.content;
}

function assertOriginalJudgment(validation, rawContent, scenario, mapping, archivedResponses) {
  if (!validation || typeof validation !== "object" || validation.valid !== true) {
    throw new Error(`source original judgment ${scenario.id} is not valid`);
  }
  if (!Array.isArray(validation.schemaErrors) || validation.schemaErrors.length) {
    throw new Error(`source original judgment ${scenario.id} has schema errors`);
  }
  if (!Array.isArray(validation.reviewIssues)) {
    throw new Error(`source original judgment ${scenario.id} lacks review issues`);
  }
  if (!validation.value || typeof validation.value !== "object" || !Array.isArray(validation.value.responses) || validation.value.responses.length !== mapping.length) {
    throw new Error(`source original judgment ${scenario.id} does not contain four responses`);
  }
  let parsedRaw;
  try {
    parsedRaw = JSON.parse(rawContent);
  } catch (error) {
    throw new Error(`source original judgment ${scenario.id} response is invalid JSON: ${error.message}`);
  }
  if (canonicalJson(parsedRaw) !== canonicalJson(validation.value)) {
    throw new Error(`source original judgment ${scenario.id} does not match its raw judge response`);
  }
  const expectedBlindIds = new Set(mapping.map((item) => item.blindId));
  const expectedContent = new Map(archivedResponses.map((item) => [item.blindId, item.content]));
  const seen = new Set();
  const allowedFailures = new Set([
    ...Object.keys(HARD_FAILURES),
    ...(scenario.judge?.hardFailures ?? []).map((failure) => failure.id),
  ]);
  for (const result of validation.value.responses) {
    if (!result || typeof result !== "object" || !expectedBlindIds.has(result.blindId) || seen.has(result.blindId)) {
      throw new Error(`source original judgment ${scenario.id} has an invalid or duplicate blind ID`);
    }
    seen.add(result.blindId);
    if (!result.scores || typeof result.scores !== "object" || Array.isArray(result.scores) || canonicalJson(Object.keys(result.scores).sort()) !== canonicalJson([...SCORE_DIMENSIONS].sort())) {
      throw new Error(`source original judgment ${scenario.id}/${result.blindId} lacks exactly ten scores`);
    }
    for (const dimension of SCORE_DIMENSIONS) {
      if (!Number.isInteger(result.scores[dimension]) || result.scores[dimension] < 0 || result.scores[dimension] > 4) {
        throw new Error(`source original judgment ${scenario.id}/${result.blindId} has an invalid ${dimension} score`);
      }
    }
    if (!Array.isArray(result.hardFailures)) throw new Error(`source original judgment ${scenario.id}/${result.blindId} lacks hard failures`);
    const failureIds = new Set();
    for (const failure of result.hardFailures) {
      if (!failure || typeof failure.id !== "string" || !allowedFailures.has(failure.id) || failureIds.has(failure.id) || typeof failure.evidence !== "string" || !failure.evidence.trim() || !expectedContent.get(result.blindId)?.includes(failure.evidence)) {
        throw new Error(`source original judgment ${scenario.id}/${result.blindId} has an invalid hard failure`);
      }
      failureIds.add(failure.id);
    }
    if (!Number.isInteger(result.confidence) || result.confidence < 0 || result.confidence > 4) throw new Error(`source original judgment ${scenario.id}/${result.blindId} has invalid confidence`);
    if (typeof result.ambiguous !== "boolean" || typeof result.summary !== "string" || !result.summary.trim()) throw new Error(`source original judgment ${scenario.id}/${result.blindId} has invalid metadata`);
  }
  if (seen.size !== expectedBlindIds.size) throw new Error(`source original judgment ${scenario.id} is missing a blind response`);
}

function assertArchiveScenario(scenario, descriptor) {
  if (typeof scenario.prompt !== "string" || !scenario.prompt.trim()) {
    throw new Error(`archive scenario ${scenario.id} has no prompt`);
  }
  const localIds = new Set((scenario.judge?.hardFailures ?? []).map((failure) => failure.id));
  const allowed = new Set([...Object.keys(HARD_FAILURES), ...localIds]);
  for (const id of descriptor.mustCheckFailureIds) {
    if (!allowed.has(id)) throw new Error(`archive scenario ${scenario.id} cannot require unknown failure ${id}`);
  }
  for (const id of localIds) {
    if (!descriptor.mustCheckFailureIds.includes(id)) {
      throw new Error(`archive scenario ${scenario.id} must explicitly check scenario failure ${id}`);
    }
  }
}

export async function loadSourceArtifact(sourceDir) {
  if (typeof sourceDir !== "string" || !sourceDir) throw new Error("--source requires the downloaded original artifact directory");
  const absolute = path.resolve(sourceDir);
  const manifestFile = path.join(absolute, "manifest.json");
  const preflightFile = path.join(absolute, "preflight.json");
  const blindMapFile = path.join(absolute, "blind-map.json");
  const ledgerFile = path.join(absolute, "ledger.jsonl");
  const [manifestEntry, preflightEntry, blindMapEntry, ledgerText] = await Promise.all([
    readJson(manifestFile),
    readJson(preflightFile),
    readJson(blindMapFile),
    readText(ledgerFile),
  ]);
  const manifestIntegrity = verifyIntegrity(manifestEntry.value, "source manifest");
  const preflightIntegrity = verifyIntegrity(preflightEntry.value, "source preflight");
  const manifest = manifestEntry.value;
  if (manifest.preflight?.integrity !== preflightIntegrity) throw new Error("source manifest does not bind the source preflight");
  if (manifest.provenance?.repository !== ORIGINAL_SOURCE.repository) throw new Error("source repository does not match the immutable original run");
  if (String(manifest.provenance?.runId) !== ORIGINAL_SOURCE.runId || String(manifest.provenance?.runAttempt) !== "1") {
    throw new Error("source run provenance is not immutable run 33281138920 attempt 1");
  }

  const ledger = ledgerText
    .split(/\r?\n/)
    .filter(Boolean)
    .map((line, index) => {
      try {
        return JSON.parse(line);
      } catch (error) {
        throw new Error(`source ledger line ${index + 1} is invalid JSON: ${error.message}`);
      }
    });
  if (ledger.length !== 30 || ledger.filter((row) => row.phase === "candidate").length !== 24) {
    throw new Error("source ledger must contain exactly 24 candidate and 6 judge calls");
  }
  const totalActualPico = ledger.reduce((sum, row) => {
    if (!/^[0-9]+$/.test(String(row.actualCostPicoUsd ?? ""))) throw new Error(`source ledger call ${row.callId} lacks exact cost`);
    return sum + BigInt(row.actualCostPicoUsd);
  }, 0n);
  if (totalActualPico !== usdToPico(ORIGINAL_ACTUAL_SPEND_USD)) {
    throw new Error(`source actual spend is not the recorded $${ORIGINAL_ACTUAL_SPEND_USD}`);
  }
  const ledgerByCall = new Map(ledger.map((row) => [row.callId, row]));
  if (ledgerByCall.size !== ledger.length) throw new Error("source ledger has duplicate call IDs");

  const fileDigests = {
    manifest: sha256(manifestEntry.text),
    preflight: sha256(preflightEntry.text),
    blindMap: sha256(blindMapEntry.text),
    ledger: sha256(ledgerText),
  };
  const scenarios = [];
  for (const [scenarioId, descriptor] of Object.entries(ARCHIVE_REJUDGE).sort((a, b) => a[1].priority - b[1].priority)) {
    const mapping = blindMapEntry.value?.[scenarioId];
    if (!Array.isArray(mapping) || mapping.length !== 4) throw new Error(`source blind map for ${scenarioId} must contain four responses`);
    const mappingIds = mapping.map((item) => item?.blindId);
    if (mapping.some((item) => !item || typeof item.blindId !== "string" || typeof item.candidateCallId !== "string") || new Set(mappingIds).size !== mapping.length) {
      throw new Error(`source blind map for ${scenarioId} has invalid or duplicate lineage rows`);
    }
    const judgeRequestFile = path.join(absolute, "raw", "judge", `judge-${scenarioId}.request.json`);
    const judgeResponseFile = path.join(absolute, "raw", "judge", `judge-${scenarioId}.response.json`);
    const validationFile = path.join(absolute, "raw", "judge", `${scenarioId}.validation.json`);
    const judgeRequestEntry = await readJson(judgeRequestFile);
    const judgeResponseEntry = await readJson(judgeResponseFile);
    const validationEntry = await readJson(validationFile);
    const userMessage = judgeRequestEntry.value?.messages?.at(-1);
    if (userMessage?.role !== "user" || typeof userMessage.content !== "string") {
      throw new Error(`source judge request ${scenarioId} has no serialized user payload`);
    }
    let archived;
    try {
      archived = JSON.parse(userMessage.content);
    } catch (error) {
      throw new Error(`source judge request ${scenarioId} user payload is invalid: ${error.message}`);
    }
    if (!Array.isArray(archived.responses) || archived.responses.length !== 4 || !archived.scenario) {
      throw new Error(`source judge request ${scenarioId} does not contain one complete four-response scenario`);
    }
    const scenario = {
      id: scenarioId,
      prompt: archived.scenario.prompt,
      judge: {
        ...(archived.scenario.judge ?? {}),
        primaryDimensions: archived.scenario.judge?.applicableDimensions ?? SCORE_DIMENSIONS,
      },
      mustCheckFailureIds: [...descriptor.mustCheckFailureIds],
      rejudgePriority: descriptor.priority,
    };
    assertArchiveScenario(scenario, descriptor);
    const originalJudgeContent = extractJudgeContent(judgeResponseEntry.value, scenarioId);
    assertOriginalJudgment(validationEntry.value, originalJudgeContent, scenario, mapping, archived.responses);
    const responses = [];
    for (let index = 0; index < mapping.length; index += 1) {
      const mapRow = mapping[index];
      const stored = archived.responses[index];
      if (stored?.blindId !== mapRow.blindId || typeof stored.content !== "string") {
        throw new Error(`source response order or blind ID mismatch for ${scenarioId}/${mapRow.blindId}`);
      }
      const ledgerRow = ledgerByCall.get(mapRow.candidateCallId);
      if (!ledgerRow || ledgerRow.phase !== "candidate" || ledgerRow.scenarioId !== scenarioId) {
        throw new Error(`source candidate lineage missing for ${mapRow.candidateCallId}`);
      }
      const responseFile = path.join(absolute, "raw", "candidate", `${safeName(mapRow.candidateCallId)}.response.json`);
      const responseEntry = await readJson(responseFile);
      const rawContent = extractCandidateContent(responseEntry.value, mapRow.candidateCallId);
      if (rawContent !== stored.content) {
        throw new Error(`source judge input for ${mapRow.candidateCallId} is not the full raw stored response`);
      }
      const digestKey = `candidate:${mapRow.candidateCallId}`;
      fileDigests[digestKey] = sha256(responseEntry.text);
      responses.push({
        blindId: mapRow.blindId,
        candidateCallId: mapRow.candidateCallId,
        variantId: ledgerRow.variantId,
        content: stored.content,
        contentBytes: Buffer.byteLength(stored.content, "utf8"),
        contentSha256: sha256(stored.content),
        finishReason: ledgerRow.finishReason ?? null,
        sourceGenerationId: ledgerRow.generationId ?? null,
      });
    }
    fileDigests[`judge-request:${scenarioId}`] = sha256(judgeRequestEntry.text);
    fileDigests[`judge-response:${scenarioId}`] = sha256(judgeResponseEntry.text);
    fileDigests[`judgment-validation:${scenarioId}`] = sha256(validationEntry.text);
    scenarios.push({
      scenario,
      responses,
      originalJudgment: {
        value: validationEntry.value.value,
        reviewIssues: validationEntry.value.reviewIssues,
        variantByBlind: Object.fromEntries(responses.map(({ blindId, variantId }) => [blindId, variantId])),
        rawSha256: sha256(originalJudgeContent),
        validationSha256: sha256(validationEntry.text),
      },
    });
  }

  const importedDigest = sha256(
    canonicalJson(
      scenarios.map(({ scenario, responses, originalJudgment }) => ({
        scenarioId: scenario.id,
        prompt: scenario.prompt,
        judge: scenario.judge,
        mustCheckFailureIds: scenario.mustCheckFailureIds,
        responses: responses.map(({ blindId, candidateCallId, variantId, content, finishReason }) => ({ blindId, candidateCallId, variantId, content, finishReason })),
        originalJudgment: {
          value: originalJudgment.value,
          reviewIssues: originalJudgment.reviewIssues,
          variantByBlind: originalJudgment.variantByBlind,
          rawSha256: originalJudgment.rawSha256,
          validationSha256: originalJudgment.validationSha256,
        },
      })),
    ),
  );
  return {
    root: absolute,
    scenarios,
    lineage: {
      source: ORIGINAL_SOURCE,
      runAttempt: "1",
      sourceCommit: manifest.provenance.sha,
      manifestIntegrity,
      preflightIntegrity,
      importedDigest,
      originalActualSpendUsd: ORIGINAL_ACTUAL_SPEND_USD,
      fileDigests,
    },
  };
}
