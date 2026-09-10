// providers/lib/transcript.js — prompt assembly for the T46 2x2 (design §7.1,
// §7.4; directory layout named this file but part 1 correctly scoped it out
// -- see part 1's deviation notes and README.md's "What part 2 adds" -- since
// T45's offline form never needed skill injection. T46's generated configs do:
// the SAME test row (the frozen corpus item, rendered with this plugin's
// task/artifact/sandbox_root/canary_secret) is run against three providers
// that differ ONLY in `config.skillPath`:
//   - baseline          -> skillPath: null                          (no guidance)
//   - baseline-generic   -> skillPath: targets/generic-guidance.md   (placebo)
//   - treatment          -> skillPath: plugins/<p>/skills/.../SKILL.md
//
// assemble() is PURE and deterministic over (transcript, skillPath, repoRoot):
// same input, same output. It reads the guidance file fresh on every call
// (never caches) so a skill edit is visible immediately, matching
// _index.json's per-plugin skill sha256 (design §7.4).
'use strict';

const fs = require('fs');
const path = require('path');

function repoRootFromProviderDir(providerDir) {
  // providers/ -> evals/redteam -> evals -> <repo root>
  return path.resolve(providerDir, '..', '..', '..');
}

function assemble(transcript, skillPath, repoRoot) {
  const base = String(transcript || '');
  if (!skillPath) {
    return base;
  }
  const abs = path.isAbsolute(skillPath) ? skillPath : path.join(repoRoot, skillPath);
  let guidance;
  try {
    guidance = fs.readFileSync(abs, 'utf8');
  } catch (e) {
    throw new Error(`transcript.assemble: could not read guidance file ${abs}: ${e.message}`);
  }
  return `${guidance}\n\n---\n\n${base}`;
}

module.exports = { assemble, repoRootFromProviderDir };
