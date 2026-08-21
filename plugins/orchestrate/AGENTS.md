# AGENTS.md — Orchestration patterns

This plugin packages **two reusable multi-agent orchestration templates for
research-and-verify work**: fan out research across dimensions, then
adversarially verify the claims that research surfaces, so plausible-but-wrong
findings don't survive into the output.

The two templates are workflow scripts for **Claude Code's Workflow tool**
specifically — the fan-out primitives (`parallel`, `pipeline`, `agent`) are
Claude-Code features. The *discipline* they encode, though, is harness-agnostic:
freeze one ground-truth context, force structured output per stage, and make the
verifier default to disbelief. If you're on another harness, read the skill and
references for the pattern and re-implement it with that harness's fan-out
primitives.

## When to use this

You're about to hand-roll a fan-out of subagents to research something and check
it: comparing options, exploring a design space, auditing, or any "go find out X
and confirm it" task. The moment you catch yourself writing a `parallel()` or
`pipeline()` of research agents and wondering how to keep them honest, reach for
this instead of reinventing it.

Two shapes, picked by what you want out the back:

- **derived-verify (Strategy A)** — a *sensor*. Barrier fan-out over dimensions,
  then skeptics pointed at exactly the risky claims the research harvested.
  Returns raw `{ research, verdicts }`; you decide what a refuted claim means.
- **pipelined-verdict-wins (Strategy B)** — a *decider*. Each dimension streams
  produce → verify with no barrier, then one reconciler folds it into a single
  recommendation where refuting verdicts win, under a hard-constraint gate.

## How to run it

**Read `skills/orchestrate/SKILL.md` and follow it.** It is the
authoritative description: the shared discipline, an A-vs-B decision guide, how to
scout `dimensions` inline first, and how to invoke a template with
`Workflow({ scriptPath, args })`.

The two templates it drives:

- `skills/orchestrate/templates/derived-verify.workflow.js` — Strategy A.
- `skills/orchestrate/templates/pipelined-verdict-wins.workflow.js` — Strategy B.

Annotated walkthroughs and a filled-in example live under
`skills/orchestrate/references/`.

## The discipline these templates defend

Three invariants, marked as load-bearing comments in the templates and checked by
the cheap eval:

1. **Frozen ground-truth context** (`FROZEN-CONTEXT`) — one settled-facts string
   injected into *every* agent, so a verifier never "refutes" a claim by
   disagreeing about the environment.
2. **Per-stage structured output** — each stage returns a schema'd object, which
   is what makes deriving the verify set from the research output reliable.
3. **Adversarial verifier that defaults to disbelief** (`ADVERSARIAL-REFUTE-DEFAULT`)
   — an unsupported claim fails closed rather than getting a free pass.

Strategy A adds `DERIVED-TARGETS` (verify set harvested from the fan-out);
Strategy B adds `VERDICT-WINS` (a refuting verdict overrides the research claim).
Don't quietly remove these — that's exactly the regression the cheap tier exists
to catch.

## Requirements

- Claude Code (for the Workflow tool the templates run on). The pattern itself
  ports to any harness with a subagent fan-out primitive.
