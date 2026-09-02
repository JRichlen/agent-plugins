# Red Gate — a recursive ARM/TRACE/JUDGE protocol for skill coordination

**Status:** design of record for how this marketplace's skills compose into one
automated, interactive process triggered from a one-line idea.
**How it was produced:** a 12-agent workflow — four parallel survey agents
(external orchestration-pattern research, recursion/termination + spec-first
research, token-efficient-handoff research, and a read of all 24 shipped
`SKILL.md` files), three independent candidate designs from deliberately
divergent angles, two judges scoring on separate lenses, one synthesis, and two
adversarial critics. The critics returned 27 findings, five of them fatal; the
fatal fixes are folded into this document and recorded in
[Corrections](#corrections-applied-after-adversarial-review).

**One line:** turn a one-line idea into a **verifier proven able to fail**, flip
one criterion green with a real thin slice, then let someone who did not do the
work run the verifier — round after round, in any domain of the SDLC or AI-DLC.

`check.sh` appears throughout this document as the **code-domain reference
implementation** of the verifier, because shell is where the mechanics are
easiest to state exactly. It is not the protocol. Read "check.sh" as "the
verifier"; [The verifier, generalized](#the-verifier-generalized) gives the
mapping for research, planning, docs, ops, and judged work.

---

## The problem this solves

The marketplace has 24 skills across 21 plugins. Each is a single-invariant
discipline that works alone. Nothing composes them — there is no answer to
"I have an idea, now run the right skills in the right order and prove you
finished." Red Gate is that answer: a self-similar three-stage process where
ARM writes a falsifiable contract, TRACE cuts one tracer-bullet slice, and
JUDGE is a fresh agent executing the contract.

## The invariant

> No TRACE work begins until a **verifier** exists that **runs and rejects the
> current state on every checkable criterion**. No criterion is ever marked
> green except by that same pinned verifier, executed by a party that did not
> do the work, producing evidence. Criteria are ratified once **per round** and
> never edited — a wrong contract is corrected by spawning a child within the
> round, or by letting the round end and seeding the next round's fresh
> contract, never by rewriting the ratified one.

Criteria that cannot be rejected are not criteria. That is the whole design in
one sentence.

---

## The verifier, generalized

Red Gate is a process model for executing tasks, not a shell-script convention.
The load-bearing property is never "it is bash" — it is four properties any
verifier must have, whatever the domain:

1. **Runnable** — it executes against the current state, on demand, without the
   worker's cooperation.
2. **Proven able to fail** — it was run at ARM and rejected the starting
   state. A verifier that has never said no is not a verifier.
3. **Pinned** — its definition cannot be edited by the party doing the work.
4. **Independently executed** — at JUDGE it is run by a party that did not do
   the work: a fresh agent, a different tier, or the human at the round gate.

What that concretely is varies by task domain:

| Task domain | The verifier | "Proven red" means | Coupling control |
|---|---|---|---|
| Code | Test suite / `check.sh` / CI tier | Tests fail before the change | Revert the hunk, must re-fail |
| Research / scout | Shape checks on the brief + the human round gate | The artifact does not exist yet | The human rejects substance shape cannot see |
| Planning | Shape checks on the slice list + approval gate | No plan file, no proposed criteria | Each slice's proposed verifier must itself be red-able |
| Docs / knowledge | `docs-hygiene` audit against current repo state | The claim is absent or stale today | Re-audit after an unrelated change; claim must survive |
| Ops / infra | A probe or synthetic check against the live system | The endpoint 404s / the alert fires | Tear down the change; probe must go red again |
| Judged output (prose, design) | An LLM rubric **with a negative control** | The stub/baseline fails the rubric | The calibration case: a gutted input must not pass |

The last row is the important one, and this marketplace has already built it:
the behavioral eval tier's **calibration cases** are exactly the mutation
control translated to judged verifiers — a stub that passes anyway proves the
rubric measures the model, not the work. The repo's own three eval tiers are
the verifier ladder applied to itself: cheap = shape, behavioral = judged with
negative control, deep = end-to-end in a sandbox. Red Gate does not invent a
new verification scheme; it applies the one this repo already trusts to every
task the system executes.


---

## Why "the criteria are defined up front" was not enough

The raw idea said ARM should define the verifiable output criteria. Research
and adversarial review both say that is too weak, in five specific ways. These
are the **refinements** — the places the original idea needed correcting, not
merely implementing.

| The original idea | Why it fails | The refinement |
|---|---|---|
| ARM "defines verifiable criteria" | Criteria written but never executed are self-report. A model writes criteria it already believes it meets. | **The red gate.** `check.sh` must run and come back FAIL on every checkable criterion before TRACE starts. |
| Every output is verifiable | Taste, prose, and exploration are not command-checkable. A hard red gate incentivizes *fake* `check_cmd`s written purely to clear it. | A declared **`WITNESS`** verdict, capped and individually human-countersigned at ARM — never an JUDGE downgrade of a red check. |
| JUDGE is "checked against ARM's criteria" | Omits *who* checks. LLMs are poor at autonomous error detection (Huang et al., ICLR 2024); the common failure is silently rewriting criteria to match what was built. | A **fresh agent** that did not write the code, handed only the criteria, the script, and the diff — plus sha-pinning so drift is detected mechanically. |
| "Subagents fan out for creativity" | Conflates reading with writing. Concurrent writers on shared code produce conflicting assumptions (Cognition's single-writer principle; Anthropic's own caveat that orchestrator-worker misfires on code editing). | **Fan out reads, funnel writes.** Fan-out is for search, analysis, and option generation. Exactly one writer per run by default. |
| An agent's output "can be a plan that breaks the problem into more subagents" | Implies *eager* decomposition. ADaPT shows the opposite ordering wins; an eager tree propagates a wrong top-level split through everything beneath it. | **Lazy recursion.** Attempt the slice first; decompose only at an observed, named failure with demonstrated sub-criteria. |
| "Self-similar/recursive" | Self-similarity is a shape, not a termination rule. Unbounded self-similarity is unbounded cost. | A four-part **spawn precondition** plus numeric depth/budget backstops. |
| "Handoffs must be token-efficient" | Half right, half dangerous. Compressing the *criteria* is goal drift. | Pointerize anything re-readable from the environment; criteria travel **verbatim**, never paraphrased. |
| (omitted) the default shape | Fan-out costs ~15x a single agent. For a simple idea, orchestration is waste. | The default path is a **linear single-writer chain**. Orchestration is an escalation triggered by observed failure. |
| "Tracer bullet" | Without a number it degrades into a partial layer. | One criterion flipped, every named layer touched, **no stub at the proving seam**, and a hard tool-call budget that aborts rather than grows. |
| Immutable criteria + real learning | A contradiction the idea leaves unresolved. | **Rounds.** A run is a sequence of contracts, each written fresh and seeded by the previous round's approved output — so learning advances the run instead of editing a ratified file. Within a round, a child with new criteria handles the smaller case. |

---

## The three stages

### ARM — write a contract that is proven falsifiable

Trigger: `/redgate "<one-line idea>"`.

1. **Interview, bounded.** `grill-me` at stakes-scaled depth: at most 5
   questions, one at a time, each with a proposed default that silence accepts.
2. **Verify assumptions.** `docs-hygiene` re-checks any instruction-file claim
   the idea leans on before it becomes a contract assumption.
3. **Order the work.** `wayfinder` types criteria as dependency tickets and
   computes the dispatchable frontier.
4. **Emit two artifacts** into `.redgate/<slug>/`:
   - `CRITERIA.md` — 3–7 numbered criteria. Each carries a statement, the
     layers it crosses, and either a `check_cmd` or a declared `WITNESS`
     with a named human observation. **At least two criteria must be checkable,
     and checkable must be the majority.**
   - `check.sh` — runs every `check_cmd` under a hard timeout with stdin from
     `/dev/null`, tees each command's output to `evidence/<n>.out`, and prints
     `#n PASS|FAIL|WITNESS`.
5. **The red gate.** `check.sh` runs. It must emit a verdict line per criterion,
   and every checkable criterion must be **FAIL**. A *preflight* must come back
   clean — harness failure exits with reserved code `99` and is **not** red.
   Preflight covers **only the harness's own prerequisites**: the interpreter
   and utilities `check.sh` itself invokes (`bash`, `timeout`, `tee`, the
   evidence directory being writable). It deliberately does **not** probe the
   binaries or paths *under test* — a missing subject binary is the normal
   greenfield starting state, and probing for it would flag the very absence
   the criterion exists to measure. A `check_cmd` that exits non-zero for any
   reason, including 127, **is** a legitimate FAIL.
6. **Coupling control.** Each criterion records *why* it is red (absent vs.
   present-but-wrong) and carries a **positive control**: the same check shape
   run against a known-good target, returning PASS today. No control, no gate.
7. **Ratify.** The human approves once — shown, per criterion, the statement,
   the actual red output just produced, and one line stating what output will
   count as green. Each `WITNESS` is countersigned individually. `sha256`
   of **both** `CRITERIA.md` and `check.sh` is pinned into the run manifest.

Nothing dispatches to TRACE until both files exist, the gate is red, and
ratification is recorded.

### TRACE — one vertical slice, one writer

- **One writer.** Sequential single-writer is the default. Parallel leases exist
  only under an explicit human-enabled parallel mode.
- Take the frontier criterion crossing the most layers. `tracer-bullets` cuts
  **one** vertical slice that flips exactly that criterion id FAIL→PASS through
  every layer it names — real code path, **no stub at the seam the slice exists
  to prove**.
- `find-before-build` runs named searches before any new abstraction.
  `codebase-design` scores 3+ candidates only when the slice commits a durable
  boundary. `diagnosing-bugs` supplies ranked falsifiable hypotheses on failure.
- Subagents may fan out **read-only** — search, analysis, option generation.
  They never edit.
- `scope-fence` requires every hunk trace to a criterion id, with two escape
  hatches so the fence does not become a formality: hunks tagged
  `enabling:<id>` with a one-line justification, and an `incidental` bucket
  capped at ~10% of changed lines. Both are enumerated in the JUDGE report.
  Out-of-scope discoveries go to a run-scoped `BACKLOG.md` that survives
  context clears.
- `stop-rule` declares the bound up front, **scaled to the number of layers the
  criterion names**, with discovery and edit/verify budgeted separately. First
  exhaustion is a mandatory re-plan checkpoint, not an attempt-consuming
  failure.
- `.redgate/**` is on a global deny-list. No TRACE lease can cover it. The
  writer cannot touch the criteria or the checker.
- Re-run `check.sh` after each slice.

### JUDGE — a fresh agent runs the pinned script

`bash .redgate/<slug>/check.sh`, executed by a **fresh subagent that did not
write the code**, handed only `CRITERIA.md`, `check.sh`, and the diff — never
the build transcript.

1. Re-hash **both** `CRITERIA.md` and `check.sh` against the pinned shas.
   Either mismatch fails the run outright as drift.
2. Per criterion: `PASS` only when the command ran and its output exists at
   `evidence/<n>.out`, written by `check.sh` itself and newer than the run's
   start timestamp. A `PASS` whose evidence file is missing or stale is
   rejected. `WITNESS` only where ARM declared it.
3. **Mutation control.** Before a criterion is accepted green, revert the
   slice's core hunk and re-run that criterion; it must return to FAIL. A check
   that still passes after revert is `WITNESS`, not green — it was never
   coupled to the behavior.
4. `verify-before-claim` forbids an unrun PASS. `prove-the-undo` exercises the
   restore path before any irreversible criterion is marked green.
5. Report in `human-voice`: verdict line, per-criterion table, unmet ids, and
   one next-smallest-slice suggestion. `second-opinion` is **offered, not run**,
   when the verdict is architectural.

---

## Rounds — the horizontal axis

A run is not one contract. It is a **sequence of rounds**, each a complete
ARM/TRACE/JUDGE, with a **classified gate** sitting *between* rounds — PATCH
auto-passes, MINOR passes-and-flags, MAJOR blocks on the human (see
[Graduated autonomy](#graduated-autonomy--the-classified-round-gate)). This is where
"I have an idea to implement a Hermes agent that does xyz" actually enters the
protocol: you cannot write behavioral criteria for an idea you have not decided
how to build yet, so the first round's verifiable output is **not code — it is a
decision**.

### The round-zero rule

> Start at the first round whose criteria you can write **without already
> knowing the answer.** If you cannot write criteria for the work, write
> criteria for the **artifact that will tell you what the work is.**

"I don't know what to do yet" is not a blocker to the red gate. It selects the
round type.

| Round type | The Judged artifact | Criteria check | Who judges substance |
|---|---|---|---|
| **Orientation** | A decision brief: options, costs, a recommendation | The brief's *shape* | Human, at the round gate |
| **Plan** | An ordered slice list, each with a proposed `check_cmd` | The plan's *shape* | Human, at the round gate |
| **Build** | Working code flipping one criterion | The system's *behavior* | `check.sh`, mechanically |
| **Consolidation** | The slice widened in place | Behavior, at more inputs | `check.sh`, mechanically |

### The escalating-verifiability ladder

This is what makes early rounds honest rather than a loophole. A research round's
criteria are **structurally checkable even when its content is a judgment call**:
you do not check "is this plan good" (unverifiable, and inviting a fake
`check_cmd`), you check "does this artifact have the structure a reviewable plan
must have" — a file at a path, three options, a costs section per option, a
falsifiable recommendation. The machine checks shape; **the human checks
substance at the round gate.** The two meet exactly there.

So the ratio shifts as the problem becomes known:

```
round 1  scout         shape ■■■■■□□□□□  behavior          ← "idk what to do"
round 2  plan          shape ■■■■□□□□□□  behavior
round 3  build         shape □□□□□□■■■■  behavior          ← first real slice
round 4  consolidate   shape □□□□□□□■■■  behavior
```

A useful consequence: rounds **relieve pressure on `WITNESS`** rather than
adding to it. Without rounds, "produce a good plan" is an unverifiable criterion
and the cap gets spent immediately. With rounds, it decomposes into checkable
shape plus a human gate, and the `WITNESS` budget stays available for the
genuinely unjudgeable.

### How rounds chain

Each round's contract is written **fresh at its own ARM**, seeded by the
previous round's approved output. Nothing is edited. That is the release valve
the single-contract framing was missing:

```
round N   JUDGE → human accepts the artifact
                        ↓
round N+1 ARM → the accepted artifact is the input that makes
                  the next contract writable at all
```

The clearest case is round 2 → round 3: **an approved plan literally contains
the next round's criteria.** The plan round's job is to produce the thing that
makes the build round's contract writable.

### Rounds are not recursion

Two different axes, and conflating them is the easy mistake:

| | **Rounds** (horizontal) | **Recursion** (vertical) |
|---|---|---|
| Advances by | Human accepting a round | A slice failing at a named seam |
| Gate | Human, every time | None — automatic within a round |
| Produces | The next contract | Sub-criteria under the current one |
| Bounded by | A round budget declared at run start | `depth_remaining` + the ledger |
| Fixes | "We learned the goal was wrong" | "This criterion is too big to flip at once" |

A round can contain recursion. Recursion never crosses a round boundary.

### Round budget

The run declares a round budget up front (default: **4**). Hitting it is not
failure — it is a stop-and-report on the whole run, with what shipped, what did
not, and the next round's proposed criteria. Extending the budget is an
always-MAJOR gate — only the human funds another. This
prevents the round loop from becoming an unbounded "one more round" of the exact
kind `stop-rule` exists to stop.

---

## Worked examples

### A. "I have an idea to implement a Hermes agent that triages my inbox"

Nothing here is buildable yet — there is no decision about approach, boundaries,
or what "triage" means. Round-zero rule sends this to an **scout round**.

**Round 1 — scout.** ARM's ≤5 questions establish the one thing that
matters: the approach is undecided. `CRITERIA.md` is therefore about the brief:

```
#1  docs/hermes-triage/decision-brief.md exists
    check_cmd: test -f docs/hermes-triage/decision-brief.md
#2  It presents at least 3 candidate approaches
    check_cmd: test "$(rg -c '^## Option ' docs/hermes-triage/decision-brief.md)" -ge 3
#3  Every option carries a Costs and a "Fails if" subsection
    check_cmd: [ "$(rg -c '^### Costs')" = "$(rg -c '^## Option ')" ] && …
#4  Every option cites at least one primary source URL
    check_cmd: …one https:// inside each option block…
#5  It ends in one recommendation naming what would falsify it
    check_cmd: rg -q '^## Recommendation' && rg -q '^\*\*Falsified if:\*\*'
```

All five are **red at ARM** — the file does not exist, so every check fails
honestly, and the preflight is clean because `rg` and `test` are harness tools,
not the subject. Nothing is `WITNESS`.

TRACE is the one place the raw idea's "fan out for creativity" is exactly
right: this round's work is **reads**, so `orchestrate` fans out read-only
agents across approaches (rules engine / embedding classifier / LLM-per-message
/ hybrid), and a single writer composes the brief.

JUDGE: a fresh agent runs `check.sh` — the brief's shape is verified
mechanically. Then **you** read it and pick an option. That choice is round 2's
input, and it is an always-MAJOR gate — the scout decision steers every
round beneath it.

**Round 2 — plan.** Criteria are again shape, now on the plan: an ordered slice
list, each slice naming the layers it crosses and a *proposed* `check_cmd`, with
the first slice required to cross every layer end to end. Its JUDGE produces the
thing that makes round 3 writable.

**Round 3 — build, first tracer bullet.** Now the criteria are behavioral,
lifted from the approved plan:

```
#1  A message with subject "Invoice #42" lands in the "Bills" label
    check_cmd: pytest tests/triage/test_end_to_end.py::test_invoice_to_bills
```

One slice, every layer the plan named, no stub at the proving seam. If it fails
at a named seam — say the classifier boundary — **recursion happens inside round
3**, with no human gate, until the round's JUDGE either goes green or reports out.

**Round 4 — consolidation.** Widen the slice: more message shapes, the ambiguous
cases, the failure paths.

The whole shape: **four classified gates, four contracts, one idea** — two of
them MAJOR (scout decision, plan approval), two auto-passing as PATCH once the
mandate exists — and the human
was asked exactly four questions of consequence, each about an artifact that
already existed for them to react to.

### B. When rounds are ceremony — skip them

"Add exponential backoff to the orders client, we've already agreed on the
approach." The approach is decided, the layers are known, the criterion is
writable today:

```
#1  The client retries a 503 three times with growing delay
    check_cmd: pytest tests/test_client.py::test_backoff
```

Round-zero rule puts this straight into a **build round**. There is no
scout round and no plan round, because their outputs already exist in the
user's head and the criteria can be written without them. Inserting them would
be exactly the overhead-cosplay the adversarial critics warned about.

### C. The two axes in one run

Round 3 above, in detail:

```
round 3 ARM   contract ratified, gate red
        TRACE  slice attempted → check.sh → #1 still FAIL
                named seam: the classifier never receives the parsed subject
                ├── child a: "parser emits a subject field"      → green
                └── child b: "classifier reads the subject field" → green
        TRACE  re-run the ORIGINAL #1 check_cmd → PASS
        JUDGE     fresh agent, re-hash, mutation control → green
        ─── gate: PATCH (derived from approved plan) → auto-pass, logged ───
round 4 ARM   fresh contract, seeded by round 3's result
```

The children are automatic and invisible to you. The gate is at the round
boundary. That is the whole distinction.

---

## Where reflection lives — the stage question, settled

Should rounds gain phases like Reflect, Plan, or Investigate? Researched
against primary sources (`research/phase-structure-prior-art.md`); the
answer is **no — three stages encode falsifiability, and the variance
belongs elsewhere**. Plan and Investigate are round *types* (plan,
scout) plus in-stage actions (calibration's infer-first, mid-round
fact lookups). Reflection lives *between* rounds in every mature
verified-work loop — Deming's Act, Scrum's per-sprint-not-per-story
retrospective, Reflexion's after-episode memory — and unenforced in-cycle
phases evaporate (Beck marks refactor "optionally"; Fowler calls skipping
it TDD's most common failure). Token-matched self-inspection phases also
measurably underperform sampling (arXiv 2607.28576, 2310.01798).

So reflection gets teeth as **gate obligations**, not a fourth stage: a
mandatory one-line `lesson` field in every `gates.log` entry; a red
verdict's lesson names what the next contract must encode, and the next
round's ARM reads prior `gates.log` files first (the Reflexion
mechanism); a widen cadence — after 3 consecutive build gates, a
widen or retro round is proposed by default; and an optional
**retro round type** whose Judged artifact is the completed lessons ledger.
The driver skill carries the rules; `round-types.md` carries the retro
template.

## Recursion

Every node is the same ARM/TRACE/JUDGE.

**Spawn precondition — all four required, and demonstrated rather than claimed:**

1. The node's own tracer bullet was attempted and **failed a `check.sh` run**,
   with evidence. Budget exhaustion is *not* a seam.
2. The failure has a **named seam**.
3. ARM can write ≥2 independently checkable sub-criteria for that seam — and
   their `check.sh` **actually runs red** before the child dispatches.
4. The run-level ledger's remainder exceeds the child floor.

**Children add checks; they never replace one.** Delegation is recorded in a
separate mutable `DELEGATION.md` keyed by criterion id. `CRITERIA.md` keeps its
original `check_cmd`, and the parent criterion goes green only when **that
original command** runs and passes at JUDGE. This is what keeps a successful
recursion from tripping its own drift detector.

**Budget.** The parent reserves one child pool — 50% of its remaining budget —
that **all siblings split**, debited from a single run-scoped ledger before
every spawn. A run-level cumulative token/tool-call ceiling terminates the whole
tree, not just a node.

**Termination.** One field, `depth_remaining`, counting down from a single
number set at ARM, terminating at 0. Also terminal: no legal split, two failed
attempts, or ledger remainder below the child floor. Extension is an
always-MAJOR gate — only the human extends.
On termination `stop-rule` reports state plus ranked hypotheses.

**Harvest.** The parent's JUDGE lists every child's per-criterion table and
artifact paths verbatim, then re-runs its own original `check_cmd` for the
verdict — so a successful sibling's work is never silently lost behind a failed
one.

---

## The handoff envelope

Pointers only; no transcripts.

**DOWN:** `notes` (free text, **first**) · `criteria` (verbatim numbered lines)
· `criteria_path` + `sha` · `check_cmd` · `context[]` (≤5 `path:line`/URL
pointers) · `boundary` (1 line) · `lease[]` (globs) ·
`budget{tool_calls, attempts, tokens, depth_remaining}`

**UP:** `notes` (free text, **first**, ≤80 words) · `status` ·
`results[{id, PASS|FAIL|WITNESS, evidence_ref}]` · `artifacts[]` (paths) ·
`unmet[]` · `blocked` (≤2 lines)

Rules:
- **300-token cap applies to `notes`/`results`/`blocked` only.** Criteria text
  is excluded from the cap — capping it forces paraphrase, which is the exact
  goal drift the verbatim rule exists to prevent.
- Criteria appear **verbatim once at the tail** of the child prompt, alongside
  `criteria_path` + `sha`. A child with filesystem access re-reads the file;
  duplication at both head and tail is redundant once the path is carried.
- **Reasoning fields precede verdict fields** — constrained decoding degrades
  reasoning when the verdict is emitted first.
- `machine-voice` compresses `notes`. Criteria are never compressed.
- Evidence travels as `out_ref` paths, never as pasted command output.

---

## Graduated autonomy — the classified round gate

The round gate is no longer an unconditional human stop. Every gate decision
is **classified with `semver-gate`'s four-property test** (reversibility,
blast radius, contract change, cost to undo) and its tie-break rule, imported
verbatim: **any single property landing MAJOR makes the whole gate MAJOR.**

The governing idea: **autonomy flows downhill from an approved plan.** A
human-ratified plan is the *mandate*; rounds that execute strictly
inside it pass their gates automatically, and anything that would leave the
envelope escalates.

| Class | Gate behavior | Qualifies when |
|---|---|---|
| **PATCH** | Auto-pass. Logged to the gate ledger, folded into the round summary; the next round seeds automatically. | ALL of: build/widen round · verifier green via independent JUDGE · zero `WITNESS` · diff inside the declared fence · the round's criteria are a strict derivation of a human-approved plan slice · no escalator fired. |
| **MINOR** | Auto-pass **with a prominent flag** — called out at the moment it happens, staged separately revertible, with a standing veto. Never a blocking question. | Durable-but-revertible artifacts inside the approved direction: new files, a plan amendment that reorders approved slices, a widened consolidation. |
| **MAJOR** | **Block on a structured human question** naming the specific decision and mechanism. A prior adjacent "yes" does not transfer. | Any escalator below, or any semver-gate property landing MAJOR. |

**Always MAJOR — the escalators (never auto-passed, never softened):**

- The **scout decision** — choosing the approach steers every downstream
  round; it is a contract change for the whole run.
- The **plan round's approval** — this IS the mandate being drawn.
  No plan approval, no PATCH rounds anywhere beneath it.
- The **first ratification** of a run's contract, and any `WITNESS`
  countersignature (by definition a human observation).
- **Fence widening**, **round-budget or depth extension**, and the run's
  **final acceptance**.
- Anything `semver-gate`'s own table calls MAJOR: irreversible actions
  (`prove-the-undo` first), protection toggles, `egress-gate` transmissions
  to unnamed destinations.

**Derived ratification.** When an approved plan lists slices each carrying a
proposed verifier, a build round whose criteria are byte-derivable from its
plan slice may **auto-ratify as PATCH**, with the derivation logged. Any
deviation from the plan slice — added criteria, changed check shapes,
different layers — is a contract change and escalates to MAJOR. This is what
keeps auto-ratification from becoming self-ratification: the human approved
these exact criteria once, at plan approval, at a higher altitude.

**The gate ledger.** Every gate decision — class, the property that drove it,
and the outcome — is appended to `.redgate/<slug>/gates.log`. Auto-passed
gates are auditable after the fact; a MINOR flag carries a pointer to its
ledger line so the veto is one reference away. An auto-pass that cannot cite
its qualifying conditions is a protocol violation, not a judgment call.

**What survives from the old model.** The ≤5 interview questions keep their
silence-acceptable defaults. Ratification timeout still parks the run
(releases leases and reservations, persists state, exits resumable). `stop`
still halts at any turn. And precedence is inherited from semver-gate:
a coded deny (`autoMode` `hard_deny`/`soft_deny`, a harness permission
refusal) always wins over this classification, a coded allow is permission to
run a tool and never consent at a gate (landing on `main` and destructive
steps still stop for their own confirmation), and the system prompt's care
principle is the ground truth the table serves.

---

## Skill map

| Stage | Skill | Role |
|---|---|---|
| ARM | `grill-me` | Bounded 5-question interview turns a one-line idea into falsifiable criteria |
| ARM | `docs-hygiene` | Re-verifies instruction-file claims before they become contract assumptions |
| ARM | `wayfinder` | Types criteria as dependency tickets; computes the dispatchable frontier |
| ARM | `fleet-playbook-curator` | Optional — when the idea's context spans multiple repos |
| TRACE | `tracer-bullets` | Defines the one-criterion vertical slice; forbids stubbing the proving seam |
| TRACE | `find-before-build` | Named searches for an existing equivalent before any new abstraction |
| TRACE | `codebase-design` | 3+ scored candidates when the slice commits a durable boundary |
| TRACE | `diagnosing-bugs` | Ranked falsifiable hypotheses when a slice fails to flip its criterion |
| TRACE | `orchestrate` | Read-only fan-out template with frozen context and adversarial verifiers |
| TRACE | `plugin-factory`, `tailscale-wif`, `graveyard` | Domain executors, invoked only when a criterion names them |
| JUDGE | `verify-before-claim` | The verdict is `check.sh` output, run — never asserted |
| JUDGE | `prove-the-undo` | Restore path exercised before any irreversible criterion goes green |
| JUDGE | `second-opinion` | Offered, not forced, on architectural or confidence-flagged verdicts |
| JUDGE | `dev-diary`, `dev-diary-review` | Post-run capture of the slice and its unmet criteria |
| CROSS | `scope-fence` | Every hunk traces to a criterion id; discoveries recorded, never folded in |
| CROSS | `stop-rule` | Declares the attempt bound whose exhaustion forces a re-plan checkpoint |
| CROSS | `semver-gate` | Per-action autonomy lookup; MAJOR breaks the autonomous run and asks |
| CROSS | `context-handoff` | Pointer-only continue/clear/delegate decision at every node boundary |
| CROSS | `egress-gate` | Enumerates what leaves the machine before any transmitting `check_cmd` |
| CROSS | `machine-voice` / `human-voice` | Envelope compression; verdict-first prose at the three gates |

---

## Corrections applied after adversarial review

Two critics (a cost/safety lens and a will-it-actually-be-followed lens)
returned 27 findings. Five were fatal — two of them found independently by both
critics, which is the strongest signal available here that they are real. Every
fatal fix is already folded into the stages above; they are recorded separately
because a future edit that quietly undoes one of them would reopen a known hole.

| # | Fatal flaw | Fix now in the spec |
|---|---|---|
| 1 | Only `CRITERIA.md` was sha-pinned. `check.sh` lives in the repo and the TRACE writer could edit it — rewriting a curl assertion to `echo '#3 PASS'` produces a green run. *(Found by both critics.)* | Pin `check.sh` too; re-hash both at JUDGE; `.redgate/**` on a deny-list no lease can cover. |
| 2 | Recursion rewrote the parent criterion's `check_cmd` to "all child checks green" — mutating the sha-pinned file, so **every successful recursion self-destructed** on the drift check. *(Found by both critics.)* | Delegation moves to a mutable `DELEGATION.md`; `CRITERIA.md` keeps the original command; the parent re-runs *that* for its verdict. |
| 3 | "A crash is not red" deadlocked greenfield work: `foo --version` on an unbuilt CLI exits 127, so the gate could never go red and TRACE never dispatched. | "Not red" now means only *harness* failure (no verdict line emitted, reserved exit 99, or a dirty preflight — where preflight covers only the harness's own prerequisites, never the binaries under test). A `check_cmd` exiting non-zero — 127 included — is a legitimate FAIL. |
| 4 | Red proved a check *currently fails*, not that it is **coupled** to the criterion. `grep -q RETRY src/client.go` goes green when a comment containing RETRY is added. | Positive control at ARM + **mutation control** at JUDGE: revert the core hunk, re-run; a check that still passes is `WITNESS`, not green. |
| 5 | Budget halved per child but not across siblings, with no global ledger — four criteria spawning two children each consumed 4x the root cap while every local rule reported compliance. | One child pool per parent split by all siblings, debited from a single run-scoped ledger, under a run-level ceiling that terminates the whole tree. |

Notable non-fatal corrections also folded in: the 300-token cap excluded
criteria text (it was arithmetically incompatible with carrying 7 criteria
verbatim twice, and the model would have resolved the conflict by paraphrasing);
`scope-fence` given `enabling:`/`incidental` buckets so real slices can register
a route without laundering a false trace; per-check timeouts and non-interactive
stdin so a credential prompt cannot hang the gate forever; `stop-rule` bounds
scaled to layer count with discovery budgeted separately, so decomposition is
triggered by an observed seam rather than by ritual exhaustion; a single
`depth_remaining` field replacing three contradictory depth numbers; and
ratification presenting observable behavior rather than seven `bash -c`
one-liners a human will rubber-stamp.

---

## The operating loop — self-learning and growing

Zoom out and Red Gate is not a workflow; it is the **process model of an
agentic operating system**, and this marketplace is that system's disk. The
parts map directly:

| OS concept | In this system |
|---|---|
| Process | A round (one ARM/TRACE/JUDGE) |
| Kernel loop | The round chain: accept → seed → next contract |
| Scheduler | `wayfinder`'s dependency frontier |
| Syscall gates | `semver-gate` (privilege), `egress-gate` (network) |
| Resource limits | The spend ledger, `depth_remaining`, `stop-rule` bounds |
| Programs | Skills — single-invariant, composable |
| Package manager | The marketplace itself (`/plugin install <name>@jrichlen`) |
| Episodic memory | `dev-diary` — what happened, what mattered, why |
| Semantic index | `fleet-playbook-curator` — a living map that cites sources |
| Memory consistency | `docs-hygiene` — stale claims caught before trusted |
| Process genesis | `plugin-factory` — new programs start valid, wired, RED |
| Immune system | The three eval tiers gating every program change |

### The growth loop

"Self-learning" is not a property a prompt can grant; it is a **pipeline the
exhaust of every run flows through**. Each round already emits learning
exhaust as a side effect of the discipline: `stop-rule` reports with ranked
hypotheses, `scope-fence` findings in `BACKLOG.md`, unmet criteria at round
gates, `dev-diary` entries. The growth loop is what turns that exhaust into
new capability:

```
1. EMIT        every run: stop-reports, findings, unmet criteria, diary entries
2. CONSOLIDATE dev-diary (episodic) + fleet-playbook-curator (semantic)
3. DETECT      the same failure shape or manual ritual recurring across runs
                → a candidate skill, named as an invariant
4. SCAFFOLD    plugin-factory: valid, wired, RED by default
5. GATE        cheap tier (shape) → behavioral tier with calibration
                (does the skill beat the bare model?) → deep tier if safety
6. LOAD        merged = the OS grew a new program; every later run composes it
```

Step 5 is what separates growing from accreting. A candidate skill that cannot
beat its calibration stub is the system trying to memorize noise — the
behavioral tier's negative controls exist precisely to reject it (this repo
has already done so: verify-before-claim's pack documents six scenarios,
six rejections). Growth is **eval-gated**, so the skill set compounds only
where a measured invariant earned its slot.

This document is itself one turn of the loop: the 12-agent run that produced
it emitted the "10 skills the marketplace still lacks" list below — detected
gaps, named as invariants, waiting at step 4.

### Where the loop is not yet closed

Steps 1, 2, 4, 5, 6 exist today as shipped plugins and CI. Step 3 —
**recurrence detection across runs** — is the missing organ: nothing today
reads a month of diary entries and stop-reports and says "this failure shape
has now appeared four times; here is the invariant that would prevent it."
Until it exists, the human is the detector, which is a fine bootstrap and a
real bottleneck. It belongs on the gap list as much as anything there.

---

## What the marketplace still lacks

Red Gate is a protocol, not yet an implementation. These are the skills it would
need — ordered by whether the protocol can run at all without them.

**Blocking:**
- **`criteria-contract`** — writes `CRITERIA.md` + `check.sh` from an
  interviewed idea and enforces the red gate. Nothing produces the ARM
  artifact today.
- **`reconcile`** — re-hashes, runs `check.sh` from a fresh context, scores
  criterion-by-criterion with evidence pointers and the mutation control.
- **`redgate-driver`** — the entry-point command that runs ARM→TRACE→JUDGE and
  blocks each transition on its exit condition. `orchestrate` is fan-out
  templates only; `wayfinder` never executes.

**Structural:**
- **`recursion-contract`** — the four-part spawn precondition, budget pooling,
  termination report.
- **`handoff-envelope`** — the typed parent↔child schema as a reusable skill
  rather than per-template JSON inside `orchestrate`.
- **`spend-ledger`** — cumulative tokens/tool-calls across the whole recursion.
- **`harvest`** — deterministic sibling reducer with a dedupe rule.
- **`recurrence-detector`** — reads accumulated diary entries, stop-reports,
  and findings across runs; surfaces failure shapes seen ≥N times as candidate
  invariants for `plugin-factory`. The missing organ that closes the growth
  loop.

**Refinement:**
- **`fanout-budget`** — how many divergent read-only subagents, justified
  against a single linear agent.
- **`escalate`** — child→parent return-and-renegotiate vs. abort vs. re-split.
- **`lease`** — file-glob arbitration for the optional parallel mode.

---

## Research grounding

The design is built on surveyed patterns rather than invented from scratch. The
load-bearing ones:

- **Orchestrator-worker** (Anthropic, *How we built our multi-agent research
  system*) — subagents as compression filters returning distilled results, not
  raw traces. Also the source of the ~15x token-cost figure that makes linear
  the default here.
- **Task-description contract** (same) — objective / output format / tools /
  boundary. This *is* the ARM stage rendered as a message payload.
- **Anthropic's workflow taxonomy** (*Building Effective Agents*) — prompt
  chaining, routing, parallelization, orchestrator-workers, evaluator-optimizer;
  and its own guidance to prefer the simplest pattern that works.
- **Plan-and-execute** (LangChain) — plan once with a strong model, execute with
  cheaper ones, replan only when a result invalidates the plan.
- **ReAct** (Yao et al., arXiv:2210.03629) — the inner loop of any TRACE slice.
- **Reflexion** (Shinn et al., NeurIPS 2023) — a failed JUDGE emits a critique
  that re-enters ARM, making the process a loop rather than one-shot.
- **HTN decomposition** (arXiv:2511.12901) — the formal justification for
  self-similarity: a node is primitive or compound, and the verifier at each
  level is what keeps recursion sound.
- **Blackboard architecture** (arXiv:2510.01285) — pointers into shared state
  instead of replayed transcripts.
- **Contract-net** (Smith 1980; *Agent Contracts*, arXiv:2601.08815) — success
  criteria plus a budget as an explicit, lifecycle-tracked contract.
- **ADaPT** — as-needed decomposition beats eager planning; the source of the
  lazy-recursion refinement.
- **Huang et al., ICLR 2024** — LLMs cannot reliably self-correct without
  external feedback; the source of the fresh-checker requirement.

---

## Glossary and calibration

The canonical vocabulary — every load-bearing term, the collision rulings
(Calibration vs negative control, stage vs `phase`, verifier harness vs
agent harness), and the run lifecycle verbs — lives at
[`red-gate-glossary.md`](red-gate-glossary.md). The run-sizing layer that
precedes every ARM — five dials (tier, domain, scope, taste,
orchestration), the T0 decline, and the recalibration rules — is specified
in the redgate plugin at
[`../plugins/redgate/skills/redgate/references/calibration.md`](../plugins/redgate/skills/redgate/references/calibration.md).

## Pattern corpus

A full corpus of the agentic patterns AI leaders are using — 88 unique
patterns from 90 scout sightings, every one kept, deep-dive-verified against
primary sources, with a ranked adoption roadmap — lives at
[`research/agentic-patterns-corpus.md`](research/agentic-patterns-corpus.md)
(machine-readable: [`research/agentic-patterns-corpus.json`](research/agentic-patterns-corpus.json)).
Its verdict: Red Gate's invariants live in prose the model is asked to honor,
while the field has moved the same invariants into code — hooks, tool classes,
pinned constraint blocks. The protocol should compile.

## Implementation plan

The plan-round artifact for building this protocol — the concrete file tree
(two new plugins, three amendments), five build slices each with a proposed
verifier, and the CI cost sequencing — is
[`red-gate-implementation-plan.md`](red-gate-implementation-plan.md).

## Interactive map

An interactive representation of this protocol — the red-gate simulator, all 24
skills filterable by stage, the refinement table, and the fatal ledger — is
published as an artifact and its source lives at
[`docs/assets/red-gate.html`](assets/red-gate.html).
