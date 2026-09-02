# Testing — the complete eval architecture

Authoritative inventory of every eval tier, CI workflow job, and per-plugin
eval pack in this repository: what each tier proves, what it structurally
cannot prove, when it fires, what it costs, and how to run it locally. It is
linked from `evals/README.md` and the root `AGENTS.md`/`CLAUDE.md`, and it is
**verified, not trusted**: the [machine-readable inventory
block](#machine-verified-inventory) at the bottom is checked against the live
workflows and eval packs by `evals/cheap/check-testing-doc.sh` on every
`evals/cheap/run.sh` run, in both directions.

> **Standing order.** Any PR that adds, removes, renames, or re-scopes an eval
> tier, workflow job, or per-plugin eval pack MUST update this document in the
> same PR — same-PR, not follow-up, so this doc can never describe a tier that
> no longer exists. The cheap tier's testing-doc drift guard machine-enforces
> the inventory half of this order; the prose half (the tier tables below) is
> on the PR author and reviewer.

## The tier map

Cheapest first. Each tier catches a class of regression the tiers above it
structurally cannot.

| Tier | Where | Cost | Fires | Required check? |
|---|---|---|---|---|
| [cheap](#cheap-tier) | `evals/cheap/run.sh` | free, offline, <1 min | every push/PR + before every commit | yes — `cheap tier (deterministic, offline)` |
| [counterfeit](#counterfeit-tier) | `evals/counterfeits/run.sh` | free, offline, ~1 min | path-gated (`evals/cheap/**`, `evals/counterfeits/**`, `plugins/**`) | yes — `counterfeit tier` |
| [install](#install-tier) | `ci/install-smoke.sh` + `evals/cheap/run-one.sh` | free, offline, per-plugin matrix | every push/PR, all registered plugins | yes — `install tier (marketplace install-smoke + per-plugin evals)` |
| [grader-model](#grader-model-check) | `evals.yml` job | ~1 API ping per grader slug | every push/PR (needs secrets; skipped on fork PRs) | yes — `confirm grader model resolves` |
| [behavioral](#behavioral-tier-promptfoo) | `plugins/<p>/evals/promptfoo/` | cents per touched plugin | path-gated per plugin (`plugins/<p>/evals/promptfoo/**`, `evals/paid/**`) | yes — `behavioral tier (promptfoo)` (aggregate) |
| [routing](#routing-tier) | `evals/routing/` | cents (subject model only) | path-gated (routing pack, any `SKILL.md` description, marketplace) | no — advisory |
| [paid multi-plugin gate](#paid-multi-plugin-gate) | `evals/paid/count-touched-plugins.sh` | free | every PR | no — advisory, always exits 0 |
| [scale](#scale-tier) | `plugins/{redgate,agent-compiler}/evals/scale/` | free, offline, minutes | path-gated (`plugins/redgate/**`, `plugins/agent-compiler/**`) | no — evidence, not a merge gate |
| [deep](#deep-tier-pier) | `plugins/<p>/evals/pier/` | dollars + minutes (sandboxed agents) | path-gated to the safety surface (`plugins/*/skills/**/scripts/**`, `plugins/*/evals/pier/**`) | yes — `deep tier (pier)` (aggregate) |
| [example gallery](#example-gallery-refresh--pages) | `refresh-examples.yml` / `pages.yml` | real API budget per refresh | scheduled (1st + 15th, 06:00 UTC) / on `docs/**` push to main | no — review-gated PR / publish |
| [demonstration](#demonstration-discipline) | PR comment | one manual skill run | every skill-change PR | no — human review gate, cannot be machine-enforced |

The six **required** status checks are frozen in `ci/required-checks.json` and
locked to the workflow by `ci/check_branch_protection.py` (run locally:
`python3 ci/check_branch_protection.py --repo .`). Only static aggregate names
are frozen — never dynamic per-plugin matrix-leg names, which would deadlock a
PR if required. Every paid tier is shaped detect → run (matrix, path-filtered,
never individually required) → aggregate (`always()`, required), so a skipped
leg can never leave branch protection hanging — and a skipped leg **announces**
that it is green because it did not run, never silently.

## cheap tier

- **What it proves.** The deterministic structural + safety invariants that
  need no LLM: every shell script parses, every JSON manifest is valid,
  marketplace ↔ plugin wiring holds in both directions, SKILL.md/command
  frontmatter parses, no unfilled placeholders, AGENTS.md and markdown links
  resolve, references are reachable, portability lint, per-plugin safety packs
  (fail-closed: a registered plugin with no `evals/cheap/checks.sh` is a
  failure, not a skip), branch-protection lock, paid-pack discovery self-test,
  install-smoke coverage, cross-plugin references, context-tax budget, version
  drift, secret gate on agent exhaust, routing-pack structure, statistical-gate
  self-test, example-gallery sync/provenance, and the testing-doc drift guard
  defending this document.
- **What it cannot prove.** Whether any load-bearing sentence still *means*
  anything to a model, or whether a skill's behavior changed. It greps and
  parses; it never runs a model.
- **Fires.** Every push and PR (`cheap tier (deterministic, offline)`), and by
  repo discipline before **every** local commit that touches `plugins/**` or
  `evals/**`.
- **Cost.** Free, offline, under a minute.
- **Local run.**
  ```sh
  evals/cheap/run.sh                 # whole repo — exit 0 required to commit
  evals/cheap/run-one.sh <plugin>    # one plugin's pack in isolation
  ```

## counterfeit tier

- **What it proves.** That the cheap gate *discriminates*: a corpus of
  deliberately broken plugins (each fixture mutates a copy of a known-good
  baseline at runtime in a temp dir) must be rejected by the cheap tier **for
  the right reason** (expected failure substring), after a calibration step
  proves the untouched baseline is green. Includes a `weakened-guard` fixture
  that is structurally perfect and only weakens the safety invariant.
- **What it cannot prove.** Anything about gates the corpus has no fixture
  for, and nothing about model behavior.
- **Fires.** Path-gated in CI (`evals/cheap/**`, `evals/counterfeits/**`,
  `plugins/**`); the required `counterfeit tier` aggregate always reports.
- **Cost.** Free, offline, about a minute.
- **Local run.**
  ```sh
  evals/counterfeits/run.sh   # exit 0 = baseline green AND every counterfeit rejected
  ```

## install tier

- **What it proves.** Every marketplace-registered plugin actually *installs*
  structurally — source → `plugin.json` → declared component paths all resolve
  and parse, headless and cross-harness — and that plugin's own cheap pack
  passes in isolation. The matrix is enumerated from `marketplace.json`, so new
  plugins are auto-covered.
- **What it cannot prove.** Runtime behavior in a live harness session; it is
  a structural check, not an interactive install.
- **Fires.** Every push/PR, all plugins, no path filter (free coverage tier);
  required aggregate `install tier (marketplace install-smoke + per-plugin evals)`.
- **Cost.** Free, offline.
- **Local run.**
  ```sh
  ci/install-smoke.sh <plugin> && evals/cheap/run-one.sh <plugin>
  ```

## grader-model check

- **What it proves.** The `anthropic:messages:<model>` grader slug in every
  promptfoo pack resolves to a real, reachable model (HTTP 200), so a
  behavioral run can never be judged by a nonexistent grader.
- **What it cannot prove.** Anything about the subject model or the rubric.
- **Fires.** Every push/PR with secrets (skipped on fork PRs — treated as
  green by the behavioral aggregate); required check
  `confirm grader model resolves`.
- **Cost.** One 8-token API ping per distinct grader slug.
- **Local run.** No dedicated script — the slug lives in each
  `plugins/<p>/evals/promptfoo/promptfooconfig.yaml`; a curl against
  `https://api.anthropic.com/v1/messages` with that model id reproduces it.

## behavioral tier (promptfoo)

- **What it proves.** A model *given the skill prose* behaves as the skill
  demands, judged by an LLM rubric — e.g. graveyard's
  archives-then-verifies-then-hands-over-a-guarded-script. Packs are
  discovered fail-closed by `evals/paid/discover-paid-packs.sh` (declared but
  broken ⇒ red; absent ⇒ no leg). Verdicts go through the
  [statistical spine](#the-statistical-spine) — promptfoo's own exit code is
  never the arbiter.
- **What it cannot prove.** Multi-round protocol behavior, composition between
  plugins, or anything an LLM judge can be fooled about; each pack tests its
  skill alone, single-turn, under a pinned cheap subject model. Because that
  turn is tool-less, every pack's `prompt.txt` carries an explicit no-tools
  clause (the subject must never emit tool-call syntax or stop to "read the
  file first" — it says what it would look for and answers anyway, without
  inventing results it did not obtain), and the cheap tier asserts the clause
  is present in every pack.
- **Fires.** Per-plugin matrix leg, path-gated to that plugin's
  `evals/promptfoo/**` or the shared `evals/paid/**`; required aggregate
  `behavioral tier (promptfoo)`; skipped legs announce themselves.
- **Cost.** Cents per touched plugin per run (subject model via OpenRouter,
  grader on Anthropic).
- **Local run.**
  ```sh
  cd plugins/<plugin>/evals/promptfoo
  OPENROUTER_API_KEY=... ANTHROPIC_API_KEY=... npx --yes promptfoo@0.122.0 eval --output results.json
  cd - && evals/paid/pass-rate.sh plugins/<plugin>/evals/promptfoo/results.json --floor 0.6 --min-runs 2 --min-valid 2
  ```

## routing tier

- **What it proves.** With the *full* roster of installed skill descriptions
  in context, a model routes labeled requests to the right plugin — the
  cross-plugin mis-routing that per-plugin packs are blind to. Verdicts are
  deterministic regex on the model's `ROUTE:` line (no grader key), with
  must-not-fire calibration negatives, `repeat: 5`, and `PROMPTFOO_RETRY_5XX`
  for transient transport errors.
- **What it cannot prove.** That the routed-to skill then *does* anything
  right; it grades the first routing decision only.
- **Fires.** Path-gated (`evals/routing/**`, any `plugins/*/skills/*/SKILL.md`,
  `.claude-plugin/marketplace.json`); job `routing tier (roster trigger
  routing)` is **not** in the required set.
- **Cost.** Cents (subject model only).
- **Local run.**
  ```sh
  evals/routing/gen-roster.sh --check     # roster in sync before spending
  cd evals/routing
  OPENROUTER_API_KEY=... PROMPTFOO_RETRY_5XX=true npx --yes promptfoo@0.122.0 eval -c promptfooconfig.yaml --output results.json
  cd - && evals/paid/pass-rate.sh evals/routing/results.json --floor 0.8 --min-runs 3
  ```

## paid multi-plugin gate

- **What it proves.** Nothing — it is a nudge. It warns (`::warning::`) when a
  PR touches more than one plugin's paid surface, because a red paid leg on a
  multi-plugin PR is ambiguous and a rerun re-bills every touched plugin.
- **What it cannot prove.** It never fails: always exits 0, deliberately not
  in `ci/required-checks.json` (a required red here would hard-block
  legitimate multi-plugin changes).
- **Fires.** Every PR.
- **Cost.** Free.
- **Local run.** `BASE_SHA=... HEAD_SHA=... evals/paid/count-touched-plugins.sh`

## scale tier

- **What it proves.** The same invariants the cheap tier proves once, held
  across hundreds of randomized, isolated trials: agent-compiler kernel stress
  (seeded random registries up to 300 modules — byte-determinism,
  discovery-order independence, metamorphic hash invariance, fail-closed on
  injected faults) and redgate round-lifecycle stress (red-from-birth, pin,
  drift, tamper → drift, stale evidence rejected, guard deny/allow matrix).
- **What it cannot prove.** Model behavior — it is offline, stdlib-only
  stress of the deterministic machinery.
- **Fires.** `scale.yml`, path-gated to `plugins/redgate/**` /
  `plugins/agent-compiler/**` / the workflow itself; **not** a required check
  — evidence, not a merge gate.
- **Cost.** Free, offline, minutes.
- **Local run.**
  ```sh
  plugins/redgate/evals/scale/run.sh
  plugins/agent-compiler/evals/scale/run.sh --sizes 40,120,300 --seeds 3
  ```

## deep tier (pier)

- **What it proves.** A real coding agent in a sandboxed container, across
  harnesses (claude-code in CI; codex, gemini, cursor locally), honors the
  safety invariant end-to-end — for graveyard: gamma (the repo with no
  verified backup) survives a delete request. Runs with a calibration floor
  (oracle must pass, nop must fail) so a broken verifier cannot read green.
- **What it cannot prove.** Anything about non-safety skills, and nothing at
  all when the gate switch is off — see the root `AGENTS.md` WARNING: the
  required check keeps reporting green *because the tier did not run*, and the
  aggregate emits a `::warning::` saying exactly that.
- **Fires.** Path-gated to the safety surface (`plugins/*/skills/**/scripts/**`,
  `plugins/*/evals/pier/**` — frozen in `ci/required-checks.json`); unattended
  (no protected-environment approval); required aggregate `deep tier (pier)`.
- **Cost.** Real API spend plus minutes of sandboxed agent time per pier pack.
- **Local run.**
  ```sh
  PIER_AGENTS="oracle nop" plugins/graveyard/evals/pier/run.sh   # calibration floor, no keys
  plugins/graveyard/evals/pier/run.sh                            # full roster in Docker
  ```

## example gallery (refresh + pages)

- **What it proves.** The published before/after gallery is a *verification
  surface*: every card is a real, provenanced with-skill/without-skill pair
  captured from a graded behavioral run — never hand-written.
  `refresh-examples.yml` re-runs the packs on a biweekly schedule and opens a
  **review-gated PR** (never pushes to main); `pages.yml` publishes `docs/`
  only after merge, re-verifying `docs/build-examples.sh --check` first. The
  cheap tier's gallery gate enforces sync + provenance offline.
- **What it cannot prove.** That the captured pair is *representative* — a
  human reviews the transcript diffs before merge.
- **Fires.** Refresh: scheduled (1st and 15th, 06:00 UTC) + manual dispatch.
  Pages: push to main touching `docs/**`.
- **Cost.** Refresh spends real API budget on every packed plugin per run
  (accepted owner decision); pages is free.
- **Local run.** `docs/build-examples.sh --check` (sync only; the capture
  itself needs the behavioral tier's keys).

## demonstration discipline

- **What it proves.** What a changed skill actually does to real material —
  the one thing no green check shows. Every skill-change PR must carry a PR
  comment with the skill applied to real input: the input, the output, the
  rule that produced each change, and the misses.
- **What it cannot prove / why it cannot be machine-enforced.** The cheap tier
  is offline and cannot read a PR comment; no deterministic check can tell a
  real run from a fabricated one. It is a **human review gate**: do not
  approve a skill change whose demonstration is missing, and never post a
  demonstration you did not actually run.
- **Fires.** Every PR that creates or edits a `SKILL.md`, a skill's
  `references/`, or its invoking command. Full rules: root
  `AGENTS.md`/`CLAUDE.md`, "Demonstration discipline".
- **Cost.** One manual run of the skill.

## The statistical spine

Every LLM-driven tier shares the same statistical machinery, so no green is an
uninterpretable n=1 and no required check goes red on the weather:

- **`repeat:`** — every promptfoo pack declares `repeat:` (behavioral: 3,
  routing: 5); the cheap tier fails any pack that loses it.
- **k-of-N pass-rate floor** — `evals/paid/pass-rate.sh` is the verdict, not
  promptfoo's exit code: per-scenario pass rate over *valid* samples must meet
  the floor (behavioral 0.6 = majority of 3; routing 0.8).
- **FAULT vs verdict separation** — a transport error (504, aborted call,
  empty body) is a FAULT, an invalid sample excluded from the floor — never
  counted as a rubric failure. Classification keys on promptfoo's
  `failureReason`: `2`/`"error"` = FAULT (excluded); `1` = a real assertion
  FAIL scored against the floor — even though under promptfoo ≥ 0.122 every
  assertion-failed row *also* carries `.error` (the assertion message).
  `.error` alone marks a FAULT only on legacy rows with no `failureReason`
  recorded.
- **Fail-closed starvation** — a scenario with too few valid samples
  (`--min-runs` / `--min-valid`) fails the run: an all-504 scenario is "never
  tested", not "green". A missing/unreadable `results.json` also fails.
- **`PROMPTFOO_RETRY_5XX`** — transient 5xx responses are retried with backoff
  before ever becoming a FAULT row (routing tier wiring).
- The spine itself is mutation-tested offline in `evals/cheap/run.sh` §18
  against synthetic fixtures — gut the floor logic and the cheap tier goes red
  without a single model call.

Any **new** LLM tier inherits this spine wholesale.

## Planned tiers (not yet live)

Planned, not specified here — the linked issues own the design. Do **not**
add these to the inventory block until they actually exist:

- **L1 decision-point probes** — trajectory-prefix promptfoo scenarios that
  freeze a fabricated mid-run transcript and assert on the single next move,
  with a must-not-fire twin for every must-fire:
  [#89](https://github.com/JRichlen/agent-plugins/issues/89).
- **L2 plan-audit and L3 trajectory/composition tiers** — typed composition
  results, plan grading against a labeled corpus, and deterministic post-hoc
  artifact audits of `.redgate/`; owned by
  [#88](https://github.com/JRichlen/agent-plugins/issues/88) (see the scope
  split recorded on #89).

## Machine-verified inventory

The block below is parsed by `evals/cheap/check-testing-doc.sh` and compared
— both directions — against the live repo: workflow files and job display
names from `.github/workflows/*.yml` and `*.yaml` (matrix `${{ ... }}`
suffixes stripped), repo-level eval directories from `evals/*/`, and the
plugin-qualified eval packs from `plugins/*/evals/*/` (so one plugin gaining
or losing a pack is itself an inventory change, not just a new pack *kind*).
If you add, remove, rename, or re-scope any
of these, update this block (and the prose above) in the same PR;
`evals/cheap/check-testing-doc.sh --print` emits the current live list.

<!-- BEGIN LIVE-INVENTORY (verified by evals/cheap/check-testing-doc.sh) -->
```
eval-dir: evals/cheap
eval-dir: evals/counterfeits
eval-dir: evals/paid
eval-dir: evals/routing
eval-dir: evals/templates
job: agent-compiler scale (kernel stress)
job: behavioral tier (promptfoo)
job: behavioral tier — detect paid packs
job: behavioral tier — promptfoo
job: build
job: cheap tier (deterministic, offline)
job: confirm grader model resolves
job: counterfeit tier
job: counterfeit tier — detect
job: counterfeit tier — run (corpus)
job: deep tier (pier)
job: deep tier — detect safety-path changes
job: deep tier — pier run
job: deploy
job: install tier (marketplace install-smoke + per-plugin evals)
job: install tier — detect plugins
job: install tier — install-smoke + evals
job: paid multi-plugin gate
job: redgate scale (lifecycle stress)
job: refresh
job: routing tier (roster trigger routing)
pack: agent-compiler/cheap
pack: agent-compiler/promptfoo
pack: agent-compiler/scale
pack: codebase-design/cheap
pack: context-handoff/cheap
pack: dev-diary/cheap
pack: diagnosing-bugs/cheap
pack: docs-hygiene/cheap
pack: egress-gate/cheap
pack: find-before-build/cheap
pack: find-before-build/promptfoo
pack: fleet-playbook-curator/cheap
pack: fleet-playbook-curator/pier
pack: fleet-playbook-curator/promptfoo
pack: graveyard/cheap
pack: graveyard/pier
pack: graveyard/promptfoo
pack: grill-me/cheap
pack: orchestrate/cheap
pack: plugin-factory/cheap
pack: prove-the-undo/cheap
pack: recurrence-detector/cheap
pack: redgate/cheap
pack: redgate/promptfoo
pack: redgate/scale
pack: scope-fence/cheap
pack: scope-fence/promptfoo
pack: semver-gate/cheap
pack: semver-gate/promptfoo
pack: stop-rule/cheap
pack: stop-rule/promptfoo
pack: tailscale-wif/cheap
pack: tailscale-wif/promptfoo
pack: tracer-bullets/cheap
pack: verify-before-claim/cheap
pack: verify-before-claim/promptfoo
pack: voice/cheap
pack: voice/promptfoo
pack: wayfinder/cheap
pack: wayfinder/promptfoo
workflow: evals.yml
workflow: pages.yml
workflow: refresh-examples.yml
workflow: scale.yml
```
<!-- END LIVE-INVENTORY -->
