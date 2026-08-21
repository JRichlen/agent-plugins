---
name: orchestrate
description: >-
  Two reusable multi-agent orchestration templates for research-and-verify work
  built on Claude Code's Workflow tool: fan out research over dimensions, then
  adversarially verify the claims that research surfaces. Use this WHENEVER you
  are about to hand-roll a fan-out of subagents for research, exploration,
  design comparison, auditing, or "go find out X and check it" — especially any
  time you catch yourself writing a parallel()/pipeline() of research agents and
  wondering how to keep them honest. It captures the frozen-ground-truth,
  per-stage-schema, adversarial-verifier discipline so plausible-but-wrong
  findings don't survive. Reach for it on phrases like "research and verify",
  "fan out agents", "explore this thoroughly", "compare these options and
  fact-check", "audit and confirm", or "orchestrate subagents".
license: MIT
compatibility: >-
  The templates target Claude Code's Workflow tool (agent()/parallel()/pipeline()).
  The DISCIPLINE (frozen context, per-stage schemas, adversarial verify,
  verdict-wins reconciliation) is harness-agnostic and can be re-expressed in any
  orchestration layer.
---

# Orchestration patterns: research that fact-checks itself

When you fan out subagents to research something, the danger isn't too little
output — it's confident, plausible, **wrong** output that reads as authoritative
because a fleet of agents produced it. These two templates exist to make a
fan-out fact-check itself, so what survives to your synthesis is the part that
withstood an adversary.

Both templates are in `templates/`. Both are domain-agnostic — you drive them
with `args`, not by editing the script. Fill in a worked example by reading
`references/worked-example-observability.md`.

## The shared discipline (why these work)

Three invariants hold across **both** templates. They are the reusable idea; the
two shapes below are just two ways to spend them.

1. **Frozen ground-truth context, injected into every agent.** One `context`
   string carries the facts you already trust (hard constraints, confirmed
   environment, known-good values). Every agent — researcher and verifier alike
   — receives it verbatim, so no agent reasons from unanchored assumptions and
   they don't contradict each other on settled facts. In the templates this is
   `CTX`, marked `FROZEN-CONTEXT`.

2. **Per-stage structured output.** Every stage forces a JSON `schema`, so the
   next stage consumes a validated shape instead of parsing prose. This is what
   makes the *harvest* step possible — you can only pull "risky claims" out of a
   research result if the result is guaranteed to have a `riskyClaims` field.

3. **An adversarial verifier that defaults to disbelief.** Verifiers are told to
   return `refuted` unless the evidence clearly supports the claim. Disbelief is
   the default so an unsupported claim fails closed. In the templates this is
   marked `ADVERSARIAL-REFUTE-DEFAULT`. Prefer a distinct `agentType` (e.g.
   `general-purpose`) or a different lens per verifier so the check isn't just
   the researcher agreeing with itself.

## Which template?

Pick by **when verification binds to research** and **what you want back**.

### Strategy A — `derived-verify` (batched, targets derived from the fan-out)

`templates/derived-verify.workflow.js`

Research **all** dimensions first (a barrier), then **harvest** the risky claims
out of the combined structured output and fan skeptics at exactly that set. The
verify targets are a *function of the research*, not a list you guessed up front
— that's the defining move (`DERIVED-TARGETS`). Returns raw
`{ research, verdicts }` and stops; the caller decides what a refuted claim
means.

Use it when:
- You don't know what's worth checking until the research surfaces it.
- You want the raw research + verdicts to inspect or feed elsewhere.
- A global view of all claims matters (e.g. dedup across dimensions before
  verifying, or cap the total number of checks).

### Strategy B — `pipelined-verdict-wins` (streamed, one reconciled answer)

`templates/pipelined-verdict-wins.workflow.js`

Each dimension flows through produce → verify with **no barrier** (`pipeline()`),
so dimension B is still researching while dimension A's claims are already being
checked. A single reconciler then merges everything under an explicit
**verdict-wins** precedence: *where a verifier refuted or corrected a research
claim, the verdict supersedes the claim* — the refuted claim must not survive
into the recommendation as if true. It also emits `correctionsToPriorBrief`, a
self-diff of what got overturned.

Use it when:
- You want **one coherent recommendation** out the back, not raw data.
- Latency matters — no dimension waits for the slowest sibling to start
  verifying.
- You have **hard constraints** that gate the answer (pass them as
  `constraints`); the reconciler treats them as a floor the recommendation may
  not cross.

### Rule of thumb

| You want… | Use |
|---|---|
| Raw research + verdicts, verify-set discovered from the research | **A** `derived-verify` |
| One reconciled recommendation, refuted claims can't survive | **B** `pipelined-verdict-wins` |
| Lowest wall-clock (verify overlaps research) | **B** (no barrier) |
| A global pass over all claims before verifying (dedup/cap) | **A** (barrier) |

## Running a template

These are Workflow scripts. Invoke with the `Workflow` tool, passing your filled
`args` as the `args` input (see the worked example for a complete object):

```
Workflow({ scriptPath: "<...>/templates/derived-verify.workflow.js",
           args: { context: "...", dimensions: [ ... ] } })
```

Start by scouting inline to build the `dimensions` list (what axes actually
matter for this question), then hand the list to the template — don't hardcode
dimensions you haven't confirmed are the right cut of the problem.

## Extending the pattern

The reusable ideas generalize past these two scripts. Common moves:

- **Perspective-diverse verify:** give each verifier a distinct lens
  (correctness / security / does-it-reproduce) instead of N identical skeptics —
  diversity catches failure modes redundancy can't.
- **Constraint-axis gating:** encode a non-negotiable floor as a `constraint`
  the synthesis may not cross (in the observability example, an "all nodes must
  clear this CPU floor" axis disqualified options wholesale).
- **"Superseded by" discipline:** when re-running against a prior brief, make the
  reconciler diff against it (`correctionsToPriorBrief`) so corrections are
  explicit, not silently absorbed.

See `references/strategy-a-derived-verify.md` and
`references/strategy-b-pipelined-verdict-wins.md` for annotated walkthroughs of
each template, and `references/worked-example-observability.md` for the real run
these were distilled from.
