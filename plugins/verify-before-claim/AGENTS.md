# AGENTS.md — verify-before-claim

Never assert a fact, completion, or reproduction claim without naming and running the specific check that would prove it false, first.

## How to use it

Read `skills/verify-before-claim/SKILL.md` and follow it — it is the authoritative
description of this plugin's workflow and the invariant it defends. It is an
always-on, inline discipline: the core procedure in the SKILL.md body applies
to every claim, every turn, with no invocation step. Four reference files
under `skills/verify-before-claim/references/` load only when their specific
trigger fires:

- `pre-claim-reproduction.md` — bug-report and merge/PR readiness claims
- `uncertainty-flagging.md` — claims headed into a handoff doc or deliverable
- `primary-source-research.md` — claims citing an external source
- `skill-behavior-verification.md` — claims about what a skill/tool/command does

The command `commands/verify-before-claim.md` is the entry point a user invokes
to reload the discipline explicitly mid-session.

## The invariant this plugin defends

A claim of fact, completion, or reproduction must ALWAYS be backed by the specific check that would prove it false, performed directly — and NEVER asserted as settled when that check wasn't run; residual uncertainty must ALWAYS be flagged explicitly, never smoothed into confident-sounding prose.

The deterministic checks that defend it live in `evals/cheap/checks.sh` and run
as part of the marketplace cheap tier.
