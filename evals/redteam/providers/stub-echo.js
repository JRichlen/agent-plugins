// providers/stub-echo.js — minimal provider for T43 conformance (design §1).
//
// The smallest possible provider that still satisfies the documented
// ApiProvider contract (a class, `new`-invoked — design §3.2): echoes the
// prompt back with a fixed tokenUsage, and writes a side-channel file into
// `config.sideChannelDir` on every call, which is the mechanism
// test_redteam_provider.py uses to prove promptfoo's own loader actually
// invoked `callApi` (the same technique as design evidence E2), independent
// of the ledger-writing machinery the real target/control providers share.
'use strict';

const fs = require('fs');
const path = require('path');

class StubEchoProvider {
  constructor(options) {
    this.providerId = (options && options.id) || 'stub-echo';
    this.config = (options && options.config) || {};
  }

  id() { return this.providerId; }
  toString() { return `[Stub Echo ${this.providerId}]`; }

  async callApi(prompt, context) {
    const cfg = this.config || {};
    if (cfg.sideChannelDir) {
      fs.mkdirSync(cfg.sideChannelDir, { recursive: true });
      const marker = `${Date.now()}-${Math.random().toString(36).slice(2)}.txt`;
      fs.writeFileSync(path.join(cfg.sideChannelDir, marker), String(prompt || ''));
    }
    return {
      output: `echo: ${prompt}`,
      tokenUsage: { total: 10, prompt: 5, completion: 5 },
    };
  }
}

module.exports = StubEchoProvider;
