# AGENTS.md — redgate

Run work through Red Gate as rounds of ARM/TRACE/JUDGE with graduated autonomy — each round gate is classified PATCH/MINOR/MAJOR via semver-gate, so derived work auto-passes inside a human-approved mandate while scout decisions, plan approval, and irreversible actions always block on the human. ARM emits a verifier proven able to fail; JUDGE is that pinned verifier run by a party that did not do the work.

Redgate is a **working harness/protocol layer**, not the universal router for
nontrivial tasks. Route to the most-specific applicable specialist skill or
recipe for the work itself. Compose Redgate around that procedure when the
execution benefits from explicit falsifiable criteria, iterative verified
rounds, or a classified human gate. The specialist owns the domain procedure;
Redgate reinforces how the work is carried out and verified. Calibration sends
T0 work straight through, and specialist work with no need for an evidence
contract or classified gate does not gain Redgate ceremony merely because it
is complex.

When a harness-native structured choice/confirmation primitive is available,
use it for decisions, approvals, ratification, multi-selects, WITNESS
countersignatures, scope/budget changes, and final confirmation. Ask one
decision per interaction by default, offer 2-3 tap-ready options with the
recommendation first, and use multi-select only for independent choices. If no
structured primitive exists, present the same compact options in text and
accept a short answer. Never dump a long prose questionnaire or require a
large typed response. Free text is a last resort and must be one bounded
prompt. Subagents return ambiguities to the parent; they never interview the
user directly.

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
  ratification, WITNESS countersignatures, fence/budget changes (a
  mid-run widen included), landing on `main`, anything irreversible — always
  stops for a structured human confirmation using the best interaction
  primitive the harness provides, at the moment the action would happen; a
  blanket approval never pre-authorizes one, a coded allow rule (autoMode
  `allow`, harness permission) never lowers landing or a destructive action
  below MAJOR or stands in for its confirmation (coded denies still win and
  block), and landing or a destructive step is never bundled into an earlier
  ratification or scheduled to run unattended.
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
