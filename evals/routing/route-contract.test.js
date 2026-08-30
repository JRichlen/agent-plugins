#!/usr/bin/env node
// Offline deterministic tests for the typed routing contract (RQ-002 / issue #88).
// No network, no model call — pure node. Proves:
//   1. every scenario's expected ROUTE: line validates against the contract AND
//      matches exactly one per-scenario regex in promptfooconfig.yaml;
//   2. a malformed/ambiguous fixture set REJECTS — each of the 8 fail-closed
//      rules exercised individually;
//   3. the S1 legacy-string negative control: the old single-skill
//      representation (`ROUTE: diagnosing-bugs`, `ROUTE: redgate`) cannot
//      satisfy the composition contract — deterministic proof (no spend) that
//      the old schema is insufficient for S1.
// Wired into evals/cheap/run.sh (RQ-002 section). Exit 0 = all green.
'use strict';
const fs = require('fs');
const path = require('path');

const HERE = __dirname;
const rc = require(path.join(HERE, 'route-contract.js'));

let pass = 0, fail = 0;
function check(name, cond, detail) {
  if (cond) { pass++; console.log(`  PASS ${name}`); }
  else { fail++; console.log(`  FAIL ${name}${detail ? ` — ${detail}` : ''}`); }
}

const roster = rc.loadRoster(path.join(HERE, 'roster.txt'));
check('roster loads as a closed vocabulary', roster.size >= 20 && roster.has('redgate') && roster.has('diagnosing-bugs'));

// ── 1. Every scenario's expected line validates ─────────────────────────────
const EXPECTED = [
  // 8 migrated single-specialist must-fire scenarios
  'ROUTE: specialist=prove-the-undo | envelope=none | guards=none | interaction_owner=none',
  'ROUTE: specialist=find-before-build | envelope=none | guards=none | interaction_owner=none',
  'ROUTE: specialist=egress-gate | envelope=none | guards=none | interaction_owner=none',
  'ROUTE: specialist=stop-rule | envelope=none | guards=none | interaction_owner=none',
  'ROUTE: specialist=semver-gate | envelope=none | guards=none | interaction_owner=none',
  'ROUTE: specialist=tracer-bullets | envelope=none | guards=none | interaction_owner=none',
  'ROUTE: specialist=grill-me | envelope=none | guards=none | interaction_owner=none',
  'ROUTE: specialist=docs-hygiene | envelope=none | guards=none | interaction_owner=none',
  // S1 / S2 / S4 composition labels
  'ROUTE: specialist=diagnosing-bugs | envelope=redgate | guards=verify-before-claim | interaction_owner=redgate',
  'ROUTE: specialist=codebase-design | envelope=none | guards=none | interaction_owner=none',
  'ROUTE: specialist=graveyard | envelope=redgate | guards=prove-the-undo,semver-gate | interaction_owner=redgate',
  // 2 migrated calibration negatives + S3 (all-none)
  'ROUTE: specialist=none | envelope=none | guards=none | interaction_owner=none',
];
for (const line of EXPECTED) {
  const v = rc.validateRoute(line, roster);
  check(`expected line validates: ${line}`, v.pass === true, v.reason);
}

// Cross-check against the shipped config: every expected line must satisfy at
// least one per-scenario regex, and the config must carry one typed regex per
// scenario (14 = 8 migrated + S1 + S2 + S4 + 2 negatives + S3).
const cfgRaw = fs.readFileSync(path.join(HERE, 'promptfooconfig.yaml'), 'utf8');
const cfgRegexes = [...cfgRaw.matchAll(/value: '(ROUTE:[^']*)'/g)].map((m) => m[1]);
check('config carries 14 per-scenario typed ROUTE regexes', cfgRegexes.length === 14, `found ${cfgRegexes.length}`);
for (const line of EXPECTED) {
  const hit = cfgRegexes.some((r) => new RegExp(r).test(line));
  check(`config has a scenario regex matching: ${line.slice(7, 60)}…`, hit);
}

// ── 2. Fail-closed rules, each exercised individually ───────────────────────
const REJECTS = [
  // rule 1 — zero ROUTE lines
  ['no ROUTE line at all', 'I would route this to diagnosing-bugs.', 'rule 1'],
  // rule 1 — more than one ROUTE line
  ['two ROUTE lines',
    'ROUTE: specialist=diagnosing-bugs | envelope=none | guards=none | interaction_owner=none\n' +
    'ROUTE: specialist=none | envelope=none | guards=none | interaction_owner=none', 'rule 1'],
  // rule 1 — non-whitespace text after the line
  ['prose after the ROUTE line',
    'ROUTE: specialist=diagnosing-bugs | envelope=none | guards=none | interaction_owner=none\nHope that helps!', 'rule 1'],
  // rule 2 — missing key / wrong order / unknown separator
  ['missing interaction_owner key', 'ROUTE: specialist=diagnosing-bugs | envelope=none | guards=none', 'rule 2'],
  ['keys out of order', 'ROUTE: envelope=none | specialist=diagnosing-bugs | guards=none | interaction_owner=none', 'rule 2'],
  ['semicolon separator', 'ROUTE: specialist=diagnosing-bugs; envelope=none; guards=none; interaction_owner=none', 'rule 2'],
  // rule 3 — name outside the roster (closed vocabulary)
  ['unknown skill name', 'ROUTE: specialist=made-up-skill | envelope=none | guards=none | interaction_owner=none', 'rule 3'],
  ['unknown guard name', 'ROUTE: specialist=diagnosing-bugs | envelope=none | guards=not-a-skill | interaction_owner=none', 'rule 3'],
  // rule 4 — redgate may never occupy specialist
  ['redgate as specialist', 'ROUTE: specialist=redgate | envelope=none | guards=none | interaction_owner=redgate', 'rule 4'],
  // rule 5 — a skill in two slots (the hedging router)
  ['same skill in specialist and guards', 'ROUTE: specialist=diagnosing-bugs | envelope=none | guards=diagnosing-bugs | interaction_owner=none', 'rule 5'],
  ['same skill in envelope and guards', 'ROUTE: specialist=diagnosing-bugs | envelope=redgate | guards=redgate | interaction_owner=redgate', 'rule 5'],
  // rule 6 — interaction_owner outside specialist ∪ envelope
  ['guard as interaction owner', 'ROUTE: specialist=diagnosing-bugs | envelope=none | guards=verify-before-claim | interaction_owner=verify-before-claim', 'rule 6'],
  ['absent skill as interaction owner', 'ROUTE: specialist=diagnosing-bugs | envelope=none | guards=none | interaction_owner=grill-me', 'rule 6'],
  // rule 7 — a slot mixing none with a name
  ['guards mixes none with a name', 'ROUTE: specialist=diagnosing-bugs | envelope=none | guards=none,verify-before-claim | interaction_owner=none', 'rule 7'],
  ['envelope mixes a name with none', 'ROUTE: specialist=diagnosing-bugs | envelope=redgate,none | guards=none | interaction_owner=redgate', 'rule 7'],
  // rule 8 — set slots sorted and deduped
  ['guards unsorted', 'ROUTE: specialist=graveyard | envelope=redgate | guards=semver-gate,prove-the-undo | interaction_owner=redgate', 'rule 8'],
  ['guards duplicated', 'ROUTE: specialist=graveyard | envelope=redgate | guards=prove-the-undo,prove-the-undo | interaction_owner=redgate', 'rule 8'],
];
for (const [name, output, rule] of REJECTS) {
  const v = rc.validateRoute(output, roster);
  check(`rejects (${rule}): ${name}`, v.pass === false, `accepted: ${v.reason}`);
}

// ── 3. S1 legacy-string negative control ────────────────────────────────────
// Under the old single-skill schema, S1 ("payment webhook double-charge with
// explicit evidence demands") had two defensible answers. BOTH legacy strings
// must fail the composition contract AND fail S1's per-scenario regex — the
// deterministic proof (acceptance criterion 1) that the old representation is
// insufficient, with no model spend.
const s1Regex = cfgRegexes.find((r) => r.includes('specialist=diagnosing-bugs'));
check('found S1 scenario regex in the config', Boolean(s1Regex));
for (const legacy of ['ROUTE: diagnosing-bugs', 'ROUTE: redgate']) {
  const v = rc.validateRoute(legacy, roster);
  check(`legacy string fails the contract: "${legacy}"`, v.pass === false, `accepted: ${v.reason}`);
  if (s1Regex) {
    check(`legacy string fails S1's scenario regex: "${legacy}"`, !new RegExp(s1Regex).test(legacy));
  }
}
// The correct composed answer, for contrast, passes both.
const s1Line = 'ROUTE: specialist=diagnosing-bugs | envelope=redgate | guards=verify-before-claim | interaction_owner=redgate';
check('S1 composed line passes contract AND scenario regex',
  rc.validateRoute(s1Line, roster).pass === true && Boolean(s1Regex) && new RegExp(s1Regex).test(s1Line));

// ── Round-trip: the promptfoo entry point agrees with validateRoute ─────────
const asAssertion = rc(EXPECTED[0], { vars: {} });
check('promptfoo assertion entry point passes a valid line', asAssertion.pass === true);
const asAssertionBad = rc('ROUTE: redgate', { vars: {} });
check('promptfoo assertion entry point fails a legacy line', asAssertionBad.pass === false);

console.log(`\nroute-contract.test: ${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
