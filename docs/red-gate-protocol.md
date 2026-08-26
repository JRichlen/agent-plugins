# Red Gate — a recursive BEGIN/MIDDLE/END protocol for skill coordination

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

**One line:** turn a one-line idea into a red-by-default `check.sh`, flip one
criterion green with a real vertical slice, then let a fresh agent run the script.

---

## The problem this solves

The marketplace has 24 skills across 21 plugins. Each is a single-invariant
discipline that works alone. Nothing composes them — there is no answer to
"I have an idea, now run the right skills in the right order and prove you
finished." Red Gate is that answer: a self-similar three-stage process where
BEGIN writes a falsifiable contract, MIDDLE cuts one tracer-bullet slice, and
END is a fresh agent executing the contract.

## The invariant

> No MIDDLE work begins until a `check.sh` exists that **executes and returns
> FAIL on every checkable criterion**. No criterion is ever marked green except
> by a fresh agent running that same pinned script and producing evidence on
> disk. Criteria are ratified once and never edited — a wrong contract is
> corrected by spawning a child with new criteria, never by rewriting the
> ratified one.

Criteria that cannot go red are not criteria. That is the whole design in one
sentence.

---

## Why "the criteria are defined up front" was not enough

The raw idea said BEGIN should define the verifiable output criteria. Research
and adversarial review both say that is too weak, in five specific ways. These
are the **refinements** — the places the original idea needed correcting, not
merely implementing.

| The original idea | Why it fails | The refinement |
|---|---|---|
| BEGIN "defines verifiable criteria" | Criteria written but never executed are self-report. A model writes criteria it already believes it meets. | **The red gate.** `check.sh` must run and come back FAIL on every checkable criterion before MIDDLE starts. |
| Every output is verifiable | Taste, prose, and exploration are not command-checkable. A hard red gate incentivizes *fake* `check_cmd`s written purely to clear it. | A declared **`UNVERIFIABLE`** verdict, capped and individually human-countersigned at BEGIN — never an END downgrade of a red check. |
| END is "checked against BEGIN's criteria" | Omits *who* checks. LLMs are poor at autonomous error detection (Huang et al., ICLR 2024); the common failure is silently rewriting criteria to match what was built. | A **fresh agent** that did not write the code, handed only the criteria, the script, and the diff — plus sha-pinning so drift is detected mechanically. |
| "Subagents fan out for creativity" | Conflates reading with writing. Concurrent writers on shared code produce conflicting assumptions (Cognition's single-writer principle; Anthropic's own caveat that orchestrator-worker misfires on code editing). | **Fan out reads, funnel writes.** Fan-out is for search, analysis, and option generation. Exactly one writer per run by default. |
| An agent's output "can be a plan that breaks the problem into more subagents" | Implies *eager* decomposition. ADaPT shows the opposite ordering wins; an eager tree propagates a wrong top-level split through everything beneath it. | **Lazy recursion.** Attempt the slice first; decompose only at an observed, named failure with demonstrated sub-criteria. |
| "Self-similar/recursive" | Self-similarity is a shape, not a termination rule. Unbounded self-similarity is unbounded cost. | A four-part **spawn precondition** plus numeric depth/budget backstops. |
| "Handoffs must be token-efficient" | Half right, half dangerous. Compressing the *criteria* is goal drift. | Pointerize anything re-readable from the environment; criteria travel **verbatim**, never paraphrased. |
| (omitted) the default shape | Fan-out costs ~15x a single agent. For a simple idea, orchestration is waste. | The default path is a **linear single-writer chain**. Orchestration is an escalation triggered by observed failure. |
| "Tracer bullet" | Without a number it degrades into a partial layer. | One criterion flipped, every named layer touched, **no stub at the proving seam**, and a hard tool-call budget that aborts rather than grows. |
| Immutable criteria + real learning | A contradiction the idea leaves unresolved. | Legitimate mid-flight learning enters as a **child with new criteria**, keeping drift detectable without a human unblocking every correction. |

---

## The three stages

### BEGIN — write a contract that is proven falsifiable

Trigger: `/redgate "<one-line idea>"`.

1. **Interview, bounded.** `grill-me` at stakes-scaled depth: at most 5
   questions, one at a time, each with a proposed default that silence accepts.
2. **Verify assumptions.** `docs-hygiene` re-checks any instruction-file claim
   the idea leans on before it becomes a contract assumption.
3. **Order the work.** `wayfinder` types criteria as dependency tickets and
   computes the dispatchable frontier.
4. **Emit two artifacts** into `.redgate/<slug>/`:
   - `CRITERIA.md` — 3–7 numbered criteria. Each carries a statement, the
     layers it crosses, and either a `check_cmd` or a declared `UNVERIFIABLE`
     with a named human observation. **At least two criteria must be checkable,
     and checkable must be the majority.**
   - `check.sh` — runs every `check_cmd` under a hard timeout with stdin from
     `/dev/null`, tees each command's output to `evidence/<n>.out`, and prints
     `#n PASS|FAIL|UNVERIFIABLE`.
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
   count as green. Each `UNVERIFIABLE` is countersigned individually. `sha256`
   of **both** `CRITERIA.md` and `check.sh` is pinned into the run manifest.

Nothing dispatches to MIDDLE until both files exist, the gate is red, and
ratification is recorded.

### MIDDLE — one vertical slice, one writer

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
  capped at ~10% of changed lines. Both are enumerated in the END report.
  Out-of-scope discoveries go to a run-scoped `BACKLOG.md` that survives
  context clears.
- `stop-rule` declares the bound up front, **scaled to the number of layers the
  criterion names**, with discovery and edit/verify budgeted separately. First
  exhaustion is a mandatory re-plan checkpoint, not an attempt-consuming
  failure.
- `.redgate/**` is on a global deny-list. No MIDDLE lease can cover it. The
  writer cannot touch the criteria or the checker.
- Re-run `check.sh` after each slice.

### END — a fresh agent runs the pinned script

`bash .redgate/<slug>/check.sh`, executed by a **fresh subagent that did not
write the code**, handed only `CRITERIA.md`, `check.sh`, and the diff — never
the build transcript.

1. Re-hash **both** `CRITERIA.md` and `check.sh` against the pinned shas.
   Either mismatch fails the run outright as drift.
2. Per criterion: `PASS` only when the command ran and its output exists at
   `evidence/<n>.out`, written by `check.sh` itself and newer than the run's
   start timestamp. A `PASS` whose evidence file is missing or stale is
   rejected. `UNVERIFIABLE` only where BEGIN declared it.
3. **Mutation control.** Before a criterion is accepted green, revert the
   slice's core hunk and re-run that criterion; it must return to FAIL. A check
   that still passes after revert is `UNVERIFIABLE`, not green — it was never
   coupled to the behavior.
4. `verify-before-claim` forbids an unrun PASS. `prove-the-undo` exercises the
   restore path before any irreversible criterion is marked green.
5. Report in `human-voice`: verdict line, per-criterion table, unmet ids, and
   one next-smallest-slice suggestion. `second-opinion` is **offered, not run**,
   when the verdict is architectural.

---

## Recursion

Every node is the same BEGIN/MIDDLE/END.

**Spawn precondition — all four required, and demonstrated rather than claimed:**

1. The node's own tracer bullet was attempted and **failed a `check.sh` run**,
   with evidence. Budget exhaustion is *not* a seam.
2. The failure has a **named seam**.
3. BEGIN can write ≥2 independently checkable sub-criteria for that seam — and
   their `check.sh` **actually runs red** before the child dispatches.
4. The run-level ledger's remainder exceeds the child floor.

**Children add checks; they never replace one.** Delegation is recorded in a
separate mutable `DELEGATION.md` keyed by criterion id. `CRITERIA.md` keeps its
original `check_cmd`, and the parent criterion goes green only when **that
original command** runs and passes at END. This is what keeps a successful
recursion from tripping its own drift detector.

**Budget.** The parent reserves one child pool — 50% of its remaining budget —
that **all siblings split**, debited from a single run-scoped ledger before
every spawn. A run-level cumulative token/tool-call ceiling terminates the whole
tree, not just a node.

**Termination.** One field, `depth_remaining`, counting down from a single
number set at BEGIN, terminating at 0. Also terminal: no legal split, two failed
attempts, or ledger remainder below the child floor. Only the human extends.
On termination `stop-rule` reports state plus ranked hypotheses.

**Harvest.** The parent's END lists every child's per-criterion table and
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
`results[{id, PASS|FAIL|UNVERIFIABLE, evidence_ref}]` · `artifacts[]` (paths) ·
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

## Where the human is

Three touchpoints, and only one is blocking:

1. The ≤5 BEGIN interview questions, each with a silence-acceptable default.
2. **Ratification** of `CRITERIA.md` after the red gate proves it falsifiable —
   the only mandatory approval. On ratification timeout the run releases its
   leases and ledger reservation, persists state, and exits **PARKED** and
   resumable rather than blocking overnight.
3. The END verdict: accept / again / split.

Between gates it runs autonomously. It breaks out only for `semver-gate` MAJOR
actions, `egress-gate` transmissions, or a depth/attempt cap breach. `stop`
halts at any turn.

---

## Skill map

| Stage | Skill | Role |
|---|---|---|
| BEGIN | `grill-me` | Bounded 5-question interview turns a one-line idea into falsifiable criteria |
| BEGIN | `docs-hygiene` | Re-verifies instruction-file claims before they become contract assumptions |
| BEGIN | `wayfinder` | Types criteria as dependency tickets; computes the dispatchable frontier |
| BEGIN | `fleet-playbook-curator` | Optional — when the idea's context spans multiple repos |
| MIDDLE | `tracer-bullets` | Defines the one-criterion vertical slice; forbids stubbing the proving seam |
| MIDDLE | `find-before-build` | Named searches for an existing equivalent before any new abstraction |
| MIDDLE | `codebase-design` | 3+ scored candidates when the slice commits a durable boundary |
| MIDDLE | `diagnosing-bugs` | Ranked falsifiable hypotheses when a slice fails to flip its criterion |
| MIDDLE | `orchestrate` | Read-only fan-out template with frozen context and adversarial verifiers |
| MIDDLE | `plugin-factory`, `tailscale-wif`, `graveyard` | Domain executors, invoked only when a criterion names them |
| END | `verify-before-claim` | The verdict is `check.sh` output, run — never asserted |
| END | `prove-the-undo` | Restore path exercised before any irreversible criterion goes green |
| END | `second-opinion` | Offered, not forced, on architectural or confidence-flagged verdicts |
| END | `dev-diary`, `dev-diary-review` | Post-run capture of the slice and its unmet criteria |
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
| 1 | Only `CRITERIA.md` was sha-pinned. `check.sh` lives in the repo and the MIDDLE writer could edit it — rewriting a curl assertion to `echo '#3 PASS'` produces a green run. *(Found by both critics.)* | Pin `check.sh` too; re-hash both at END; `.redgate/**` on a deny-list no lease can cover. |
| 2 | Recursion rewrote the parent criterion's `check_cmd` to "all child checks green" — mutating the sha-pinned file, so **every successful recursion self-destructed** on the drift check. *(Found by both critics.)* | Delegation moves to a mutable `DELEGATION.md`; `CRITERIA.md` keeps the original command; the parent re-runs *that* for its verdict. |
| 3 | "A crash is not red" deadlocked greenfield work: `foo --version` on an unbuilt CLI exits 127, so the gate could never go red and MIDDLE never dispatched. | "Not red" now means only *harness* failure (no verdict line emitted, reserved exit 99, or a dirty preflight — where preflight covers only the harness's own prerequisites, never the binaries under test). A `check_cmd` exiting non-zero — 127 included — is a legitimate FAIL. |
| 4 | Red proved a check *currently fails*, not that it is **coupled** to the criterion. `grep -q RETRY src/client.go` goes green when a comment containing RETRY is added. | Positive control at BEGIN + **mutation control** at END: revert the core hunk, re-run; a check that still passes is `UNVERIFIABLE`, not green. |
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

## What the marketplace still lacks

Red Gate is a protocol, not yet an implementation. These are the skills it would
need — ordered by whether the protocol can run at all without them.

**Blocking:**
- **`criteria-contract`** — writes `CRITERIA.md` + `check.sh` from an
  interviewed idea and enforces the red gate. Nothing produces the BEGIN
  artifact today.
- **`reconcile`** — re-hashes, runs `check.sh` from a fresh context, scores
  criterion-by-criterion with evidence pointers and the mutation control.
- **`redgate-driver`** — the entry-point command that runs BEGIN→MIDDLE→END and
  blocks each transition on its exit condition. `orchestrate` is fan-out
  templates only; `wayfinder` never executes.

**Structural:**
- **`recursion-contract`** — the four-part spawn precondition, budget pooling,
  termination report.
- **`handoff-envelope`** — the typed parent↔child schema as a reusable skill
  rather than per-template JSON inside `orchestrate`.
- **`spend-ledger`** — cumulative tokens/tool-calls across the whole recursion.
- **`harvest`** — deterministic sibling reducer with a dedupe rule.

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
  boundary. This *is* the BEGIN stage rendered as a message payload.
- **Anthropic's workflow taxonomy** (*Building Effective Agents*) — prompt
  chaining, routing, parallelization, orchestrator-workers, evaluator-optimizer;
  and its own guidance to prefer the simplest pattern that works.
- **Plan-and-execute** (LangChain) — plan once with a strong model, execute with
  cheaper ones, replan only when a result invalidates the plan.
- **ReAct** (Yao et al., arXiv:2210.03629) — the inner loop of any MIDDLE slice.
- **Reflexion** (Shinn et al., NeurIPS 2023) — a failed END emits a critique
  that re-enters BEGIN, making the process a loop rather than one-shot.
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

## Interactive map

An interactive representation of this protocol — the red-gate simulator, all 24
skills filterable by stage, the refinement table, and the fatal ledger — is
published as an artifact and its source lives at
[`docs/assets/red-gate.html`](assets/red-gate.html).
