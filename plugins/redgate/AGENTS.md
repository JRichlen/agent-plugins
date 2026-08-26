# AGENTS.md — redgate

Run any idea through Red Gate: rounds of BEGIN/MIDDLE/END with graduated autonomy — each round gate is classified PATCH/MINOR/MAJOR via semver-gate, so derived work auto-passes inside a human-approved plan envelope while orientation decisions, plan approval, and irreversible actions always block on the human. BEGIN emits a verifier proven able to fail; END is that pinned verifier run by a party that did not do the work.

## How to use it

Read `skills/redgate/SKILL.md` (the round driver) and
`skills/criteria-contract/SKILL.md` (the BEGIN stage) and follow them — they
are the authoritative description of this plugin's workflow and the invariant
it defends. The generator `skills/criteria-contract/scripts/scaffold-run.sh`
creates and pins runs under `.redgate/<slug>/`; the emitted `check.sh` is the
verifier. The command `commands/redgate.md` is the entry point a user invokes.

## Cross-harness operation

This file is the complete operating doc for harnesses that read `AGENTS.md`
natively (Codex, and Copilot via `apm compile -t copilot`, which aggregates
installed APM dependencies into the generated .github/copilot-instructions.md file). Everything
load-bearing is prose plus plain bash — no Claude-Code primitive is required:

- **BEGIN / red gate / pin**: run `scaffold-run.sh`, write criteria, run
  `check.sh` (exit 1 = red = dispatchable; exit 99 = harness failure, never
  red; a check_cmd exiting non-zero — 127 included — is a legitimate FAIL),
  ratify, `scaffold-run.sh --pin <slug>`.
- **END independence** without subagents (subagents are a Claude-Code
  convenience, not a dependency — the pattern ports to any harness): run
  `check.sh` in a fresh session,
  or hand the human the verdict table — the requirement is that the party
  who did the work never grades it; the mechanism adapts per harness.
- **Round gates are classified, not defaulted to the human**: PATCH (strictly
  derived from an approved plan slice, verifier green, no escalator)
  auto-passes and appends to `gates.log`; MINOR auto-passes with a prominent
  flag and standing veto; MAJOR — orientation decisions, plan approval, first
  ratification, UNVERIFIABLE countersignatures, fence/budget changes,
  anything irreversible — always stops for a structured human question.
- Full protocol: `docs/red-gate-protocol.md` at the marketplace root.

## Status: slices 1–2 of 5

Ships the driver, BEGIN (criteria-contract), and END (reconcile) — the full
round loop: command → skills → generator → red gate → independent verify with
drift, evidence, and mutation control. An optional Claude-Code hooks enforcement layer (hooks are
CC-specific; on any other harness the same rules hold as prose discipline), and the protocol references
land as later slices per `docs/red-gate-implementation-plan.md`.

## The invariant this plugin defends

No MIDDLE work begins until a verifier exists that runs and rejects the current state on every checkable criterion — and no criterion is ever marked green except by that same pinned verifier, executed independently of the party that did the work, producing evidence on disk.

The deterministic checks that defend it live in `evals/cheap/checks.sh` and run
as part of the marketplace cheap tier.
