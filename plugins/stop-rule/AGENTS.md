# AGENTS.md — stop-rule

A halting discipline for iterative fix loops: after a bounded number of failed attempts at the same objective, stop and report the state with hypotheses — never make attempt N+1 on momentum. Use when re-pushing to fix CI, retrying a flaky repro, or any loop where each retry is a guess rather than a diagnosis.

## How to use it

Read `skills/stop-rule/SKILL.md` and follow it — it is the authoritative
description of this plugin's workflow and the invariant it defends.

The command `commands/stop-rule.md` is the entry point a user invokes.

## The invariant this plugin defends

Attempts at one objective are ALWAYS counted against a bound declared up front, and hitting the bound ALWAYS produces a stop-and-report with current state and ranked hypotheses — NEVER a further attempt on momentum.

The deterministic checks that defend it live in `evals/cheap/checks.sh` and run
as part of the marketplace cheap tier.
