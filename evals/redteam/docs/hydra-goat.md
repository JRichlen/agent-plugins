# Hosted Hydra / GOAT — a separate, approval-gated path

Design: `agent-plugins-promptfoo-redteam.md` §12. Config:
[`../configs/hosted/hydra-goat.yaml`](../configs/hosted/hydra-goat.yaml).

## What this is

Promptfoo 0.122.0 ships several **multi-turn** red-team strategies —
`goat`, `mischievous-user`, `crescendo`, `custom`, `jailbreak:hydra`,
`jailbreak:goblin` (`dist/src/tables-CdYHKM_u.js`'s `MULTI_TURN_STRATEGIES`).
They generate each attack turn adaptively, in response to the target's prior
reply, by calling out to promptfoo's own **remote task API**
(`https://api.promptfoo.app/api/v1/task`, via `getRemoteGenerationUrl()`).

That is a fundamentally different shape from everything else in this lane:

| | frozen 2×2 corpus (T44/T46) | hosted Hydra/GOAT |
|---|---|---|
| attack turns | fixed, committed, sha256-hashed | generated per run, per turn |
| network | none, ever | one external call per turn, to promptfoo's own cloud |
| cost | free | billed (a hosted generation call per turn) |
| comparable across runs | yes — same corpus every time | **no** — a fresh generation each run |
| what leaves the machine | nothing | prompts, including a plugin's `SKILL.md` text |

## Why it cannot run offline even by accident

`generateMultiTurnPrompt()` (`main.js:13121`) calls `neverGenerateRemote()`
*first*. Under this lane's offline environment
(`PROMPTFOO_DISABLE_REMOTE_GENERATION=1` and
`PROMPTFOO_DISABLE_REDTEAM_REMOTE_GENERATION=1`, README.md / design §10.2),
that check is true and the function **throws** before any turn is produced.
There is no silent local fallback, no degraded-but-working mode: a hosted
strategy under `--offline` is a hard failure, not a quieter version of the
same attack. `evals/redteam/run.sh --offline` never reads anything under
`configs/hosted/` in the first place, so this is defense in depth on top of
a runner that would never reach the file at all.

## How this lane keeps it quarantined

- `run.sh` never globs or validates `configs/hosted/**` in its offline
  pass (the config-validation loop explicitly prunes that directory).
- `run.sh --hosted` requires `--approve-token <T>`, the same authority T25's
  native-adapter spawn requires, and **this delivery has no approved
  execution path wired even with a token** — it refuses unconditionally,
  the same posture as `--paid`.
- Results from a hosted run, if one is ever approved and executed, land
  under a separate `.artifacts/hosted/` tree with `corpus_frozen: false` in
  their manifest. `bin/verdict.py` never merges hosted-strategy rows into a
  frozen-corpus cell (C1–C6) — pooling an unfrozen, per-run-generated attack
  set with the frozen 2×2 would make every comparison across runs
  meaningless, and would let a "fix" be nothing more than a different reroll.
- Both `PROMPTFOO_DISABLE_REMOTE_GENERATION` and
  `PROMPTFOO_DISABLE_REDTEAM_REMOTE_GENERATION` must be **unset** for a
  hosted run even to attempt generation, and the approval token must be
  present — two independent gates, not one.

## Data-egress note

A hosted turn's prompt includes whatever the transcript carries at that
point in the conversation — for a treatment-arm run, that is the plugin's
real `SKILL.md` text. Approving a hosted run means that text leaves the
machine as part of the request to promptfoo's remote task API. This is
disclosed here so an approval decision is made with that fact in view, not
discovered after the fact in a bill or a log.

## `configs/hosted/hydra-goat.yaml`

Exists so the option is **schema-valid and reviewable** — `promptfoo
validate` accepts it under the pinned 0.122.0 build — without being
runnable from any default path. Its `providers:` entry is a placeholder
(`plugin: __not_yet_wired__`); wiring a hosted run to a real subject-model
target is a separate, explicitly-approved action, not something this file
or `run.sh --hosted` does on its own. `test_redteam_config.py`'s
`HostedStrategiesQuarantined` selector (design §13; not part of this
delivery's test files) is the structural check that no
`MULTI_TURN_STRATEGIES` id or bare `custom:`-prefixed id appears anywhere
outside `configs/hosted/` — a **parsed-key** check, never a substring grep,
because the bare token `custom` occurs constantly in ordinary prose and
unrelated YAML keys throughout this tree.

## What would need to happen to actually run this

1. Separate, explicit approval (handoff.md: "Hosted Hydra/GOAT separate";
   the same authority class as a native-adapter spawn or a paid
   subject-model run).
2. A real target provider replacing the placeholder in
   `hydra-goat.yaml` — either a real subject model, or this lane's own
   `arm-treatment.js` pointed at one once T46's native path exists.
3. `PROMPTFOO_DISABLE_REMOTE_GENERATION` and
   `PROMPTFOO_DISABLE_REDTEAM_REMOTE_GENERATION` deliberately unset for that
   one invocation, with the approval token supplied to `run.sh --hosted`.
4. Results filed under `.artifacts/hosted/`, reported with
   `corpus_frozen: false`, and never merged into the frozen 2×2's cells.

None of this exists in the current delivery. `run.sh --hosted
--approve-token <anything>` refuses today with `BLOCKED — approval
required`, by design, regardless of the token's value.
