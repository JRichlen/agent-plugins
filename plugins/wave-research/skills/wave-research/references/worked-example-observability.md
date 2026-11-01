# Worked example — an observability-stack decision

Both templates are domain-agnostic; you drive them with an `args` object. This is
a **real** filled-in example: the run these patterns were distilled from. The
task was "choose an observability stack for a small ARM64 (Raspberry Pi 5)
Kubernetes cluster", and it exercised both strategies — Strategy A to research
the option space and fact-check the risky claims, Strategy B to reconcile it all
into one recommendation with a hard resource-budget gate.

Read this alongside the two templates in `../templates/`. The point is to see
what goes in `context`, `dimensions`, and `constraints` for a concrete problem —
then swap your own in.

## The frozen context (`context`)

This string is injected verbatim into *every* agent — researcher and verifier
alike — so nothing drifts off the ground truth. Keep it to confirmed facts, not
opinions:

```
CLUSTER: 4× Raspberry Pi 5 (ARM64, Cortex-A76, 8GB RAM each), k3s.
BUDGET: the observability stack must fit in ~5GiB total RAM across the cluster,
leaving the majority of cluster RAM free for workloads.
HARD REQUIREMENT: every image must have a published linux/arm64 build — no
amd64-only components, no emulation.
INGRESS: a single Tailscale Funnel endpoint is the only inbound path.
Anything that must receive external OTLP has to sit behind it.
These facts are settled. Do not re-litigate them; reason within them.
```

## Strategy A — `derived-verify` args

Use A here to map the option space and then chase down whatever risky claims the
research raised (arm64 availability, memory footprints, etc.) — targets you
cannot enumerate before the research surfaces them.

```js
{
  context: CTX,                       // the block above
  maxClaims: 18,
  dimensions: [
    { key: 'traces',
      prompt: 'Evaluate tracing backends (Tempo, Jaeger, Phoenix) for this ' +
              'cluster. For each, state the arm64 image status and steady-state ' +
              'RAM. List as riskyClaims any load-bearing factual assertion that, ' +
              'if wrong, would flip the choice.' },
    { key: 'logs',
      prompt: 'Evaluate log backends (Loki, OpenObserve, Elasticsearch). Same ' +
              'output contract: arm64 status, RAM footprint, and the riskyClaims ' +
              'that carry the conclusion.' },
    { key: 'collector',
      prompt: 'Evaluate the ingest/collector layer (otelcol-contrib vs ' +
              'alternatives) and how it fans out to the backends behind a single ' +
              'Funnel endpoint. Surface riskyClaims about arm64 and footprint.' },
  ],
}
```

What comes back is `{ research, verdicts }`. The verdicts are adversarial checks
of the harvested claims — e.g. a research claim "OpenObserve ships arm64 images"
gets chased and may come back `refuted`. Strategy A hands you that raw; *you*
decide what a refuted claim means for the choice.

## Strategy B — `pipelined-verdict-wins` args

Use B to turn the same shape of work into **one** recommendation, with the
resource budget as a hard gate the answer may not cross. Note the `constraints`
array — that's the constraint-axis-gating idea: a non-negotiable floor, not just
another dimension.

```js
{
  context: CTX,
  maxClaims: 5,
  constraints: [
    'The full stack must fit within ~5GiB total cluster RAM.',
    'Every component must have a published linux/arm64 image.',
    'External OTLP ingest must terminate behind the single Tailscale Funnel endpoint.',
  ],
  dimensions: [
    { key: 'traces',    prompt: 'Recommend a tracing backend for this cluster ...' },
    { key: 'logs',      prompt: 'Recommend a log backend for this cluster ...' },
    { key: 'collector', prompt: 'Recommend the collector/fan-out topology ...' },
  ],
}
```

What comes back is a single `{ recommendation, correctionsToPriorBrief }`. The
reconciler is bound by verdict-wins: where a per-dimension verifier refuted a
research claim, the refuted claim cannot survive into the recommendation as if
true, and it shows up under `correctionsToPriorBrief`. In the real run this is
exactly what disqualified an option whose arm64 support turned out to be
aspirational — the verdict overrode the optimistic research and the reconciler
recorded the correction instead of silently absorbing it.

## What to copy

- **`context`** = only settled facts, ~5–15 lines. This is the single highest-
  leverage field; a vague context lets every agent wander.
- **`dimensions`** = the axes that actually cut your problem. Scout these inline
  first — don't hardcode axes you haven't confirmed are the right split.
- **`constraints`** (Strategy B) = the floors the answer may not cross. If a fact
  is "we'd prefer X", it's context or a dimension; if it's "the answer is invalid
  without X", it's a constraint.
