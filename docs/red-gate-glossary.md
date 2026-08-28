# Red Gate — glossary and terminology rulings

The protocol grew fast, and its vocabulary grew faster. This document is the
**canonical** meaning of every load-bearing term, plus the product rulings
that resolve the collisions the growth created. When prose elsewhere in this
marketplace disagrees with this file, this file wins and the other prose is a
bug.

Companion documents: [`red-gate-protocol.md`](red-gate-protocol.md) (the
spec), [`../plugins/redgate/skills/redgate/references/calibration.md`](../plugins/redgate/skills/redgate/references/calibration.md)
(Calibration — how a run is sized before it starts).

## Core objects

| Term | Canonical meaning |
|---|---|
| **run** | One invocation of the protocol on one idea: a directory `.redgate/<slug>/` plus the sequence of rounds executed under it. A run ends at final acceptance (always-MAJOR) or when its round budget stops it. |
| **round** | One BEGIN/MIDDLE/END cycle inside a run. Rounds are the *horizontal* axis: each ends at a classified gate, and learning between rounds happens by writing a **fresh** contract, never by editing a pinned one. |
| **round type** | What the round produces: **orientation** (a decision brief), **plan** (an ordered slice list with proposed verifiers), **build** (a working change flipping one criterion), **consolidation** (a slice widened in place), **retro** (the run's lessons ledger, completed). Selected by the round-zero rule. |
| **stage** | One of BEGIN / MIDDLE / END *within* a round. BEGIN writes and pins the contract; MIDDLE is the single-writer slice; END is the independent verification. |
| **slice** | The tracer-bullet unit of MIDDLE work: the smallest change that flips one criterion through every layer it names, with no stub at the proving seam. |
| **slug** | The kebab-case identifier of a run; names its directory `.redgate/<slug>/`. |

## The contract

| Term | Canonical meaning |
|---|---|
| **contract** | The pair `CRITERIA.md` + `check.sh`, ratified together, pinned together. Immutable for the life of the round. |
| **criterion** | One numbered entry in `CRITERIA.md`: statement, layers crossed, why it is red today (`absent` or `present-but-wrong`), and either a `check_cmd` or a declared UNVERIFIABLE. |
| **checkable** | A criterion whose truth a command decides. At least two per contract; checkable criteria must be the majority. |
| **UNVERIFIABLE** | A criterion whose truth only a named human observation decides. Declared at BEGIN, countersigned individually at ratification, capped at 1 (2 with explicit human opt-in). Never a shell command — writing `check_cmd: UNVERIFIABLE …` runs it as a command and red-locks the criterion. |
| **check_cmd** | The single-line command the harness runs for one criterion. Exit 0 = PASS; any non-zero — 127 included — is a legitimate FAIL. |
| **verifier** | The generalized four-property object: runnable · proven able to fail · pinned · independently executed. `check.sh` is only its code-domain instance; a rubric-scored document review can be a verifier too, if it holds all four properties. |
| **red gate / red-from-birth** | The BEGIN requirement that the verifier reject the current state on every checkable criterion *before* any MIDDLE work. A criterion that cannot go red is not a criterion. |
| **ratification** | The human approving the contract while looking at the literal red output, per criterion, with one line stating what will count as green. Happens once per round. |
| **pin** | Recording the sha256 of both contract files into the manifest (`scaffold-run.sh --pin`). After the pin, neither file is ever edited. |
| **drift** | Either pinned file hashing differently at END than at the pin. Drift fails the run outright — it is never a warning. |
| **positive control** | For a check shape with a known-good target: the same shape shown passing there today. Proves the check *can* pass. |
| **Calibration** | The run-sizing record produced at BEGIN step 0 — tier, domain, scope, taste, orchestration level — written into the header of `CRITERIA.md` so the existing pin covers it. See the calibration reference. **Ruling:** "Calibration" (capitalized, run-level) means only this. |

## Verification

| Term | Canonical meaning |
|---|---|
| **END independence** | The party who did the MIDDLE work never grades it. Mechanism adapts per harness (fresh subagent, fresh session, or the human); the requirement does not. |
| **reconcile** | The END-stage skill/script: refuses unpinned runs, re-hashes both pinned files, runs the verifier itself, and rejects any PASS without evidence written during *its* run. |
| **evidence** | `evidence/<n>.out`, written by the harness while executing criterion `n`. A PASS without fresh evidence is REJECTED, not trusted. |
| **harness (verifier harness)** | The emitted `check.sh` loop: preflight, per-criterion execution under timeout, verdict lines. **Ruling:** when ambiguity is possible, say *verifier harness* for `check.sh` and *agent harness* for Claude Code/Codex/Copilot. Bare "harness" inside run docs means the verifier harness. |
| **harness failure (exit 99)** | The verifier harness's own breakage (missing prerequisite, unwritable `evidence/`, no criteria parsed). Never red, never a FAIL — fix the harness. Preflight covers harness prerequisites only, never the subject under test. |
| **mutation control** | The post-green discipline: revert the slice's core hunk and re-run; a criterion still green is UNVERIFIABLE-in-fact, not proven. The protocol's four-time lesson: assert **exit codes on passing fixtures**, not messages. |
| **negative control** | An eval-tier fixture built to FAIL (a gutted stub, `RG_TEST_DROP_EVIDENCE=1`), proving a check can reject. **Ruling:** the eval-tier artifact formerly also called a "calibration stub/control" is canonically a *negative control*; "calibration" is reserved for run sizing. |

## Gates and autonomy

| Term | Canonical meaning |
|---|---|
| **round gate** | The decision point after END: continue, stop, or ask. Classified, never defaulted to the human. |
| **gate class** | PATCH (auto-pass, logged) / MINOR (auto-pass with prominent flag and standing veto) / MAJOR (stop; structured question). Classified by semver-gate's four-property test; any property MAJOR → gate MAJOR. |
| **escalator** | A condition that forces MAJOR regardless of other properties: orientation decisions, plan approval, first ratification, UNVERIFIABLE countersignatures, fence widening, budget/depth extension, final acceptance, anything irreversible. Never auto-passed, never softened. |
| **autonomy envelope** | A human-approved plan. Rounds executing strictly inside it pass their gates automatically; autonomy flows downhill from the approval, never upward from the work. |
| **derived ratification** | Auto-ratification of a build round whose criteria are byte-derivable from an approved plan slice. Any deviation escalates to MAJOR. This is what keeps auto-ratification from becoming self-ratification. |
| **gates.log** | The append-only ledger in the run dir: round · class · driving property · outcome · lesson. An auto-pass that cannot cite its qualifying conditions is a protocol violation. |
| **lesson** | The mandatory one-line reflection in every gates.log entry — the protocol's answer to "where does Reflect go": at the gate, never as a stage. A red verdict's lesson names what the next contract must encode, and the next round's BEGIN reads prior gates.log files first. |
| **retro round** | The optional round type whose END artifact is the run's completed lessons ledger; shape-checked, substance judged at the gate. Proposed by default after 3 consecutive build gates (the consolidation cadence). |

## Budgets and recursion

| Term | Canonical meaning |
|---|---|
| **round budget** | Max rounds per run, declared in the manifest at start (default 4). Extension is always-MAJOR; there is no silent round 5. |
| **attempt bound** | Per-criterion retry cap during MIDDLE (stop-rule), declared before dispatch, scaled to the layers named. |
| **spawn precondition** | All four before recursing: failed check with evidence + named seam + ≥2 sub-criteria proven red + budget above floor. Recursion is *vertical*, lives inside one round, and never crosses a round boundary. |
| **depth_remaining** | The manifest field recursion decrements. Zero means no more children, ever, for this run. |
| **handoff envelope** | The typed DOWN/UP pointer message between parent and child. Token-capped; criteria are excluded from the cap because compressing the contract corrupts it. |
| **fence** | The declared set of paths a round may modify (scope-fence). Every hunk traces to a criterion id; widening the fence is an escalator. |

## Lifecycle vocabulary (PM ruling — closes a real gap)

The manifest field `phase` and the stage names collided, and nothing named
the end of a round. Canonical lifecycle verbs for a run directory:

1. **open** — scaffold creates the run; manifest `phase=BEGIN`.
2. **pin** — ratified contract hashed into the manifest; `phase=MIDDLE`.
3. **dispatch** — MIDDLE work begins under the fence and attempt bounds.
4. **reconcile** — independent END produces the verdict table.
5. **gate** — the classified decision, appended to `gates.log`.
6. **advance** — on a continuing run: next round opens with a **fresh
   contract** (a new run dir suffixed `-r<N>`, as `slice2-reconcile-r2` did);
   the prior round's dir is never reopened.
7. **close** — final acceptance (always-MAJOR) or budget stop; the run dir
   becomes a record.

**Known defect, tracked in PR #75's findings:** nothing today writes a
terminal phase, so closed runs still read `phase=MIDDLE`. Until the
manifest gains a `closed` marker (a script change, gated by the eval tiers),
the `gates.log` final entry is the authoritative signal that a run is
closed. Do not infer "in progress" from `phase=MIDDLE` alone.

## Lexicon v2 — proposed, not yet adopted

The founding vocabulary has three defects the glossary above can pin but
not fix: **positional names** (BEGIN/MIDDLE/END say *when*, not *what you
must do* — MIDDLE is the emptiest word in the protocol, naming the actual
work as filler between two other things), **negative names**
(UNVERIFIABLE says what a criterion isn't, spending tokens to point away
from the required behavior), and **one collision** (two unrelated
"envelopes"). Lexicon v2 replaces them under four rules:

1. **Verbs over positions.** A stage name is an instruction — reading it
   tells you what to do, so surrounding prose can stop re-explaining it.
2. **Names that make violations sound wrong.** The invariant should be
   audible in ordinary sentences: "judging your own work," "dispatching
   through an unarmed gate," "an unwitnessed taste criterion."
3. **Say the required behavior, never its absence.**
4. **One word, one meaning** — no term reused across layers.

### The stages

| Current | Proposed | Why it reinforces behavior |
|---|---|---|
| BEGIN | **ARM** | You arm the gate: write criteria, prove each can fire (red), ratify, pin. A tripwire that cannot fire is not armed — "proven able to fail" lives inside the word. "Unarmed dispatch" names the core violation in two words. |
| MIDDLE | **TRACE** | Fire one tracer: single writer, one slice, through every layer named, no stub at the proving seam. Aligns with the existing tracer-bullet vocabulary instead of sitting beside it. |
| END | **JUDGE** | The verdict, rendered independently. Nobody judges their own case — END independence, the protocol's hardest-to-enforce invariant, becomes the word's ordinary meaning. "Self-judging" is the violation. |

A round is one **ARM → TRACE → JUDGE** cycle. "The gate is armed" compresses
"criteria written, proven red, ratified, and pinned" — four clauses into
two words, which is where the token leanness actually comes from: the verbs
carry the rules, so prose stops restating them.

### Round types (all verbs, matching)

| Current | Proposed | Why |
|---|---|---|
| orientation | **SCOUT** | Go look before deciding; the artifact is what you saw (a decision brief). |
| plan | **PLAN** | Already a verb; keep. |
| build | **BUILD** | Already a verb; keep. |
| consolidation | **WIDEN** | The actual behavior — the slice widened in place — in one word instead of five syllables. |

### The renames that fix defects

| Current | Proposed | Why |
|---|---|---|
| UNVERIFIABLE | **WITNESS** | Positive and imperative: this criterion requires a named human witness, countersigned individually. Also removes the standing trap where `check_cmd: UNVERIFIABLE …` runs as a command — `WITNESS:` was never a plausible command. |
| autonomy envelope | **MANDATE** | Fixes the collision with the handoff envelope outright. "Inside the mandate" / "exceeds the mandate" is how delegated authority is described in ordinary English, which is exactly what an approved plan is. Handoff envelope keeps "envelope" unchallenged. |
| harness failure (exit 99) | **FAULT** | One word; keeps "failure" reserved for criteria (FAIL). A FAULT is never a verdict. |

Unchanged on purpose: run, round, slice, gate, PATCH/MINOR/MAJOR, pin,
drift, evidence, fence, contract, Calibration, mutation control, negative
control, reconcile (the skill name — the JUDGE stage's owner).

### Migration policy (staged, gated)

1. **Now (free):** new prose may use v2 with the v1 term in parentheses on
   first use; this glossary is the alias table either way.
2. **Docs sweep (cheap-tier gated):** rename across SKILL.md/references/
   protocol doc in one commit, keeping a v1→v2 alias table here so old
   run records stay readable.
3. **Mechanical rename (MAJOR, human-gated):** `phase=` manifest values,
   `check.sh` verdict strings, the hook guard's phase matching, and every
   eval grep that pins v1 strings. This is scripts-and-evals territory —
   it rides with the PR #75 fix batch or not at all, never as a drive-by.

Committed run records under `.redgate/` are never rewritten — they are
provenance, and v1 vocabulary inside them is part of the record.

## Deprecations

- "calibration stub", "calibration control" (eval tier) → **negative control**.
- "phase" used loosely for BEGIN/MIDDLE/END prose → **stage** in prose;
  `phase` names only the manifest field.
- "check harness" / bare "harness" in ambiguous contexts → **verifier
  harness** vs **agent harness**.
- "ticket" (imported from wayfinder discussions) → a wayfinder concept;
  inside a run the unit is a **criterion**, inside a plan it is a **slice**.
