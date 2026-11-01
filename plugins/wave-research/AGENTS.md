# AGENTS.md — wave-research

Stress-test a contested thesis with staged, adversarial research (rival hypotheses, ACH matrix, checkpoints), plus fan-out research-and-verify Workflow templates. Not for lookups.

## How to use it

Read `skills/wave-research/SKILL.md` and follow it — it is the authoritative
description of this plugin's workflow and the invariant it defends.

The command `commands/wave-research.md` is the entry point a user invokes.

## The invariant this plugin defends

A sub-claim is reported supported only when its disconfirmers were written before the search, at least one adversarial pass failed to refute it, two or more source-incentive classes agree, and at least one source is primary. Anything less is reported unverified, mixed or unknown — NEVER rounded up.

In W0 the cold critic's pre-registration (sub-claims, rivals, disconfirmers) is complete before any search-based W0 work starts; the other W0 roles then run in parallel.

## The fan-out discipline it also carries

`skills/wave-research/references/fan-out-discipline.md` holds the three rules
for any fan-out of research workers: one frozen ground-truth context injected
into every agent, a schema'd output per stage, and an adversarial verifier that
defaults to disbelief. `skills/wave-research/templates/` holds the two Claude
Code Workflow scripts that implement them for a one-pass research-and-verify
run (`derived-verify`, a sensor; `pipelined-verdict-wins`, a decider where a
refuting verdict wins). The templates carry load-bearing marker comments
(`FROZEN-CONTEXT`, `ADVERSARIAL-REFUTE-DEFAULT`, `UNTRUSTED-PROVENANCE`,
`DERIVED-TARGETS`, `VERDICT-WINS`) that the cheap checks pin; do not remove one
quietly. A template run alone does not meet the invariant above.

The deterministic checks that defend it live in `evals/cheap/checks.sh` and run
as part of the marketplace cheap tier.
