export const meta = {
  name: 'derived-verify',
  description:
    'Fan out research over a fixed set of dimensions, then adversarially ' +
    'verify the claims HARVESTED from that research. Verification targets are ' +
    'DERIVED from the fan-out output, never hardcoded — you cannot know what ' +
    'is risky until the research surfaces it.',
  // Same titles appear in phase() below so progress groups line up.
  phases: [
    { title: 'Research', detail: 'parallel agent per research dimension' },
    { title: 'Verify', detail: 'adversarial skeptic per harvested risky claim' },
  ],
}

// ---------------------------------------------------------------------------
// Strategy A — batched fan-out -> derived-target adversarial verify.
//
// Shape (domain-agnostic; drive it with `args`):
//   args = {
//     context:    string,               // FROZEN ground-truth, injected into EVERY agent
//     dimensions: [{ key, prompt }],    // the fixed research axes to fan out over
//     maxClaims?: number,               // cap on harvested claims to verify (default 24)
//   }
//
// The defining property is the HARVEST step: phase 2's targets come out of
// phase 1's structured output, so the skeptics chase exactly the claims the
// research raised — not a list the author guessed in advance. Returns the raw
// { research, verdicts } with no synthesis; a caller decides what to do with a
// refuted claim. (For inline verify + verdict-wins reconciliation instead, use
// the pipelined-verdict-wins template.)
//
// See references/worked-example-observability.md for a filled-in `args`.
// ---------------------------------------------------------------------------

// FROZEN-CONTEXT: one ground-truth string, injected into every single agent so
// no agent reasons from unanchored assumptions. This is invariant across both
// templates in this skill.
const CTX = (args && args.context) || ''
const DIMENSIONS = (args && args.dimensions) || []
const MAX_CLAIMS = (args && args.maxClaims) || 24

// Per-stage structured output — each agent is forced to return validated JSON,
// so the harvest step downstream can rely on the shape instead of parsing prose.
const RESEARCH_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['summary', 'riskyClaims'],
  properties: {
    summary: { type: 'string', description: 'what this dimension concluded' },
    riskyClaims: {
      type: 'array',
      description: 'load-bearing claims that, if wrong, would break the conclusion',
      items: { type: 'string' },
    },
  },
}

const VERIFY_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['claim', 'verdict', 'evidence'],
  properties: {
    claim: { type: 'string' },
    verdict: {
      type: 'string',
      enum: ['confirmed', 'refuted', 'partially-true', 'unverifiable'],
    },
    evidence: { type: 'string' },
  },
}

phase('Research')
// Barrier: we need the FULL research set before we can harvest claims from it.
const research = (await parallel(
  DIMENSIONS.map((d) => () =>
    agent(`${CTX}\n\n${d.prompt}`, {
      label: `research:${d.key}`,
      phase: 'Research',
      schema: RESEARCH_SCHEMA,
    })
  )
)).filter(Boolean)

// DERIVED-TARGETS: harvest the claims to verify straight out of the fan-out
// output. This is what makes it Strategy A — the verify set is a function of
// the research, not a constant.
const claims = research
  .flatMap((r) => r.riskyClaims || [])
  .slice(0, MAX_CLAIMS)

log(`harvested ${claims.length} risky claims from ${research.length} dimensions`)

phase('Verify')
const verdicts = (await parallel(
  claims.map((c) => () =>
    // ADVERSARIAL-REFUTE-DEFAULT: the skeptic is told to default to REFUTED so
    // an unsupported claim fails closed rather than getting a free pass.
    agent(
      `${CTX}\n\nAdversarially fact-check the claim below. Default to ` +
        `verdict "refuted" unless the evidence clearly supports it.\n\nCLAIM: ${c}`,
      {
        label: 'verify',
        phase: 'Verify',
        agentType: 'general-purpose',
        schema: VERIFY_SCHEMA,
      }
    )
  )
)).filter(Boolean)

return { research, verdicts }
