// providers/lib/ledger.js — shared attempt-id + effect-ledger writing helper,
// used identically by target-textual.js and the three deterministic control
// providers so every target in this lane runs through IDENTICAL machinery
// (design §6: "run through the identical pipeline as the real targets").
'use strict';

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

function attemptId(context) {
  const c = context || {};
  const key = [c.evaluationId, c.testCaseId, c.promptIdx, c.repeatIndex].join('|');
  return crypto.createHash('sha256').update(key).digest('hex');
}

function requireLedgerDir(cfg) {
  const ledgerDir = cfg && cfg.ledgerDir;
  if (typeof ledgerDir !== 'string' || ledgerDir.includes('{{') || ledgerDir.includes('}}')) {
    throw new Error('redteam FAIL provider: ledgerDir not interpolated — REDTEAM_LEDGER_DIR unset');
  }
  return ledgerDir;
}

function writeLedger(ledgerDir, id, entry) {
  fs.mkdirSync(ledgerDir, { recursive: true });
  fs.writeFileSync(path.join(ledgerDir, `${id}.json`), JSON.stringify(entry, null, 2));
}

module.exports = { attemptId, requireLedgerDir, writeLedger };
