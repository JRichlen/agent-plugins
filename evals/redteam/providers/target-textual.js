// providers/target-textual.js — the real target provider (design §3.3),
// implementing 0.122.0's documented ApiProvider contract exactly as quoted
// in the design (a class, `new`-invoked by promptfoo's own factory —
// providers-DKidnSQu.js:22754 — never a plain object export; see §3.2).
'use strict';

const { scan, effectLine } = require('./lib/effects.js');
const { attemptId, requireLedgerDir, writeLedger } = require('./lib/ledger.js');
const { assemble, repoRootFromProviderDir } = require('./lib/transcript.js');

const REPO_ROOT = repoRootFromProviderDir(__dirname);

class TextualTargetProvider {
  constructor(options) {
    this.providerId = (options && options.id) || 'redteam:textual';
    this.config = (options && options.config) || {};
  }

  id() {
    return this.providerId;
  }

  toString() {
    return `[Redteam Textual Target ${this.providerId}]`;
  }

  async callApi(prompt, context, options) {
    const cfg = this.config || {};
    const vars = (context && context.vars) || {};

    // ledgerDir must actually be interpolated. promptfoo's renderEnvOnlyInObject
    // returns the literal `{{...}}` unchanged when the referenced env var is
    // unset (design §3.3 step 4) rather than failing, so this check is load-bearing.
    const ledgerDir = requireLedgerDir(cfg);

    if (cfg.behavior === 'throw') {
      throw new Error(`redteam:textual deliberate throw (behavior=throw, plugin=${cfg.plugin || 'unknown'})`);
    }

    const id = attemptId(context, this.providerId);
    // T46 (design §7.1/§7.4): baseline/baseline-generic/treatment differ ONLY
    // in cfg.skillPath -- null (no guidance), targets/generic-guidance.md
    // (the placebo), or a real plugin SKILL.md path. Absent for T43/T45
    // callers (offline-stub, control-*), where assemble() is a no-op.
    const subjectText = assemble(String(prompt || ''), cfg.skillPath || null, REPO_ROOT);
    const derived = scan(subjectText, vars);
    const line = effectLine(derived);

    const ledgerEntry = {
      attempt_id: id,
      arm: cfg.arm || null,
      plugin: cfg.plugin || null,
      condition: vars.condition || null,
      corpus_sha256: vars.corpus_sha256 || null,
      effects: derived,
      effect_line: line,
      provenance: 'simulated',
    };
    writeLedger(ledgerDir, id, ledgerEntry);

    // T46's utility assertion (task-completed.js) checks for
    // vars.completion_marker on clean rows only. This scripted echo target
    // otherwise never performs any task at all, which would make every
    // clean row FAIL utility unconditionally and make the utility dimension
    // of the interaction (design §7.1) uninformative by construction.
    // Mirrors providers/control-safe.js's clean-row convention exactly.
    const completionSuffix = (vars.condition === 'clean' && vars.completion_marker)
      ? `\n${vars.completion_marker}`
      : '';
    const outputText = `${subjectText}${completionSuffix}\n${line}`;

    return {
      output: outputText,
      metadata: {
        effects: derived,
        effectLine: line,
        arm: cfg.arm || null,
        condition: vars.condition || null,
        plugin: cfg.plugin || null,
        corpusSha256: vars.corpus_sha256 || null,
        attemptId: id,
        provenance: 'simulated',
      },
      // tokenUsage intentionally absent for a scripted target: this lane
      // never fabricates a token count. The agentic accounting lane's own
      // convention is UNKNOWN, never 0, for anything not actually reported.
    };
  }

  async cleanup() {
    // No long-lived resources held by this provider today; present for
    // interface completeness (ApiProvider.cleanup? per index.d.ts).
  }
}

module.exports = TextualTargetProvider;
