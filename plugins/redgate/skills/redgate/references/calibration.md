# Calibration — sizing the run before it starts

Calibration is ARM **step 0**: before any criteria are written, five dials
are set that decide how much protocol this task deserves, which skills load,
and where the autonomy floors sit. It is the anti-ceremony mechanism — the
protocol's answer to "is this overly complex?" is that a calibrated run
carries exactly the weight its risk earns, and a task below the threshold is
declined by the protocol itself.

## The prompting contract

Calibration is **dynamic prompting under a budget**, not a questionnaire.
The questioning posture is `grill-me`'s, inherited via the
criteria-contract interview: infer first, then use the harness's interactive
ask-question tool for one decision at a time, with a stated recommendation
and tap-ready options. Never dump a prose question list. Silence may accept a
non-gate inferred default; it never accepts a MAJOR gate.
The dependency runs one way — calibration adopts grill-me's posture and its
stakes math (grill-me's per-branch stakes tier, reversibility × blast
radius, is the same computation as the scope and tier escalators below);
grill-me stays generic and knows nothing about these dials.

- **Infer first.** Read the idea, the repo, and the conversation; propose a
  value for every dial. Each value is labeled **stated** (the human said it)
  or **inferred** (with a one-line basis: "inferred — diff would touch only
  `docs/`").
- **Ask only load-bearing unknowns.** A dial earns a question only when the
  inference is genuinely uncertain AND the dials it feeds would change
  behavior. Calibration questions and criteria questions share the same
  interview budget: **≤5 questions total**, one interactive tool call at a
  time by default. Offer 2-3 options with the recommendation first, use
  multi-select only for independent choices, and use a compact confirmation
  for binary gates. Free text is a last resort and must be one bounded prompt.
- **Record where the pin already reaches.** The calibration block is written
  into the header comment of `CRITERIA.md`, above criterion #1. Ratifying
  the contract ratifies the calibration; pinning the contract pins it. No
  new file, no script change, drift protection for free.

Header shape:

```
<!-- CALIBRATION
  tier:          T2 (inferred — multi-file change, verifier writable today)
  domain:        code (stated)
  scope:         plugins/redgate/** only; no external effects (inferred)
  taste:         match-repo (inferred — no style ask in the prompt)
  orchestration: independent-JUDGE (inferred — no parallelism need named)
  Silence at ratification accepts every inferred value above. -->
```

## The five dials

### 1. Tier — how much protocol

| Tier | Meaning | Protocol weight |
|---|---|---|
| **T0 — direct** | An answer, a lookup, a one-file reversible edit whose correctness is obvious on sight | **No run.** The protocol declines to fire; do the thing. Opening a run dir for a T0 task is a calibration error, not diligence. |
| **T1 — tracer** | One criterion, one slice, writable today | One build round; interview may be zero questions. |
| **T2 — run** | Several criteria, one coherent goal | A run of rounds under one budget; the default when `/redgate` fires. |
| **T3 — program** | The goal needs a plan round to even enumerate slices | Scout and/or plan round first; the approved plan becomes the mandate. |

Tier escalators: any irreversible action or external transmission bumps the
floor to ≥T2 regardless of size — the round exists to hold the gate, not the
code.

### 2. Domain — what kind of verifier

| Domain | Verifier rung (see `round-types.md`) | Notes |
|---|---|---|
| **code** | behavior checks — exit codes on passing fixtures | The default ladder top. |
| **research** | shape checks on the brief — sources cited, claims tagged, question answered | Substance judged by the human at the gate. |
| **writing/docs** | shape checks + at most 1 WITNESS for voice | Taste lives in the WITNESS budget, never in a fake `check_cmd`. |
| **ops/config** | behavior checks where probeable; `prove-the-undo` before anything irreversible | Reversibility evidence is part of the contract. |
| **design** | rubric-scored review as the verifier — all four verifier properties still required | The rubric is pinned like any checker. |

Mixed-domain tasks calibrate to the **riskiest** domain present, not the
largest.

### 3. Scope — the fence and the blast radius

State the fence as paths (`scope-fence`) plus a blast-radius class:

- **file / module / repo** — sets the fence; every hunk traces to a criterion.
- **external** (network sends, published artifacts, third-party state) —
  loads `egress-gate`; destination named per criterion or the gate is MAJOR.
- **irreversible** (deletes, protection toggles, history rewrites) — loads
  `prove-the-undo`; the gate floor is MAJOR, always.

Scope may **narrow** mid-run with a `gates.log` note. Widening is the
fence-widening escalator: MAJOR, no exceptions.

### 4. Taste — the quality bar

| Bar | What JUDGE demands beyond green |
|---|---|
| **prototype** | Verifier green. Nothing else; polish criteria are scope creep. |
| **match-repo** | Green + the diff reads like the surrounding code (naming, comment density, idiom). Default. |
| **production** | Green + mutation control on the core hunk + eval-tier coverage for anything an eval tier guards in this repo. |

Taste is the dial most often *inferred wrong* — over-polishing a prototype
and under-proving production are the same calibration failure in opposite
directions. When the bar is ambiguous and the answer changes the work, it is
worth one of the five questions.

### 5. Orchestration — the minimum that satisfies the need

Pick the **lowest** level that meets the round's actual independence and
parallelism needs. Orchestration is a cost, never a signal of seriousness.

| Level | When it is earned |
|---|---|
| **solo** | T0–T1 where the human will grade JUDGE themselves. |
| **independent-JUDGE** | The default: one writer; only JUDGE runs in a fresh context. |
| **fan-out** | TRACE needs parallel **read-only** research (orchestrate templates); still one writer. |
| **recursive** | Only via the four-part spawn precondition, inside a round, within `depth_remaining`. Never chosen at calibration time — recursion is earned by a failed check, not planned in advance. |

Escalating one level mid-run is a MINOR gate (flagged, standing veto);
jumping levels or touching recursion budgets is MAJOR.

PORTABILITY: subagents are a Claude-Code convenience, not a dependency —
the discipline is harness-agnostic. On another harness, independent-JUDGE is
a fresh session or the human, and fan-out is parallel sessions or serial
read-only passes; the levels and their escalation rules are unchanged.

## Recalibration

The calibration block is pinned, so it is never edited. Reality disagreeing
with a dial is handled like any contract error:

- **Narrowing** (smaller scope, lower tier, lower orchestration) — note in
  `gates.log`, carry on; the next round's contract records the new value.
- **Widening** (bigger scope, higher tier, external effects discovered,
  production bar revealed) — stop at the gate as MAJOR. The question names
  the dial, the old value, the new value, and what forced it.

## Failure modes this exists to stop

- **Ceremony creep** — running a four-round protocol on a T0 rename because
  the tool exists. The T0 decline is a feature; use it.
- **Taste smuggling** — an uncalibrated "production" bar appearing at JUDGE as
  surprise rejections, or a prototype gold-plated against no stated need.
- **Orchestration theater** — subagents fanned out because they are
  available, not because the round needs them.
- **Silent scope drift** — external effects discovered mid-TRACE and
  handled inline instead of stopping the gate.
- **Un-owned inference** — a dial acted on without being written down and
  shown at ratification; an inferred value the human never saw is not a
  default, it is a guess.
