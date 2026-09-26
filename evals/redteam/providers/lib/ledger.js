// providers/lib/ledger.js — shared attempt-id + effect-ledger writing helper,
// used identically by target-textual.js and the three deterministic control
// providers so every target in this lane runs through IDENTICAL machinery
// (design §6: "run through the identical pipeline as the real targets").
'use strict';

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

// Canonical JSON: object keys sorted at every depth, so the same vars always
// stringify to the same bytes regardless of insertion order.
function canonicalize(value) {
  if (value === undefined) return 'null';
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonicalize).join(',')}]`;
  return `{${Object.keys(value).sort()
    .map((k) => `${JSON.stringify(k)}:${canonicalize(value[k])}`)
    .join(',')}}`;
}

// The per-attempt identity for the effect ledger and for bin/verdict.py's
// provenance map. It MUST be unique per (row x arm x repeat), because
// writeLedger() names the ledger file after it and verdict.py keys its
// `ledger_entries` dict on it.
//
// It previously hashed `[evaluationId, testCaseId, promptIdx, repeatIndex]`.
// PROBED DIRECTLY against promptfoo 0.122.0 (a provider returning
// Object.keys(context)): the context this version actually passes is
//
//   ['vars','prompt','filters','originalProvider','test','logger',
//    'getCache','repeatIndex','evaluationId']
//
// -- `testCaseId` and `promptIdx` DO NOT EXIST. Both were therefore
// `undefined` on every call and the id degenerated to
// sha256(evaluationId + '|undefined|undefined|' + repeatIndex): with
// `repeat: 3`, exactly THREE distinct ids for a whole 288-row eval.
// Measured on a real `voice.yaml` run: 288 rows, 3 distinct attemptIds, 3
// ledger files, each overwritten ~96 times -- 1% of the evidence retained,
// two different corpus rows in two different arms sharing one attempt id,
// and verdict.py's qualify() inspecting 3 synthetic attempts while blessing
// 288 rows.
//
// The identity is now built only from fields this pinned version really
// supplies: the eval, the PROVIDER (the arm -- distinct `file://` ids per
// design §7.3), the repeat index, and a canonical digest of the row's own
// rendered `vars` (which carry transcript/family/condition/corpus_sha256 and
// so identify the corpus row exactly). Callers pass their own provider id
// explicitly rather than this helper guessing at a context field, so a
// future promptfoo that renames things cannot silently collapse the id
// again -- and the `v2|` prefix keeps old ledger files from ever colliding
// with new ones.
function attemptId(context, providerId) {
  const c = context || {};
  const key = [
    'v2',
    c.evaluationId,
    providerId === undefined || providerId === null ? '' : String(providerId),
    c.repeatIndex,
    canonicalize(c.vars || {}),
  ].join('|');
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

module.exports = { attemptId, canonicalize, requireLedgerDir, writeLedger };
