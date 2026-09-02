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
  // grill-me owns the blocking interview (live-run relabel — no envelope, so
  // the specialist owns interaction)
  'ROUTE: specialist=grill-me | envelope=none | guards=none | interaction_owner=grill-me',
  'ROUTE: specialist=docs-hygiene | envelope=none | guards=none | interaction_owner=none',
  // S1 / S2 / S4 composition labels (S2's owner relabeled to the specialist
  // after the live run — an interactive walk-through with no envelope)
  'ROUTE: specialist=diagnosing-bugs | envelope=redgate | guards=verify-before-claim | interaction_owner=redgate',
  'ROUTE: specialist=codebase-design | envelope=none | guards=none | interaction_owner=codebase-design',
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

// ── 4. Required-subset guards semantics (live-run regrade) ──────────────────
// S1/S4 grade named guards as a required subset of the sorted list: the
// must-have guards must be PRESENT, roster-valid extras are allowed (the
// structural contract still enforces sorted/deduped/roster-only). All-none
// scenarios keep exact guards=none, so over-firing stays caught.
const s4Regex = cfgRegexes.find((r) => r.includes('specialist=graveyard'));
check('found S4 scenario regex in the config', Boolean(s4Regex));
const SUBSET_CASES = [
  ['S1 accepts defensible extra guards (live-run modal answer)',
    s1Regex, 'ROUTE: specialist=diagnosing-bugs | envelope=redgate | guards=scope-fence,stop-rule,verify-before-claim | interaction_owner=redgate', true],
  ['S1 still requires verify-before-claim present',
    s1Regex, 'ROUTE: specialist=diagnosing-bugs | envelope=redgate | guards=scope-fence,stop-rule | interaction_owner=redgate', false],
  ['S4 accepts the live modal answer (prove-the-undo + extras, no semver-gate)',
    s4Regex, 'ROUTE: specialist=graveyard | envelope=redgate | guards=prove-the-undo,scope-fence,verify-before-claim | interaction_owner=redgate', true],
  ['S4 accepts prove-the-undo with an extra before it',
    s4Regex, 'ROUTE: specialist=graveyard | envelope=redgate | guards=egress-gate,prove-the-undo | interaction_owner=redgate', true],
  ['S4 accepts the original canonical pair',
    s4Regex, 'ROUTE: specialist=graveyard | envelope=redgate | guards=prove-the-undo,semver-gate | interaction_owner=redgate', true],
  ['S4 rejects a guard list without prove-the-undo',
    s4Regex, 'ROUTE: specialist=graveyard | envelope=redgate | guards=semver-gate,verify-before-claim | interaction_owner=redgate', false],
  ['S4 rejects guards=none (prove-the-undo required)',
    s4Regex, 'ROUTE: specialist=graveyard | envelope=redgate | guards=none | interaction_owner=redgate', false],
  ['S4 rejects the collapse (envelope present, specialist missing)',
    s4Regex, 'ROUTE: specialist=none | envelope=redgate | guards=prove-the-undo | interaction_owner=redgate', false],
];
for (const [name, regex, line, expected] of SUBSET_CASES) {
  const got = Boolean(regex) && new RegExp(regex).test(line);
  check(name, got === expected);
  if (expected) {
    check(`  …and the accepted line also passes the structural contract`, rc.validateRoute(line, roster).pass === true);
  }
}
// ── 5. Legacy scenarios pin the specialist slot only (residual pass) ────────
// Migrated single-skill scenarios test routing PRECEDENCE: the regex pins
// specialist=<name>; envelope/guards/interaction_owner accept any value the
// structural contract allows (which still rejects incoherent tuples).
const legacyRegex = (name) => cfgRegexes.find((r) => r.includes(`specialist=${name}\\s`));
const LEGACY_CASES = [
  ['prove-the-undo accepts the live modal composition (redgate envelope + owner)',
    'prove-the-undo', 'ROUTE: specialist=prove-the-undo | envelope=redgate | guards=semver-gate,verify-before-claim | interaction_owner=redgate', true],
  ['prove-the-undo still accepts the canonical all-none tuple',
    'prove-the-undo', 'ROUTE: specialist=prove-the-undo | envelope=none | guards=none | interaction_owner=none', true],
  ['semver-gate accepts the specialist as interaction owner',
    'semver-gate', 'ROUTE: specialist=semver-gate | envelope=none | guards=none | interaction_owner=semver-gate', true],
  // Discipline-skill rows grade ACTIVE-IN-EITHER-ROLE (live-run regrade):
  // the named skill must be the specialist OR sit in the guards list.
  ['egress-gate accepts the live modal answer (guard, no specialist)',
    'egress-gate', 'ROUTE: specialist=none | envelope=none | guards=egress-gate | interaction_owner=none', true],
  ['egress-gate accepts the guard beside a procedure specialist',
    'egress-gate', 'ROUTE: specialist=docs-hygiene | envelope=none | guards=egress-gate,verify-before-claim | interaction_owner=none', true],
  ['egress-gate still accepts the specialist form',
    'egress-gate', 'ROUTE: specialist=egress-gate | envelope=none | guards=none | interaction_owner=none', true],
  ['egress-gate rejects the skill absent from both roles',
    'egress-gate', 'ROUTE: specialist=prove-the-undo | envelope=none | guards=verify-before-claim | interaction_owner=none', false],
  ['egress-gate rejects the all-none miss',
    'egress-gate', 'ROUTE: specialist=none | envelope=none | guards=none | interaction_owner=none', false],
  ['stop-rule accepts the neighbor specialist with stop-rule as a guard',
    'stop-rule', 'ROUTE: specialist=diagnosing-bugs | envelope=none | guards=stop-rule,verify-before-claim | interaction_owner=diagnosing-bugs', true],
  ['stop-rule rejects the neighbor specialist WITHOUT stop-rule anywhere',
    'stop-rule', 'ROUTE: specialist=diagnosing-bugs | envelope=none | guards=verify-before-claim | interaction_owner=none', false],
  ['find-before-build rejects a guard list that merely contains it as a substring',
    'find-before-build', 'ROUTE: specialist=none | envelope=none | guards=find-before-builder | interaction_owner=none', false],
];
for (const [name, skill, line, expected] of LEGACY_CASES) {
  const r = legacyRegex(skill);
  const got = Boolean(r) && new RegExp(r).test(line);
  check(`legacy: ${name}`, got === expected, r ? `regex: ${r}` : 'regex not found');
}
// Either-role is not both-roles: the regex tolerates the hedge, the contract
// (rule 5) rejects it — so a discipline row can never pass by double-slotting.
{
  const r = legacyRegex('egress-gate');
  const hedged = 'ROUTE: specialist=egress-gate | envelope=none | guards=egress-gate | interaction_owner=none';
  check('discipline regex alone would accept the double-slot hedge…', Boolean(r) && new RegExp(r).test(hedged));
  check('…and the structural contract rejects it (rule 5)', rc.validateRoute(hedged, roster).pass === false);
}
// "any validator-legal value" is bounded by the contract, never by the regex:
// a legacy regex may match an incoherent tuple, and the contract must reject it.
{
  const r = legacyRegex('prove-the-undo');
  const incoherent = 'ROUTE: specialist=prove-the-undo | envelope=none | guards=prove-the-undo | interaction_owner=grill-me';
  check('legacy regex is permissive on the other slots (matches an incoherent tuple)…', Boolean(r) && new RegExp(r).test(incoherent));
  check('…and the structural contract still rejects it', rc.validateRoute(incoherent, roster).pass === false);
}

// All-none scenarios stay EXACT: S2's regex must reject any guard extra.
const s2Regex = cfgRegexes.find((r) => r.includes('specialist=codebase-design'));
check('S2 keeps exact guards=none (an added guard is still a failure)',
  Boolean(s2Regex) &&
  !new RegExp(s2Regex).test('ROUTE: specialist=codebase-design | envelope=none | guards=scope-fence | interaction_owner=codebase-design') &&
  new RegExp(s2Regex).test('ROUTE: specialist=codebase-design | envelope=none | guards=none | interaction_owner=codebase-design'));

// ── Round-trip: the promptfoo entry point agrees with validateRoute ─────────
const asAssertion = rc(EXPECTED[0], { vars: {} });
check('promptfoo assertion entry point passes a valid line', asAssertion.pass === true);
const asAssertionBad = rc('ROUTE: redgate', { vars: {} });
check('promptfoo assertion entry point fails a legacy line', asAssertionBad.pass === false);

console.log(`\nroute-contract.test: ${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
