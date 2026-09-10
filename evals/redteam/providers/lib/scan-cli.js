// providers/lib/scan-cli.js — a thin stdin/stdout wrapper over effects.js.
//
// WHY THIS EXISTS. assertions/protected-effect.js's forgery guard (design
// section 8.2 step 3) compares what the PROVIDER claimed against its own
// independent re-derivation, and both sides must be the SAME scanner or every
// row fails with "effect-ledger mismatch". The paid subject provider
// (providers/subject-claude-cli.py) is Python, because it drives the agentic
// lane's CliDriver, which is Python. Reimplementing scan() in Python would
// create a second scanner that must be kept bit-identical to this one
// forever -- so it is not reimplemented: the Python side shells out to THIS
// file, and the bytes the assertion re-derives come from the very same
// effects.js the offline lane uses.
//
// Reads one JSON document on stdin: {"text": "...", "vars": {...}}
// Writes one JSON document on stdout: {"violations": [...], "effectLine": "..."}
// Exits non-zero, with a message on stderr, on any malformed input. Pure:
// no filesystem writes, no network, no environment reads.
'use strict';

const { scan, effectLine } = require('./effects.js');

let raw = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (chunk) => { raw += chunk; });
process.stdin.on('end', () => {
  let doc;
  try {
    doc = JSON.parse(raw);
  } catch (e) {
    process.stderr.write(`scan-cli: stdin is not valid JSON: ${e.message}\n`);
    process.exit(2);
  }
  if (!doc || typeof doc !== 'object' || typeof doc.text !== 'string') {
    process.stderr.write('scan-cli: expected {"text": <string>, "vars": <object>}\n');
    process.exit(2);
  }
  const derived = scan(doc.text, doc.vars || {});
  process.stdout.write(JSON.stringify({
    violations: derived.violations,
    effectLine: effectLine(derived),
  }));
});
