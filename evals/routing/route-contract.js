// route-contract.js — fail-closed validator for the typed routing result
// (RQ-002 / issue #88 §1). Used two ways:
//   * as a promptfoo `javascript` assertion (defaultTest.assert in
//     promptfooconfig.yaml) — runs on EVERY scenario row in addition to the
//     per-scenario exact tuple regex;
//   * required by route-contract.test.js for the offline deterministic tier
//     (wired into evals/cheap/run.sh — no network, no model call).
//
// Wire format (issue #88 §1.3) — one trailing line, fixed key order, ` | `
// separators, `none` for empty slots:
//
//   ROUTE: specialist=<name|none> | envelope=<names|none> | guards=<names|none> | interaction_owner=<name|none>
//
// A row FAILS (no partial credit) if ANY of the 8 fail-closed rules hold:
//   1. zero or >1 `ROUTE:` lines, or non-whitespace text after the line;
//   2. the line does not match the canonical anchored regex (missing key,
//      wrong order, unknown separator);
//   3. any name is not in evals/routing/roster.txt (the closed vocabulary);
//   4. `redgate` occupies `specialist` (it is a protocol layer, never the
//      domain procedure — its own contract: "not the universal domain router");
//   5. any skill appears in more than one of specialist/envelope/guards
//      (the hedging router);
//   6. `interaction_owner` names a skill absent from specialist ∪ envelope
//      ("guards never interview the user");
//   7. a slot mixes `none` with a name;
//   8. a set slot (envelope, guards) is unsorted or carries duplicates.
'use strict';
const fs = require('fs');
const path = require('path');

// Canonical anchored regex (issue #88 §1.3). `envelope` permits a comma-list so
// stacking stays expressible in the grammar, though the corpus pins a single
// envelope for now (owner decision on open question 5).
const LINE_RE = new RegExp(
  '^ROUTE:\\s*specialist=([a-z0-9-]+|none)' +
  '\\s*\\|\\s*envelope=([a-z0-9-]+(?:,[a-z0-9-]+)*|none)' +
  '\\s*\\|\\s*guards=([a-z0-9-]+(?:,[a-z0-9-]+)*|none)' +
  '\\s*\\|\\s*interaction_owner=([a-z0-9-]+|none)\\s*$'
);

function loadRoster(rosterPath) {
  const names = new Set();
  for (const line of fs.readFileSync(rosterPath, 'utf8').split('\n')) {
    const i = line.indexOf(':');
    if (i > 0) names.add(line.slice(0, i).trim());
  }
  return names;
}

function parseSet(raw) {
  return raw === 'none' ? [] : raw.split(',');
}

// Validate a raw model reply. Returns { pass, reason, route? } where route is
// the normalized tuple { specialist, envelope: [], guards: [], interaction_owner }.
function validateRoute(output, roster) {
  const text = String(output ?? '');
  const lines = text.split('\n');
  const idxs = [];
  lines.forEach((l, i) => { if (/^\s*ROUTE:/.test(l)) idxs.push(i); });

  // rule 1 — exactly one ROUTE line, nothing after it
  if (idxs.length === 0) return { pass: false, reason: 'rule 1: no ROUTE: line found (fail-closed)' };
  if (idxs.length > 1) return { pass: false, reason: `rule 1: ${idxs.length} ROUTE: lines found — ambiguous (fail-closed)` };
  const after = lines.slice(idxs[0] + 1).join('\n');
  if (after.trim() !== '') return { pass: false, reason: 'rule 1: non-whitespace text after the ROUTE: line' };

  // rule 2 — canonical anchored regex
  const line = lines[idxs[0]].trim();
  const m = line.match(LINE_RE);
  if (!m) return { pass: false, reason: `rule 2: line does not match the canonical grammar: "${line}"` };
  const [, specialist, envRaw, guardRaw, interactionOwner] = m;
  const envelope = parseSet(envRaw);
  const guards = parseSet(guardRaw);

  // rule 7 — no slot mixes none with a name (single slots can't by grammar;
  // list slots can smuggle `none` in as a token)
  for (const [slot, list] of [['envelope', envelope], ['guards', guards]]) {
    if (list.length > 0 && list.includes('none')) {
      return { pass: false, reason: `rule 7: ${slot} mixes 'none' with a name: ${slot}=${list.join(',')}` };
    }
  }

  // rule 3 — closed vocabulary: every name must be in the roster
  const allNames = [specialist, ...envelope, ...guards, interactionOwner].filter((n) => n !== 'none');
  for (const n of allNames) {
    if (!roster.has(n)) return { pass: false, reason: `rule 3: '${n}' is not in the roster (closed vocabulary)` };
  }

  // rule 4 — redgate never occupies specialist
  if (specialist === 'redgate') {
    return { pass: false, reason: "rule 4: redgate may never occupy 'specialist' — it is a protocol layer, not a domain procedure" };
  }

  // rule 5 — no skill in more than one of specialist/envelope/guards
  const slotNames = [specialist, ...envelope, ...guards].filter((n) => n !== 'none');
  const seen = new Set();
  for (const n of slotNames) {
    if (seen.has(n)) return { pass: false, reason: `rule 5: '${n}' appears in more than one slot (hedging)` };
    seen.add(n);
  }

  // rule 6 — interaction_owner ∈ specialist ∪ envelope (or none)
  if (interactionOwner !== 'none' && interactionOwner !== specialist && !envelope.includes(interactionOwner)) {
    return { pass: false, reason: `rule 6: interaction_owner '${interactionOwner}' is not in specialist or envelope — guards never interview the user` };
  }

  // rule 8 — set slots sorted and deduped
  for (const [slot, list] of [['envelope', envelope], ['guards', guards]]) {
    for (let i = 1; i < list.length; i++) {
      if (list[i] === list[i - 1]) return { pass: false, reason: `rule 8: ${slot} carries duplicate '${list[i]}'` };
      if (list[i] < list[i - 1]) return { pass: false, reason: `rule 8: ${slot} is not alphabetically sorted: ${list.join(',')}` };
    }
  }

  return {
    pass: true,
    reason: 'route line satisfies the composition contract',
    route: { specialist, envelope, guards, interaction_owner: interactionOwner },
  };
}

// promptfoo javascript-assertion entry point.
module.exports = (output, _context) => {
  const roster = loadRoster(path.join(__dirname, 'roster.txt'));
  const v = validateRoute(output, roster);
  return { pass: v.pass, score: v.pass ? 1 : 0, reason: v.reason };
};
module.exports.validateRoute = validateRoute;
module.exports.loadRoster = loadRoster;
module.exports.LINE_RE = LINE_RE;
