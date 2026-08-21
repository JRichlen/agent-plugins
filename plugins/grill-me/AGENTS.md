# AGENTS.md — grill-me

Interview the user about a plan before work starts, single-session and no subagents required, walking its design tree and scaling question depth to each branch's stakes (reversibility x blast radius) while offering a recommendation at almost every step. Use on phrases like grill me, interview me about this plan, stress-test this plan, or before starting a nontrivial multi-step change whose design isn't yet settled.

PORTABILITY: harness-agnostic. This is a plain conversation with the user —
no subagents, hooks, or Workflow tool needed on any harness.

## How to use it

Read `skills/grill-me/SKILL.md` and follow it — it is the authoritative
description of this plugin's workflow and the invariant it defends.

The command `commands/grill-me.md` is the entry point a user invokes.

## The invariant this plugin defends

ALWAYS size a branch's interrogation depth to its stakes tier (reversibility x blast-radius, computed per branch, not once for the whole session) and ALWAYS attach a stated recommendation to every question asked, so the user can accept-in-one-word or push back — NEVER run a fixed-depth/fixed-count question script regardless of stakes, and NEVER emit a bare question with no answer for the user to react to.

The deterministic checks that defend it live in `evals/cheap/checks.sh` and run
as part of the marketplace cheap tier.
