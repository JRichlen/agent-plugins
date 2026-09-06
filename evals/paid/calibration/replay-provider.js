// replay-provider.js — a promptfoo custom provider that returns CACHED subject
// outputs instead of calling a model (issue #102, measurement 3).
//
// The grader-agreement workflow re-grades the outputs of a finished run with a
// second grader, or with the same grader again. The subject must not be called
// again (that would grade new text, not the same text), so this provider plays
// the recorded output back: evals/paid/calibration/regrade.sh writes a map of
// sample hash -> output and a test per sample whose `__replay` var carries the
// hash; promptfoo then runs only the assertions, with whatever grader the
// overlay names.
//
// Config: { file: "<path to the replay map>" } (or REPLAY_FILE in the env).
// A missing key is an error, never an empty output: an empty output would be
// graded, and a graded blank is exactly the wrong kind of quiet.
'use strict';
const fs = require('fs');

class ReplayProvider {
  constructor(options) {
    const cfg = (options && options.config) || {};
    this.file = cfg.file || process.env.REPLAY_FILE;
    this.map = null;
  }
  id() { return 'replay'; }
  toString() { return '[Replay Provider]'; }
  load() {
    if (this.map) return;
    if (!this.file) throw new Error('replay: no replay file (config.file or REPLAY_FILE)');
    this.map = JSON.parse(fs.readFileSync(this.file, 'utf8'));
  }
  async callApi(prompt, context) {
    this.load();
    const key = context && context.vars ? context.vars.__replay : undefined;
    if (!key) return { error: 'replay: test has no __replay var' };
    if (!Object.prototype.hasOwnProperty.call(this.map, key)) return { error: `replay: no cached output for ${key}` };
    return { output: this.map[key] };
  }
}
module.exports = ReplayProvider;
