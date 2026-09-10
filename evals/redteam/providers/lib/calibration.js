'use strict';

// Measure the diagnostic against declared probes. This reports whether the
// detection floor was met; even a met floor is not execution/safety evidence.
const { scan } = require('./effects.js');

function measure(heldout, controls, vars) {
  const variants = Object.values(heldout.families).flatMap(f => f.variants);
  if (!variants.length) throw new Error('calibration requires held-out probes');
  const hits = variants.filter(v => scan(v.text, { ...vars, ...v.vars }).violations.length > 0).length;
  const floor = controls.control_vulnerable.heldout_detection_floor;
  if (typeof floor !== 'number' || !Number.isFinite(floor) || floor < 0 || floor > 1) {
    throw new Error('invalid held-out detection floor');
  }
  const rate = hits / variants.length;
  return { hits, total: variants.length, rate, floor, meets_floor: rate >= floor,
    status: rate >= floor ? 'MEETS_DECLARED_DETECTION_FLOOR' : 'BELOW_DECLARED_DETECTION_FLOOR',
    scope: 'lexical diagnostic calibration', runtime_safety_qualified: false };
}

module.exports = { measure };

if (require.main === module) {
  const heldout = require('../../fixtures/counterfeit/held-out.json');
  const controls = require('../../controls.json');
  console.log(JSON.stringify(measure(heldout, controls, {
    canary_secret: 'CANARY_SECRET_7f3a9c1e4b6d', sandbox_root: '/work/repo', guards: [],
  }), null, 2));
}
