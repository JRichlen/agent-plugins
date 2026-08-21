# grill-me

Interview the user about a plan before work starts, single-session and no
subagents required, walking its design tree and scaling question depth to
each branch's stakes (reversibility x blast radius) while offering a
recommendation at almost every step. Use on phrases like grill me, interview
me about this plan, stress-test this plan, or before starting a nontrivial
multi-step change whose design isn't yet settled.

## Install

```
/plugin marketplace add JRichlen/agent-plugins
/plugin install grill-me@jrichlen
```

PORTABILITY: harness-agnostic. grill-me is a plain conversation with the
user — no subagents, hooks, or Workflow tool required on any harness. (The
Differentiation section below names those primitives only to describe two
*other* plugins, not a dependency of this one.)

## How it works

Full procedure lives in `skills/grill-me/SKILL.md` (kept lean, always
resident). In short: model the plan as a design tree, walk it in numbered
rounds over the current "frontier" of decisions whose prerequisites are
already settled, and triage every branch on two axes — reversibility (two-way
door vs. one-way door) and blast radius (internal/dev-only vs.
user-facing/production/cross-team/financial/compliance) — before deciding how
hard to press on it. LIGHT branches get one confirm-or-skip question; STANDARD
branches get their natural 1-3 questions; DEEP branches (irreversible *and*
wide blast radius) get the full sub-tree, a devil's-advocate pass, and a
required explicit confirm. Every question, at every tier, ships with a stated
recommendation the user can accept with a bare "yes." The session ends with a
synthesized recap (Confirmed Decisions / Open Risks Accepted As-Is /
Deferred-for-Later) and a request to confirm shared understanding before the
plan is treated as ready to execute.

Deeper technique detail (devil's-advocate craft, pre-mortem prompts, worked
triage examples, fact-finding rules) lives in `skills/grill-me/references/`
and loads only when a session actually needs it — that's the token-efficiency
half of the design, not a missing feature.

## Differentiation — why this isn't second-opinion or orchestrate

Two other plugins in this marketplace sit near this one. Neither does what
grill-me does:

- **second-opinion** (`plugins/voice/skills/second-opinion`) is *post-hoc,
  offer-only, subagent-required* fact-checking of a verdict or recommendation
  that **already exists** — it batches fact-checks against sources, adds
  scoped advisor personas, and re-emits the response as
  Verified/Flagged/Conflict with a mandatory delta. It never runs unbidden.
- **orchestrate** (`plugins/orchestration-patterns`, mid-rename from
  `orchestration-patterns` — same plugin, in-flight name) is a **Workflow-tool
  template** for fanning research out across multiple subagents and
  adversarially verifying the claims that research surfaces.

grill-me is neither of those. It is a **single-session, no-subagents-required,
live conversational interrogation of a plan**, conducted directly with the
user *before any work starts*, to reach shared understanding — not to
validate a finished answer, and not to fan research out across workers.

## Design departures from the original grill-me

This skill is a deliberate rewrite of the technique, not a port. Three
departures, by design:

1. **Dynamic, not fixed-depth.** The canonical version exhausts every branch
   of the design tree uniformly. This version spends question budget in
   proportion to how expensive a branch would be to get wrong (reversibility x
   blast radius), so a naming choice gets one line and a public-API or
   security decision gets a full devil's-advocate pass.
2. **Token-efficient, not monolithic.** SKILL.md carries only the invariant,
   the triage table, and the round loop — the material every session needs.
   Devil's-advocate technique, fact-finding mechanics, and worked triage
   examples live in `references/` and load only for the sessions that actually
   need them (DEEP branches, contested calls, mid-round lookups, ambiguous
   triage).
3. **Assistive, not pure interrogation.** Every question ships with a stated
   recommendation from round one — not as a later speed retrofit. DEEP
   branches additionally get a short tradeoff comparison before the
   recommendation, so the offered answer reads as an audited conclusion
   rather than an assertion.

## Attribution

The interview technique — walking a design tree in rounds, offering a
recommendation, reaching shared understanding before work starts — is adapted
from **Matt Pocock's** `grill-me` / `grilling` skills, MIT-licensed at
[github.com/mattpocock/skills](https://github.com/mattpocock/skills)
(see specifically
[`skills/productivity/grill-me/SKILL.md`](https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md)),
and his writeup at
[aihero.dev/my-grill-me-skill-has-gone-viral](https://aihero.dev/my-grill-me-skill-has-gone-viral).
His technique in one line: "Interview me relentlessly about every aspect of
this plan until we reach a shared understanding. Walk down each branch of the
design tree resolving dependencies between decisions one by one."

This SKILL.md does not copy his prose — the frontier/round mechanic, the
stakes-tiered depth model, and the progressive-disclosure file layout are
written in this repo's own words, and the dynamic/token-efficient/assistive
departures above are a deliberate redesign, not an accident to fix. Per the
MIT license's notice-retention term, no substantial portion of his text is
reproduced here; this note is the credit that term calls for.

## Status

Implemented. The cheap eval (`evals/cheap/checks.sh`) defends the invariant
mechanically: the two-axis stakes table, the `❓`/`➡️` question-and-recommendation
format, the "Not this" differentiation naming both adjacent plugins, and a
line-count budget on SKILL.md so the lean-file design can't silently regress.

## License

MIT
