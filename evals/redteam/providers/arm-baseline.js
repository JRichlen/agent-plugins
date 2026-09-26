// providers/arm-baseline.js — a trivial named subclass of TextualTargetProvider
// (design §7.3/§7.4). The ONLY reason this file exists separately from
// target-textual.js: promptfoo's provider factory sets
// `providerId = providerOptions.id ?? providerPath` (providers-DKidnSQu.js:22756),
// and a generated config's `id: file://.../arm-baseline.js` therefore gives
// this arm a distinct provider id merely by pointing at a distinct file --
// no behavioral difference lives here (it is a real `class` per T43's
// ClassExportRequired convention, not just a re-exported reference, so it
// satisfies the SAME source-level shape check every other provider in this
// directory does). What actually differs between arms (guidance injected or
// not) is driven entirely by each arm's own `config.skillPath`, set
// per-plugin by bin/generate.py and read at request time by
// providers/lib/transcript.js inside target-textual.js.
'use strict';

const TextualTargetProvider = require('./target-textual.js');

class ArmBaselineProvider extends TextualTargetProvider {}

module.exports = ArmBaselineProvider;
