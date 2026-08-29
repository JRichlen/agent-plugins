---
name: redgate
description: >-
  Run any idea through Red Gate: rounds of ARM/TRACE/JUDGE with graduated
  autonomy — each round gate is classified PATCH/MINOR/MAJOR via semver-gate,
  so derived work auto-passes inside a human-approved mandate while
  scout decisions, plan approval, and irreversible actions always block
  on the human. ARM emits a verifier proven able to fail; JUDGE is that
  pinned verifier run by a party that did not do the work. Use on
  /redgate "<idea>", or whenever done-criteria must be proven falsifiable
  before building.
license: MIT
compatibility: >-
  PORTABILITY: the protocol is prose plus plain bash — no hooks, no
  subagent-spawning tool, no Workflow tool required. It runs identically
  under Claude Code, Codex (which reads this plugin's AGENTS.md natively),
  and GitHub Copilot (via `apm compile -t copilot`). Where a harness offers
  subagents, JUDGE runs in a fresh one; where it does not, JUDGE runs in a
  fresh session or falls to the human at the round gate — the independence
  requirement ports, the mechanism adapts. A Claude-Code hooks enforcement
  layer ships in this plugin as optional hardening, never a dependency.
---

# redgate

## Invariant

No TRACE work begins until a verifier exists that runs and rejects the current state on every checkable criterion — and no criterion is ever marked green except by that same pinned verifier, executed independently of the party that did the work, producing evidence on disk.

Criteria that cannot be rejected are not criteria.

## What this is

The driver for the Red Gate protocol (`docs/red-gate-protocol.md` in this
marketplace — read it for the full design and its adversarial corrections).
A **run** is a sequence of **rounds** with classified gates; every round is one
ARM/TRACE/JUDGE. This skill drives the run; the `criteria-contract` skill
(same plugin) owns ARM; `reconcile` (same plugin) owns JUDGE.

## The round-zero rule

Start at the first round whose criteria you can write **without already
knowing the answer**. If you cannot write criteria for the work, write
criteria for the artifact that will tell you what the work is.

| Round type | Judged artifact | The verifier checks | Substance judged by |
|---|---|---|---|
| Scout | a decision brief | its shape | the human, at the gate |
| Plan | an ordered slice list + proposed verifiers | its shape | the human, at the gate |
| Build | working change flipping one criterion | behavior | the verifier |
| Widen | the slice widened in place | behavior | the verifier |
| Retro | the run's lessons ledger, completed | its shape | the human, at the gate |

"I don't know what to do yet" is not a blocker; it selects the round type.
And when rounds would be ceremony — the approach is agreed and the criterion
is writable today — go straight to a build round.

## Driving a round

0. **Calibrate** — before any criteria, set the five dials (tier, domain,
   scope, taste, orchestration) per
   [`references/calibration.md`](references/calibration.md): infer first,
   ask only load-bearing unknowns inside the shared ≤5-question budget, and
   write the calibration block into the `CRITERIA.md` header so the pin
   covers it. A **T0** task is declined by the protocol — do it directly,
   no run dir.
1. **ARM** — invoke `criteria-contract`: interview (≤5 questions total,
   calibration questions included, defaults accepted by silence), emit
   `CRITERIA.md` + `check.sh` into `.redgate/<slug>/`, prove the gate red,
   get ratification (which ratifies the calibration block with it), pin
   both files.
2. **TRACE** — one writer, one tracer-bullet slice flipping one criterion
   through every layer it names, no stub at the proving seam. Subagents (or
   parallel sessions) fan out **read-only**. Every hunk traces to a criterion
   id (`scope-fence`); the attempt bound is declared up front (`stop-rule`),
   scaled to the layers the criterion names. Never edit `.redgate/<slug>/`
   contents after ratification — not the criteria, not the checker.
3. **JUDGE** — run `.redgate/<slug>/check.sh` from a context that did not do
   the work (fresh subagent, fresh session, or the human), after re-hashing
   both pinned files against the manifest. `verify-before-claim` governs the
   verdict: no unrun PASS, ever.
4. **Round gate — classified, not defaulted to the human.** Classify the
   gate with `semver-gate`'s four-property test and tie-break (any property
   MAJOR → gate MAJOR), then act by class as the table below requires.

## The classified round gate

Autonomy flows downhill from an approved plan: a human-ratified plan is the
**mandate**, and rounds executing strictly inside it pass their
gates automatically.

| Class | Behavior | Qualifies when |
|---|---|---|
| PATCH | Auto-pass; append to `gates.log`; fold into the summary; seed the next round | ALL of: build/widen round · verifier green via independent JUDGE · zero WITNESS · diff inside the fence · criteria strictly derived from a human-approved plan slice · no escalator |
| MINOR | Auto-pass **with a prominent flag** and a standing veto; staged separately revertible; never a blocking question | Durable-but-revertible artifacts inside the approved direction |
| MAJOR | **Stop.** Structured question naming the specific decision and mechanism; a prior adjacent "yes" does not transfer | Any escalator, or any semver-gate property landing MAJOR |

**Always MAJOR — never auto-passed, never softened:** the scout
decision; the plan round's approval (the mandate itself); a run's first
ratification and every WITNESS countersignature; fence widening;
round-budget or depth extension; the run's final acceptance; and anything
semver-gate's own table calls MAJOR (irreversible actions — `prove-the-undo`
first — protection toggles, `egress-gate` transmissions to unnamed
destinations).

**Derived ratification.** A build round whose criteria are byte-derivable
from an approved plan slice auto-ratifies as PATCH with the derivation
logged. Any deviation — added criteria, changed check shapes, different
layers — escalates to MAJOR. The human approved those exact criteria once,
at plan approval; that is what keeps auto-ratification from becoming
self-ratification.

**The gate ledger.** Every gate decision — class, driving property, outcome,
**lesson** — is appended to `.redgate/<slug>/gates.log`. An auto-pass that
cannot cite its qualifying conditions is a protocol violation, not a
judgment call. Precedence is semver-gate's own, unchanged: a coded rule
(autoMode pattern, harness permission) always wins over this classification.

**Reflection lives at the gate, never as a stage** (prior art:
`docs/research/phase-structure-prior-art.md` — unenforced in-cycle phases
evaporate; reflection between iterations is what every verified-work loop
does). Three rules give it teeth:

- **The lesson field is mandatory** at every gate: one line, what this round
  taught. "None" is a legal lesson only at a PATCH gate.
- **A red verdict leaves a durable artifact**: its lesson names what the
  next contract must encode, and the next round's ARM starts by reading
  the prior rounds' `gates.log` (including predecessor `-rN` run dirs).
  That is the Reflexion mechanism — failure feeds the next episode's setup,
  not a reflective phase inside this one.
- **Widen cadence**: after 3 consecutive build gates with no
  widen or retro round, the driver proposes one as the next round;
  declining is logged in the gate line. An invitation-only "look back"
  gets skipped — Polya's own account — so the cadence is the default, not
  the exception.

## References

Load these when the situation calls for them — they stay out of the default
context budget:

- [`references/calibration.md`](references/calibration.md) — the five
  sizing dials (tier, domain, scope, taste, orchestration), the T0 decline,
  and the recalibration rules.
- [`references/round-types.md`](references/round-types.md) — criteria
  templates per round type, and the shape-vs-behavior ladder.
- [`references/handoff-envelope.md`](references/handoff-envelope.md) — the
  typed DOWN/UP envelope, its caps, and why criteria are excluded from them.
- [`references/recursion-contract.md`](references/recursion-contract.md) —
  the four-part spawn precondition, sibling budget pool, `depth_remaining`,
  harvest, and leases.

## Budgets and recursion

- **Round budget**: declared in the manifest at run start, default **4**.
  Hitting it is a stop-and-report on the whole run — extension is an
  always-MAJOR gate, never a silent round 5.
- **Recursion** happens *inside* a round, automatically, only on the
  four-part spawn precondition (failed check with evidence + named seam +
  ≥2 sub-criteria proven red + budget above floor). Rounds are horizontal
  with classified gates; recursion is vertical and never crosses a round
  boundary.
- Budgets live as fields in `.redgate/<slug>/manifest` that this skill
  decrements — honest bookkeeping, not a meter the harness enforces.

## Not this

- **wayfinder** charts a multi-session effort as a ticket map and never
  executes; redgate executes one run and uses wayfinder-style ordering only
  to pick the next criterion. A wayfinder ticket is a natural *input* to
  `/redgate`.
- **orchestrate** is fan-out templates for research-and-verify; redgate may
  use it during a TRACE's read-only fan-out, but the single writer and the
  pinned verifier are redgate's own rules.
- **tracer-bullets** defines the thin slice; redgate is the loop that
  decides *which* slice, proves the gate red first, and verifies after.
