// fixtures/counterfeit/plain-object-provider.js — T43 negative control
// (design §3.2, "correction to a prior document"). promptfoo's provider
// factory invokes the module's export with `new` (providers-DKidnSQu.js:
// 22754-22763). A plain object export has the right KEYS (callApi, id) but
// is not a constructor and throws at load time. A shape-only assertion
// ("does it export callApi and id") would pass this file; only letting
// promptfoo actually load it (test_redteam_provider.py's
// ProviderApiConformance__negative) catches the difference.
'use strict';

module.exports = {
  id: () => 'plain-object',
  callApi: async (prompt) => ({ output: `echo: ${prompt}` }),
};
