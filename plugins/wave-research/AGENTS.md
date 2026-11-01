# AGENTS.md — wave-research

Stress-test a contested thesis with staged, adversarial research (rival hypotheses, ACH matrix, checkpoints) before believing it. Not for lookups.

## How to use it

Read `skills/wave-research/SKILL.md` and follow it — it is the authoritative
description of this plugin's workflow and the invariant it defends.

The command `commands/wave-research.md` is the entry point a user invokes.

## The invariant this plugin defends

A sub-claim is reported supported only when its disconfirmers were written before the search, at least one adversarial pass failed to refute it, two or more source-incentive classes agree, and at least one source is primary. Anything less is reported unverified, mixed or unknown — NEVER rounded up.

In W0 the cold critic's pre-registration (sub-claims, rivals, disconfirmers) is complete before any search-based W0 work starts; the other W0 roles then run in parallel.

The deterministic checks that defend it live in `evals/cheap/checks.sh` and run
as part of the marketplace cheap tier.
