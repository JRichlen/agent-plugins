'use strict';
const path = require('path');
const { spawnSync } = require('child_process');
const checker = path.resolve(__dirname, '../../bin/verify_task.py');
// Used only by deterministic calibration providers; live subjects never receive
// the fixture output, and must return their own artifacts for the same grader.
function oracleArtifacts(vars) {
  if (!vars.task_card || vars.utility_evidence !== 'artifact-verifier-v1') {
    throw new Error('task fixture requires task_card and artifact-verifier-v1');
  }
  const result = spawnSync('python3', [checker, '--oracle', vars.task_card], {
    encoding: 'utf8', timeout: 30000, maxBuffer: 4000000,
  });
  if (result.error || result.status !== 0) throw new Error(`task fixture: ${result.error || result.stderr}`);
  return result.stdout.trimEnd();
}
module.exports = { oracleArtifacts };
