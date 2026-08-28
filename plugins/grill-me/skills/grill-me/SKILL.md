---
name: grill-me
description: >-
  Interview the user about a plan before work starts, single-session and no subagents required, walking its design tree and scaling question depth to each branch's stakes (reversibility x blast radius) while offering a recommendation at almost every step. Use on phrases like grill me, interview me about this plan, stress-test this plan, or before starting a nontrivial multi-step change whose design isn't yet settled.
license: MIT
compatibility: >-
  PORTABILITY: harness-agnostic. Pure conversational prose — no subagents, no
  Workflow tool, no hooks, no harness-specific primitive required at all — so
  it ports to any harness that can hold a multi-turn conversation with the
  user. The "Not this" section below names subagents and the Workflow tool
  only to describe two OTHER plugins, not a dependency of this one. Interview
  technique adapted from Matt Pocock's MIT-licensed grill-me/grilling skills
  (github.com/mattpocock/skills); see README.md for the attribution note and
  the departures this version makes.
---

# grill-me

## Invariant

ALWAYS size a branch's interrogation depth to its stakes tier (reversibility x
blast-radius, computed per branch, not once for the whole session) and ALWAYS
attach a stated recommendation to every question asked, so the user can
accept-in-one-word or push back — NEVER run a fixed-depth/fixed-count question
script regardless of stakes, and NEVER emit a bare question with no answer for
the user to react to.

## Not this

- **second-opinion** (`plugins/voice/skills/second-opinion`) is *post-hoc*:
  batched fact-checks plus advisor personas re-checking a verdict that
  already exists.
- **orchestrate** (`plugins/orchestration-patterns`) is a Workflow-tool
  template fanning research across subagents.

grill-me is neither: a **single-session, no-subagents-required, live
conversational interrogation of a plan**, run with the user *before* work
starts — shared understanding, not validation or fan-out.

## When to use this

Trigger on "grill me", "interview me about this plan", "stress-test this
plan", or before a nontrivial multi-step change whose design isn't settled.
A plan that triages LIGHT end to end gets a brief "no session needed."

## Anchor, then consent to each path

No branch questioning before the **anchor** is set: the goal, the outcome
that counts as success, and what is out of scope — inferred from the plan
text and confirmed in one exchange, never a series. Then, before
descending into any STANDARD or DEEP branch, present a **path-consent
header** — the branch, its tier, roughly how many questions it costs, and
a one-line recommendation for the whole path — and let the user route:
**explore / accept / defer / out-of-scope**. Only "explore" spends
questions; headers are batched into one routing round, ordered by
leverage. Full mechanic, header format, and the irreversibility
exception: [`references/path-consent.md`](references/path-consent.md).

## The frontier/round loop

Model the plan as a design tree; the **frontier** is every decision whose
prerequisites are settled.

1. Compute the current frontier. Ask it as one numbered round — `Q1`, `Q2`,
   ... A question whose answer depends on another still-open question in the
   same round is deferred to a later round.
2. Wait for the user's answers to the whole round.
3. Each answer resolves nodes and may reveal new sub-decisions — push the
   frontier outward, recompute, ask the next round.
4. Repeat until the frontier is empty (see Termination).

## Stakes triage — the real departure from fixed-depth

Before adding a node's sub-questions to the tree, triage it on two axes, then
gate depth and pushback by the resulting tier:

| | Small blast radius (internal / dev-only) | Wide blast radius (user-facing, prod, cross-team, financial, compliance) |
|---|---|---|
| **Two-way door** (cheaply undone: renamed, refactored, flagged, rolled back) | LIGHT | STANDARD |
| **One-way door** (locks in data shape, public API, security posture, cost, irreversible deletion) | STANDARD | DEEP |

- **LIGHT** — one confirm-or-skip question with a stated default; no
  objection means assume the recommendation. No devil's-advocate pass.
- **STANDARD** — ask the branch's natural frontier questions (typically 1-3),
  each with a recommendation. No forced pushback unless the answer is
  internally inconsistent with an earlier one.
- **DEEP** — fully decompose the branch's sub-tree, run a devil's-advocate
  pass on the first answer (`references/technique.md`), and require an
  explicit confirm — silence never counts as acceptance here.

Two signals shift tier: **novelty** (no established pattern for this
codebase pushes a branch up one tier — there's no fallback if it's wrong)
and **how settled the user sounds** (a firm, reasoned choice in the plan
text collapses that branch to one confirm-or-skip regardless of tier —
don't re-litigate settled ground). Re-triage mid-session reopens *that one
branch* at its new tier, never the whole session. Ambiguous calls:
`references/stakes-examples.md`.

## Question format — assistive by default

Every question, every tier, in this shape:

```
❓ Qn — <title>: <body>
➡️ <recommended answer, one line>
```

DEEP-tier branches get a 2-3 option tradeoff comparison *before* the
recommendation line — one line per option (option, chief upside, chief risk)
— so the recommendation reads as an audited conclusion, not an assertion.

A bare "yes" / "go with that" accepts the recommendation and moves the
round forward. Devil's-advocate pushback is reserved for a DEEP branch's
first answer or an answer contradicting the user's stated goals or an
earlier answer — never applied reflexively.

## Mid-round fact lookups

A question turning on a fact you don't have (file content, a library's real
API, a repo convention): see `references/fact-finding.md` — direct tools
first. Only questions downstream of that fact wait; the round proceeds.

## Termination

The session ends when the frontier is empty — every branch visited, nothing
silently assumed at STANDARD/DEEP tiers. Produce a synthesized recap:

```
**Confirmed Decisions**
...

**Open Risks Accepted As-Is**
...

**Deferred-for-Later**
...
```

Then ask the user to confirm shared understanding. Do not treat the plan as
ready to execute until that confirmation lands.
