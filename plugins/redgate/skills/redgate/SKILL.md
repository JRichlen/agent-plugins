---
name: redgate
description: >-
  Default protocol for nontrivial work needing explicit criteria or evidence.
  Compose it around the most-specific applicable specialist skills rather than
  replacing them. Auto-trigger for planning, research, design, implementation,
  debugging, refactoring, review, deployment, multi-agent coordination, and
  external/irreversible actions when the work needs verified rounds or a
  classified human gate. Handle trivial work directly; route larger work
  through ARM/TRACE/JUDGE. Use the harness-native structured question primitive
  when available and compact textual choices otherwise; never emit prose questionnaires.
license: MIT
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

The discipline is harness-agnostic and the protocol is portable prose plus
plain bash: it requires no hooks,
subagent-spawning tool, or Workflow tool. It runs under Claude Code, Codex
(which reads this plugin's `AGENTS.md` natively), and GitHub Copilot (via
`apm compile -t copilot`). Where a harness offers subagents, JUDGE runs in a
fresh one; otherwise it runs in a fresh session or falls to the human at the
round gate. The independence requirement ports; the mechanism adapts. The
Claude Code hooks layer is optional hardening, never a dependency.

## Default routing and interaction contract

Treat Red Gate as the default **verification envelope** for nontrivial work,
even when the user does not name the skill. It is not the universal domain
router. First route to the most-specific applicable specialist skill or recipe
for the work itself (`diagnosing-bugs`, `codebase-design`, `orchestrate`,
`wayfinder`, `scope-fence`, etc.); wrap that work in Red Gate when explicit
criteria/evidence, iterative verified rounds, or a classified human gate are
needed. A specialist supplies the domain procedure; Red Gate supplies the
ARM/TRACE/JUDGE contract around it.

The common loop is: intake and infer context, clarify only a load-bearing
ambiguity, plan the smallest safe slice, execute it through the applicable
specialist procedure, verify with evidence, report the result, and escalate
only when risk or scope requires a human decision. This includes planning,
research, design, implementation, debugging, refactoring, review, deployment,
multi-agent work, security/auth, external writes, and destructive actions.
Calibration still protects small work: T0 questions and obvious reversible
edits are handled directly with no run directory and no ceremony. A task that
is fully handled by a specialist skill and needs no explicit evidence contract,
round loop, or classified gate does not activate Red Gate merely because it is
nontrivial.

### Interactive question contract — hard rule

When the harness exposes an interactive ask-question tool or other native
structured choice/confirmation primitive (for example `AskUserQuestion` or
`request_user_input`), use it for every decision, ratification, approval,
branch choice, WITNESS countersignature, scope or budget change, and final
acceptance. The examples are adapters, not canonical API names.

- Infer first and ask only when the answer changes behavior. Do not ask the
  user to restate context already present in the request, repository, or
  conversation.
- Ask one decision per interaction by default. Combine only tightly coupled
  choices, never a backlog of questions.
- Prefer 2-3 tap-ready options with the recommended option first. Use
  multi-select when several independent choices may all apply; use a compact
  confirmation when the decision is binary.
- Put the recommendation and its chief tradeoff in the option labels or short
  descriptions. Preserve Red Gate's stakes logic without requiring an essay.
- Never emit a long-form questionnaire or a numbered prose list that requires
  a large typed response. Free text is a last resort; if unavoidable, ask one
  bounded question that can be answered briefly.
- Never place a blocking question only in ordinary prose when a structured
  primitive is available. If no such primitive exists, emulate the same
  compact options in text and accept a one-token answer.
- Subagents never interview the user. They return ambiguities to the parent,
  which deduplicates them and owns the interactive question.

The existing shared interview budget remains **at most 5 questions across the
whole ARM**, not 5 questions per card or per stage. A MAJOR gate always needs
an explicit confirmation through the best structured interaction capability
available; silence and adjacent approvals never count as gate consent.

A blanket approval — "don't ask me anything", "you've got my sign-off for
whatever it takes", "just message me when it's green" — is an adjacent
approval. It may set scope and tolerance for PATCH-classified work; it is
never consent at a gate — not at any MAJOR gate, and never for landing or a
destructive step — and it never turns a gate into something scheduled to fire
after the human leaves. Under a blanket approval the driver still stops at
every MAJOR gate, stages what it can, and reports what is waiting.

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
   ask only load-bearing unknowns through the harness-native structured
   question primitive when available (compact textual choices otherwise)
   inside the shared ≤5-question budget, and write the calibration block into
   the `CRITERIA.md` header so the pin covers it. A **T0** task is declined by
   the protocol — do it directly, no run dir.
1. **ARM** — invoke `criteria-contract`: interview (≤5 questions total,
   calibration questions included, defaults accepted by silence), emit
   `CRITERIA.md` + `check.sh` into `.redgate/<slug>/`, **prove the gate
   red** — run `check.sh` against the current, unfixed state and quote the
   observed FAIL per criterion as evidence — get ratification (which
   ratifies the calibration block with it), pin both files.
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

**Red first, stated every time.** Every plan the driver presents — a reply,
a plan round, a handoff — carries the red step as its own line: run the
verifier against the current state *before any TRACE work* and show it
FAILING, with the observed failure quoted. A sequence that reads
scaffold → build → judge, with no observed red between scaffold and build,
is incomplete and is not ratified. The round-zero rule chooses *which*
verifier goes red first (behavior for a build round, shape for a scout
brief) — never whether one does.

## The classified round gate

Autonomy flows downhill from an approved plan: a human-ratified plan is the
**mandate**, and rounds executing strictly inside it pass their
gates automatically.

| Class | Behavior | Qualifies when |
|---|---|---|
| PATCH | Auto-pass; append to `gates.log`; fold into the summary; seed the next round | ALL of: build/widen round · verifier green via independent JUDGE · zero WITNESS · diff inside the fence · criteria strictly derived from a human-approved plan slice · no escalator |
| MINOR | Auto-pass **with a prominent flag** and a standing veto; staged separately revertible; never a blocking question | Durable-but-revertible artifacts inside the approved direction |
| MAJOR | **Stop.** Structured human confirmation naming the specific decision and mechanism; a prior adjacent "yes" does not transfer | Any escalator, or any semver-gate property landing MAJOR |

**Always MAJOR — never auto-passed, never softened:** the scout
decision; the plan round's approval (the mandate itself); a run's first
ratification and every WITNESS countersignature; widening the scope fence
mid-run — a "while you're in there" bundled into the ask that no ratified
criterion covers is a widen, not part of the slice; round-budget or depth
extension; the run's final acceptance; landing on `main`; and anything
semver-gate's own table calls MAJOR (irreversible actions — `prove-the-undo`
first — protection toggles, `egress-gate` transmissions to unnamed
destinations).

**Landing and destruction are their own gates.** Merging or landing on
`main`, and every destructive or irreversible action — table truncation,
data deletion, force-push, a write to production — is a separate MAJOR gate,
confirmed at the moment it would happen by a structured confirmation that
names that specific action. It is never bundled into an earlier ratification
or plan approval, never written as a criterion the verifier satisfies on its
own, and never scheduled to run unattended. A single option of the form
"ratify and I'll do the rest autonomously — land it and message you" is a
protocol violation, not a courtesy: the honest offer stages the change
(branch, PR, prepared statement with its proven undo) and holds the landing
and each destructive step for their own confirmations.

**Derived ratification.** A build round whose criteria are byte-derivable
from an approved plan slice auto-ratifies as PATCH with the derivation
logged. Any deviation — added criteria, changed check shapes, different
layers — escalates to MAJOR. The human approved those exact criteria once,
at plan approval; that is what keeps auto-ratification from becoming
self-ratification.

**The gate ledger.** Every gate decision — class, driving property,
**disposition**, outcome, **lesson** — is appended to
`.redgate/<slug>/gates.log`. The disposition names what the human actually
did: `auto` (PATCH, no human) · `silent`/`vetoed` (MINOR standing veto) ·
`approved`/`revised`/`declined` (MAJOR — the human's answer, never a
default). It exists so the approval-fatigue report (`recurrence-detector`'s
`gate-report.sh`) can tell a calibrated mandate from rubber-stamping — a
MAJOR streak that is 100% `approved` unchanged is a signal, not a
compliment. An auto-pass that cannot cite its
qualifying conditions is a protocol violation, not a judgment call.
Precedence is semver-gate's own: a coded deny (an autoMode
`hard_deny`/`soft_deny` pattern, a harness permission refusal) always wins
over this classification. A coded allow is permission to run a tool, not
consent at a gate: it never pre-authorizes landing on `main` or a destructive
step, which still stop for their own confirmation.

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
