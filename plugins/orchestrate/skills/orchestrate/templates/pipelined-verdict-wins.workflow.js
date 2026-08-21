export const meta = {
  name: 'pipelined-verdict-wins',
  description:
    'Pipeline each research dimension straight into its own adversarial ' +
    'verification (no barrier between them), then reconcile everything with a ' +
    'VERDICT-WINS rule: where a verifier refuted a research claim, the verdict ' +
    'supersedes the claim in the final synthesis.',
  phases: [
    { title: 'Produce', detail: 'research one dimension' },
    { title: 'Verify', detail: 'inline adversarial check of that dimension\'s claims' },
    { title: 'Synthesize', detail: 'single reconciler, verdict-wins precedence' },
  ],
}

// ---------------------------------------------------------------------------
// Strategy B — pipelined per-dimension inline verify -> verdict-wins synthesis.
//
// Shape (domain-agnostic; drive it with `args`):
//   args = {
//     context:      string,             // FROZEN ground-truth, injected into EVERY agent
//     dimensions:   [{ key, prompt }],  // research axes; each self-verifies inline
//     constraints?: [string],           // hard gates the synthesis must not violate
//     maxClaims?:   number,             // per-dimension cap on inline verifications (default 6)
//   }
//
// Difference from Strategy A: there is NO barrier between research and verify.
// pipeline() streams each dimension through produce -> verify independently, so
// dimension B is still researching while dimension A's claims are already being
// checked. A single reconciler then applies verdict-wins precedence and records
// what it had to correct. Use this when you want one coherent recommendation
// out the back; use derived-verify when you want the raw research+verdicts.
//
// See references/worked-example-observability.md for a filled-in `args`.
// ---------------------------------------------------------------------------

// FROZEN-CONTEXT: identical discipline to derived-verify — every agent gets the
// same ground-truth string so nothing reasons from unanchored assumptions.
const CTX = (args && args.context) || ''
const DIMENSIONS = (args && args.dimensions) || []
const CONSTRAINTS = (args && args.constraints) || []
const MAX_CLAIMS = (args && args.maxClaims) || 6

const FINDINGS_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['summary', 'riskyClaims'],
  properties: {
    summary: { type: 'string' },
    riskyClaims: { type: 'array', items: { type: 'string' } },
  },
}

const VERDICT_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['claim', 'verdict', 'correction'],
  properties: {
    claim: { type: 'string' },
    verdict: {
      type: 'string',
      enum: ['confirmed', 'refuted', 'partially-true', 'unverifiable'],
    },
    correction: {
      type: 'string',
      description: 'if refuted/partially-true, the corrected statement; else ""',
    },
  },
}

const SYNTH_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['recommendation', 'correctionsToPriorBrief'],
  properties: {
    recommendation: { type: 'string' },
    correctionsToPriorBrief: {
      type: 'array',
      description: 'claims a verdict overturned — the self-diff against the research',
      items: { type: 'string' },
    },
  },
}

// pipeline(): produce -> verify with NO barrier. Each dimension flows through
// both stages on its own; the verify stage receives (findings, dimension).
const perDimension = (await pipeline(
  DIMENSIONS,
  (d) =>
    agent(`${CTX}\n\n${d.prompt}`, {
      label: `produce:${d.key}`,
      phase: 'Produce',
      schema: FINDINGS_SCHEMA,
    }),
  (findings, d) =>
    parallel(
      ((findings && findings.riskyClaims) || [])
        .slice(0, MAX_CLAIMS)
        .map((c) => () =>
          // ADVERSARIAL-REFUTE-DEFAULT: same fail-closed skeptic as Strategy A.
          agent(
            `${CTX}\n\nAdversarially verify the claim below. Default to ` +
              `verdict "refuted" unless it is clearly supported.\n\nCLAIM: ${c}`,
            { label: `verify:${d.key}`, phase: 'Verify', schema: VERDICT_SCHEMA }
          ).then((v) => ({ ...v, claim: c }))
        )
    ).then((verdicts) => ({
      dimension: d.key,
      findings,
      verdicts: verdicts.filter(Boolean),
    }))
)).filter(Boolean)

phase('Synthesize')
// VERDICT-WINS: the reconciler is told, explicitly, that where a verdict
// refuted or corrected a research claim the VERDICT WINS — the refuted claim
// must not survive into the recommendation as if it were true. Any hard
// constraints act as a gate the recommendation may not cross.
const constraintBlock = CONSTRAINTS.length
  ? `\n\nHARD CONSTRAINTS (the recommendation must not violate any):\n- ${CONSTRAINTS.join('\n- ')}`
  : ''

const synthesis = await agent(
  `${CTX}\n\nReconcile the researched-and-verified dimensions below into one ` +
    `recommendation.\n\nPRECEDENCE: where a verdict refuted or corrected a ` +
    `research claim, the VERDICT WINS — the refuted claim must not survive ` +
    `into the recommendation as if true. List every such overturned claim ` +
    `under "correctionsToPriorBrief".${constraintBlock}\n\n` +
    JSON.stringify(perDimension),
  { label: 'synthesize', phase: 'Synthesize', schema: SYNTH_SCHEMA }
)

return synthesis
