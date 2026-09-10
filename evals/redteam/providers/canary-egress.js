// providers/canary-egress.js — the non-vacuity canary (design §10.4).
//
// Attempts three things and records each outcome; NEVER emits a packet to
// the public internet in either mode (a reserved TLD, a loopback port a
// caller stands up itself, and RFC 5737 TEST-NET-1, guaranteed unroutable).
// Run through promptfoo (configs/canary-egress.yaml) so the canary takes the
// exact same process path a real eval would, inside whatever sandbox
// bin/netproof.sh has selected.
//
// config: { outFile: <path>, port: <int>, hostSide: bool }
// `port` is a loopback listener bin/netproof.sh starts itself; `hostSide`
// distinguishes the in-sandbox run from the outside-the-sandbox positive
// control (design §10.4's "the same canary run *outside* the container").
'use strict';

const fs = require('fs');
const path = require('path');
const dns = require('dns');
const net = require('net');

function tcpProbe(host, port, timeoutMs) {
  return new Promise((resolve) => {
    const sock = new net.Socket();
    let done = false;
    const finish = (ok, error) => {
      if (done) return;
      done = true;
      try { sock.destroy(); } catch (_e) { /* noop */ }
      resolve({ ok, error: error || null });
    };
    sock.setTimeout(timeoutMs);
    sock.once('connect', () => finish(true, null));
    sock.once('timeout', () => finish(false, 'ETIMEDOUT'));
    sock.once('error', (err) => finish(false, (err && err.code) || String(err)));
    sock.connect(port, host);
  });
}

function dnsProbe(hostname, timeoutMs) {
  return new Promise((resolve) => {
    let done = false;
    const timer = setTimeout(() => {
      if (done) return;
      done = true;
      resolve({ ok: false, error: 'ETIMEDOUT' });
    }, timeoutMs);
    dns.lookup(hostname, (err, address) => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      if (err) resolve({ ok: false, error: err.code || String(err) });
      else resolve({ ok: true, error: null, address });
    });
  });
}

class CanaryEgressProvider {
  constructor(options) {
    this.providerId = (options && options.id) || 'redteam:canary-egress';
    this.config = (options && options.config) || {};
  }

  id() { return this.providerId; }
  toString() { return `[Redteam Canary Egress ${this.providerId}]`; }

  async callApi() {
    const cfg = this.config || {};
    const port = Number(cfg.port || process.env.REDTEAM_CANARY_PORT || 0);

    const [dnsResult, loopbackResult, testnetResult] = await Promise.all([
      dnsProbe('redteam-canary.invalid', 2000),
      port ? tcpProbe('127.0.0.1', port, 2000) : Promise.resolve({ ok: false, error: 'NO_PORT_CONFIGURED' }),
      tcpProbe('192.0.2.1', 443, 2000),
    ]);

    const summary = {
      hostSide: cfg.hostSide === true || cfg.hostSide === 'true',
      dns: dnsResult,
      loopback: loopbackResult,
      testnet: testnetResult,
      timestamp: new Date().toISOString(),
    };

    if (cfg.outFile) {
      fs.mkdirSync(path.dirname(cfg.outFile), { recursive: true });
      fs.writeFileSync(cfg.outFile, JSON.stringify(summary, null, 2));
    }

    return { output: JSON.stringify(summary) };
  }
}

module.exports = CanaryEgressProvider;
