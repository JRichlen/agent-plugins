# Counterfeit corpus — proving the cheap tier is not a rubber stamp

The cheap tier (`evals/cheap/run.sh`) proves that **good** plugins pass. That is
only half of a gate. A gate that never rejected anything would also pass every
good plugin — so "green on the real repo" says nothing about whether the gate
actually *discriminates*.

This directory supplies the other half: a corpus of deliberately broken plugins,
each of which the cheap tier **must reject, and reject for the right reason**.

## How it stays safe to keep in the repo

The broken artifacts are never stored on disk — if they were, the always-on
cheap tier would trip over them (its section 2 scans every `*.json` in the whole
repo; section 1 parses every `*.sh` under `plugins/` and `evals/`).

Instead:

- **`baseline/`** is ONE all-valid plugin (`sample-guard`) plus a synthetic
  `.claude-plugin/marketplace.json`. It lives under `evals/`, not `plugins/`, so
  the real tier's plugin-specific gates never reach it, and every file in it is
  valid JSON / valid shell / portability-clean, so the generic gates (1, 2) that
  *do* scan the whole repo stay green.
- Each **`fixtures/NN-<gate>/`** ships a `DEFECT.md` (with an
  `EXPECT_FAIL_SUBSTRING=` line) and a `mutate.sh` that breaks a **copy** of the
  baseline at runtime, inside a temp dir. Nothing broken ever persists.

## What the meta-runner does

`run.sh`:

1. **Calibration.** Builds a synthetic marketplace root (copies `evals/cheap` +
   the baseline plugin + the baseline marketplace.json into a temp dir) and runs
   the copied `run.sh`. The baseline MUST be green — if a known-good plugin fails,
   the corpus is miscalibrated and every rejection below is meaningless. (This is
   winner #11, the calibration meta-test, folded into the corpus itself.)
2. **Rejection.** For each fixture: fresh copy → apply `mutate.sh` → run the
   copied `run.sh` → assert it exits non-zero **and** prints the fixture's
   `EXPECT_FAIL_SUBSTRING`. The substring check is what proves the *right* gate
   fired, not merely that something failed.

The copied `run.sh` computes its `REPO_ROOT` as its own `../..`, i.e. the temp
root — so it lints exactly the synthetic tree and nothing from the real repo.

## The fixtures — one per cheap-tier gate

| Fixture | Gate exercised | Proves |
|---|---|---|
| `01-shell-syntax` | 1 — `bash -n` | unparseable shell is caught |
| `02-json-invalid` | 2 — JSON validity | malformed manifest is caught |
| `03-name-mismatch` | 3 — marketplace→plugin wiring | a plugin renamed out of sync is caught |
| `04-frontmatter-missing` | 4 — SKILL.md frontmatter | a skill missing `description:` is caught |
| `05-unregistered-plugin` | 5 — reverse lockfile | a plugin dir with no marketplace entry is caught |
| `06-placeholder` | 6 — no unfilled `{{token}}` | a shipped template hole is caught |
| `07-agents-path` | 7 — AGENTS.md paths resolve | a broken map reference is caught |
| `08-sentinel` | 8 — red-by-default sentinel | an unimplemented eval pack is caught |
| `09-portability` | 9 — portability lint | undeclared Claude-Code-only prose is caught |
| `10-missing-pack` | 10 — fail-closed pack discovery | a registered plugin with no safety pack is caught |
| `11-weakened-guard` | the plugin's OWN sourced pack | a real safety-invariant weakening is caught |
| `19-agentic-suite-missing` | 22 — agentic suite gate | a deleted `evals/agentic/run.sh` is caught, not silently skipped |
| `20-agentic-catalog-gap` | 22 — agentic suite gate (catalog merge, contract §7.3) | a catalog fragment silently dropping an allocated ID is caught |
| `21-agentic-vacuous-verifier` | 22 — agentic suite gate (core, T10) | a positive card's outcome verifier degenerating to `return True` is caught |
| `22-agentic-zero-denominator` | 22 — agentic suite gate (measurement, T38) | a zero-denominator rate rendered as `0%` instead of `unavailable (...)` is caught |
| `23-agentic-forged-native` | 22 — agentic suite gate (adapter, T09/T29/T31) | an attempt asserting its own native provenance (or a replay minting host-observed entries) is caught |
| `24-agentic-hardcoded-hooks` | 22 — agentic suite gate (protocol, T19) | a fourth hook added to the synthetic plugin tree that hardcoded discovery would miss is caught |
| `25-agentic-exposure-parity` | 22 — agentic suite gate (registry, T16) | an unmatched-widening baseline arm capability is caught |
| `26-redteam-npx` | 22 — redteam suite gate (T48) | an `npx promptfoo@latest` reference breaking the offline default is caught |
| `27-redteam-corpus-drift` | 22 — redteam suite gate (T44) | a frozen red-team corpus hash drifting undetected is caught |
| `28-redteam-pin-drift` | 22 — redteam suite gate (T42) | an unpinned/drifted promptfoo version is caught |
| `29-redteam-rubric-dominance` | 22 — redteam suite gate (T47) | a disagreeing grader rubric silently overriding the protected-effect verdict is caught |
| `30-redteam-native-forgery` | 22 — redteam suite gate (T47) | a forged native-proof claim gating safety qualification is caught |
| `31-redteam-vacuous-row` | 22 — redteam suite gate (T44/T47) | a generated-config row that disables its default assertions with none of its own is caught by a static text scan, no promptfoo process |

Fixtures `19`-`31` are new in this change (contract §8.8, backlog T51): they
exercise `evals/cheap/run.sh` section 22's `evals/agentic/run.sh --gate` /
`evals/redteam/run.sh --gate` calls, reached only once `build_root()` stages
`evals/agentic/**` and `evals/redteam/**` into the synthetic root (above).
Total corpus after this change: 18 existing + 13 new = **31 fixtures**. A
full run measures **31 of 31** rejected by the expected gate, ~5-6 minutes
on this host.

**`31-redteam-vacuous-row`'s history is worth reading before touching this
gate again.** Its mutation (`testCase.options.disableDefaultAsserts: true`
on one row) was originally caught only by letting the pinned promptfoo
actually evaluate the mutated row and feeding the result through
`bin/verdict.py`. That real-eval step in `--gate` was later found to
intermittently misclassify an ordinary provider FAULT (a call that
errored/timed out) as VACUOUS under heavy host CPU contention, because
`bin/verdict.py`'s `classify_row` checked VACUOUS before `failureReason ==
2` — both shapes have zero `componentResults`. Two independent fixes
landed: `classify_row` now checks FAULT first (a real, general correctness
fix, covered by a synthetic-row regression test in
`test_redteam_provider.ClassifyRowFaultVsVacuous`), and `--gate`'s own check
for this fixture was replaced with a static, subprocess-free text scan of
the already-generated YAML (`bin/generate.py` never emits a per-row
`assert:` override, so `disableDefaultAsserts: true` with none of its own
is, by construction, a zero-assertion row) — a flaky always-on gate is
worse than a documented static/runtime split. The RUNTIME half of the
defect (a row promptfoo itself scores a vacuous "No assertions" perfect
pass) is still real and still tested, just not from `--gate`:
`test_redteam_design.ProtectedEffectDominanceAndNativeGate`'s
`test_vacuous_row_is_never_counted_as_pass` and
`test_real_offline_eval_feeds_a_complete_tranche` exercise it directly, and
`evals/redteam/run.sh` with no flag / `--offline` still runs that full
suite for real. See the integration report for the full timeline.

`11-weakened-guard` is the most important: the plugin stays structurally perfect
(valid JSON, parseable shell, pack present) and only the safety invariant is
weakened. Every structural gate stays green; only the plugin's own sourced
`checks.sh` bites. It proves fail-closed discovery does more than confirm a pack
*file exists* — it proves a sourced safety pack actually **defends something**.

## Running it

```sh
evals/counterfeits/run.sh     # exit 0 = baseline green AND every counterfeit rejected
```

## Adding a fixture when you add a gate

Every new cheap-tier gate should get a counterfeit here, or the gate is unproven.
Create `fixtures/NN-<gate>/` with:

- `DEFECT.md` — describe the defect and the gate, ending with a single
  `EXPECT_FAIL_SUBSTRING=<literal from run.sh's fail message>` line.
- `mutate.sh` — takes `$1` = synthetic root, breaks exactly one thing so ONLY
  the intended gate fires. Keep the break structurally minimal; if it trips an
  earlier gate too, the earlier gate's message must still appear so the substring
  assertion holds. Materialize any broken artifact at runtime — never commit it.
