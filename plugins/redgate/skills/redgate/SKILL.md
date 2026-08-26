---
name: redgate
description: >-
  Run any idea through Red Gate: human-gated rounds, each a BEGIN/MIDDLE/END
  process whose BEGIN emits a verifier proven able to fail before work
  starts, and whose END is that pinned verifier run by a party that did not
  do the work. Use on /redgate "<idea>", or whenever a task needs its
  done-criteria proven falsifiable before building.
license: MIT
compatibility: >-
  PORTABILITY: the protocol is prose plus plain bash — no hooks, no
  subagent-spawning tool, no Workflow tool required. It runs identically
  under Claude Code, Codex (which reads this plugin's AGENTS.md natively),
  and GitHub Copilot (via `apm compile -t copilot`). Where a harness offers
  subagents, END runs in a fresh one; where it does not, END runs in a
  fresh session or falls to the human at the round gate — the independence
  requirement ports, the mechanism adapts. A Claude-Code hooks enforcement
  layer is planned as an optional hardening slice, never a dependency.
---

# redgate

## Invariant

No MIDDLE work begins until a verifier exists that runs and rejects the current state on every checkable criterion — and no criterion is ever marked green except by that same pinned verifier, executed independently of the party that did the work, producing evidence on disk.

Criteria that cannot be rejected are not criteria.

## What this is

The driver for the Red Gate protocol (`docs/red-gate-protocol.md` in this
marketplace — read it for the full design and its adversarial corrections).
A **run** is a sequence of human-gated **rounds**; every round is one
BEGIN/MIDDLE/END. This skill drives the run; the `criteria-contract` skill
(same plugin) owns BEGIN; `reconcile` (next slice) owns END.

## The round-zero rule

Start at the first round whose criteria you can write **without already
knowing the answer**. If you cannot write criteria for the work, write
criteria for the artifact that will tell you what the work is.

| Round type | END artifact | The verifier checks | Substance judged by |
|---|---|---|---|
| Orientation | a decision brief | its shape | the human, at the gate |
| Plan | an ordered slice list + proposed verifiers | its shape | the human, at the gate |
| Build | working change flipping one criterion | behavior | the verifier |
| Consolidation | the slice widened in place | behavior | the verifier |

"I don't know what to do yet" is not a blocker; it selects the round type.
And when rounds would be ceremony — the approach is agreed and the criterion
is writable today — go straight to a build round.

## Driving a round

1. **BEGIN** — invoke `criteria-contract`: interview (≤5 questions, defaults
   accepted by silence), emit `CRITERIA.md` + `check.sh` into
   `.redgate/<slug>/`, prove the gate red, get ratification, pin both files.
2. **MIDDLE** — one writer, one tracer-bullet slice flipping one criterion
   through every layer it names, no stub at the proving seam. Subagents (or
   parallel sessions) fan out **read-only**. Every hunk traces to a criterion
   id (`scope-fence`); the attempt bound is declared up front (`stop-rule`),
   scaled to the layers the criterion names. Never edit `.redgate/<slug>/`
   contents after ratification — not the criteria, not the checker.
3. **END** — run `.redgate/<slug>/check.sh` from a context that did not do
   the work (fresh subagent, fresh session, or the human), after re-hashing
   both pinned files against the manifest. `verify-before-claim` governs the
   verdict: no unrun PASS, ever.
4. **Round gate** — the human: accept / again / split — and on accept,
   whether the artifact seeds another round or the run is done.

## Budgets and recursion

- **Round budget**: declared in the manifest at run start, default **4**.
  Hitting it is a stop-and-report on the whole run, never a silent round 5.
- **Recursion** happens *inside* a round, automatically, only on the
  four-part spawn precondition (failed check with evidence + named seam +
  ≥2 sub-criteria proven red + budget above floor). Rounds are horizontal
  and human-gated; recursion is vertical and never crosses a round boundary.
- Budgets live as fields in `.redgate/<slug>/manifest` that this skill
  decrements — honest bookkeeping, not a meter the harness enforces.

## Not this

- **wayfinder** charts a multi-session effort as a ticket map and never
  executes; redgate executes one run and uses wayfinder-style ordering only
  to pick the next criterion. A wayfinder ticket is a natural *input* to
  `/redgate`.
- **orchestrate** is fan-out templates for research-and-verify; redgate may
  use it during a MIDDLE's read-only fan-out, but the single writer and the
  pinned verifier are redgate's own rules.
- **tracer-bullets** defines the thin slice; redgate is the loop that
  decides *which* slice, proves the gate red first, and verifies after.
