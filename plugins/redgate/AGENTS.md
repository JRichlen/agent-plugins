# AGENTS.md — redgate

Run any idea through Red Gate: rounds of ARM/TRACE/JUDGE with graduated autonomy — each round gate is classified PATCH/MINOR/MAJOR via semver-gate, so derived work auto-passes inside a human-approved mandate while scout decisions, plan approval, and irreversible actions always block on the human. ARM emits a verifier proven able to fail; JUDGE is that pinned verifier run by a party that did not do the work.

Redgate is the default operating protocol for nontrivial planning,
research, design, building, debugging, refactoring, review, deployment,
multi-agent coordination, security/auth, external writes, and destructive
actions. Auto-trigger it from the task shape; do not wait for `/redgate`.
Calibrate T0 work back to a direct answer or obvious reversible edit so the
default does not become ceremony.

When an interactive ask-question tool is available, every user decision,
approval, ratification, multi-select, WITNESS countersignature, scope/budget
change, and final confirmation goes through it. Ask one decision per call by
default, offer 2-3 tap-ready options with the recommendation first, and use
multi-select only for independent choices. Never dump a long prose
questionnaire or require a large typed response. Free text is a last resort
and must be one bounded prompt. Subagents return ambiguities to the parent;
they never interview the user directly.

## How to use it

Read `skills/redgate/SKILL.md` (the round driver) and
`skills/criteria-contract/SKILL.md` (the ARM stage) and follow them — they
are the authoritative description of this plugin's workflow and the invariant
it defends. The generator `skills/criteria-contract/scripts/scaffold-run.sh`
creates and pins runs under `.redgate/<slug>/`; the emitted `check.sh` is the
verifier. The command `commands/redgate.md` is the entry point a user invokes.

## Cross-harness operation

This file is the complete operating doc for harnesses that read `AGENTS.md`
natively (Codex, and Copilot via `apm compile -t copilot`, which aggregates
installed APM dependencies into the generated .github/copilot-instructions.md file). Everything
load-bearing is prose plus plain bash — no Claude-Code primitive is required:

- **Calibrate before ARM**: set the five sizing dials — tier, domain,
  scope, taste, orchestration — per
  `skills/redgate/references/calibration.md`; a T0 task is done directly
  with no run, and the calibration block lives in the `CRITERIA.md` header
  so the pin covers it.
- **ARM / red gate / pin**: run `scaffold-run.sh`, write criteria, run
  `check.sh` (exit 1 = red = dispatchable; exit 99 = harness failure, never
  red; a check_cmd exiting non-zero — 127 included — is a legitimate FAIL),
  ratify, `scaffold-run.sh --pin <slug>`.
- **JUDGE independence** without subagents (subagents are a Claude-Code
  convenience, not a dependency — the pattern ports to any harness): run
  `check.sh` in a fresh session,
  or hand the human the verdict table — the requirement is that the party
  who did the work never grades it; the mechanism adapts per harness.
- **Round gates are classified, not defaulted to the human**: PATCH (strictly
  derived from an approved plan slice, verifier green, no escalator)
  auto-passes and appends to `gates.log`; MINOR auto-passes with a prominent
  flag and standing veto; MAJOR — scout decisions, plan approval, first
  ratification, WITNESS countersignatures, fence/budget changes,
  anything irreversible — always stops for an interactive tool confirmation.
- Full protocol: `docs/red-gate-protocol.md` at the marketplace root.

## Status: all five slices shipped

Driver, ARM (criteria-contract), JUDGE (reconcile), the hooks enforcement
layer (hooks are Claude-Code-specific; on another harness the same rules hold
as prose discipline), and the protocol references. The growth loop's DETECT
organ ships separately as the `recurrence-detector` plugin. Each slice was
built as a real Red Gate round — see `.redgate/*/gates.log` for the run
records, including the two rounds where the protocol caught its own defects.

## The invariant this plugin defends

No TRACE work begins until a verifier exists that runs and rejects the current state on every checkable criterion — and no criterion is ever marked green except by that same pinned verifier, executed independently of the party that did the work, producing evidence on disk.

The deterministic checks that defend it live in `evals/cheap/checks.sh` and run
as part of the marketplace cheap tier.
