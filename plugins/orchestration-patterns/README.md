# orchestration-patterns

Two reusable multi-agent orchestration templates for **research-and-verify**
work on Claude Code's Workflow tool. Both fan out research across dimensions and
then adversarially verify the claims that research surfaces — so a
plausible-but-wrong finding gets caught instead of shipped.

They were distilled from a real run (choosing an observability stack for a small
ARM64 Kubernetes cluster) into domain-agnostic templates you drive with an `args`
object.

> **Portability:** the templates run on Claude Code's Workflow tool, but the
> research-and-verify *discipline* is harness-agnostic — on any other harness,
> re-implement it with that harness's fan-out primitive (see `AGENTS.md`).

## Install

```
/plugin marketplace add JRichlen/agent-plugins
/plugin install orchestration-patterns@jrichlen
```

## The two templates

| | derived-verify (Strategy A) | pipelined-verdict-wins (Strategy B) |
|---|---|---|
| **Role** | sensor | decider |
| **Shape** | barrier fan-out, then verify a *harvested* claim set | streaming produce→verify per dimension, then reconcile |
| **Returns** | raw `{ research, verdicts }` | one `{ recommendation, correctionsToPriorBrief }` |
| **Reach for it when** | you don't yet know what's worth checking and want to inspect verdicts yourself | you want one coherent decision, latency matters, hard constraints gate the answer |

Both share the same discipline: **one frozen ground-truth context** on every
agent, **structured output per stage**, and an **adversarial verifier that
defaults to disbelief** so unsupported claims fail closed.

## Usage

Invoke the skill — `/derived-verify` or `/pipelined-verdict-wins`, or just
describe a research-and-verify task and the `orchestration-patterns` skill will
trigger. The skill helps you scout the right `dimensions` (and `constraints` for
Strategy B), then you run a template with:

```js
Workflow({
  scriptPath: '.../templates/derived-verify.workflow.js',
  args: { context: CTX, dimensions: [ /* ... */ ], maxClaims: 18 },
})
```

See `skills/orchestration-patterns/references/worked-example-observability.md`
for a fully filled-in `args` for both strategies.

## Layout

```
skills/orchestration-patterns/
  SKILL.md                                  # shared discipline + A-vs-B decision guide
  templates/
    derived-verify.workflow.js              # Strategy A
    pipelined-verdict-wins.workflow.js      # Strategy B
  references/
    strategy-a-derived-verify.md            # annotated walkthrough
    strategy-b-pipelined-verdict-wins.md    # annotated walkthrough
    worked-example-observability.md         # real filled-in example
commands/                                   # /derived-verify, /pipelined-verdict-wins
evals/cheap/checks.sh                       # fail-closed marker + structure checks
```

## License

MIT
