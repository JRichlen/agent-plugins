# AGENTS.md — context-handoff

Walk the ordered continue, clear, handoff, delegate, compact decision tree at a phase boundary, and keep any handoff artifact pointer-only — settled specs, plans, ADRs, issues, commits, and diffs referenced by path or URL, never copied inline. Use this when the context window is getting full, you're wondering whether to clear or compact, you need to hand off to another harness, directory, or colleague, you've hit a phase boundary and aren't sure whether to keep going or start fresh, or you want to cache hard-won research before it's lost.

## How to use it

Read `skills/context-handoff/SKILL.md` and follow it — it is the authoritative
description of this plugin's workflow and the invariant it defends. The
decision tree itself lives inline there; two reference files load only on
their own trigger: `skills/context-handoff/references/portable-extraction.md`
(loads on the HANDOFF branch) and
`skills/context-handoff/references/research-documenter.md` (loads on the
independent hard-to-reach-research trigger).

The command `commands/context-handoff.md` is the entry point a user invokes.

The pointer-only rule from the HANDOFF branch has a deterministic checker at
`scripts/check-handoff-portability.py` — run it against a candidate handoff
file before sending it.

PORTABILITY: this plugin's DELEGATE branch names Claude Code's Task tool /
Workflow tool as the concrete fan-out primitive it's talking about. The
discipline is harness-agnostic; on another harness, delegation just means
whatever that harness's own unattended-fan-out primitive is.

## The invariant this plugin defends

At every phase boundary, the continue / clear / handoff / delegate / compact choice must ALWAYS be reached by walking the one ordered decision tree top-to-bottom — continue, then clear, then handoff, then delegate, then compact, first match wins — never guessed ad hoc, never invoked mid-phase (mid-phase there is nothing to decide: continue, or split remaining work into a subagent), and never jumped to out of order. Anything that crosses a handoff boundary (specs, plans, ADRs, issues, commits, diffs) must ALWAYS be referenced by path or URL, NEVER copied or quoted inline into the handoff artifact, so the receiving session reads the live source instead of a copy that can drift from it.

The deterministic checks that defend it live in `evals/cheap/checks.sh` and run
as part of the marketplace cheap tier.
