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
| [subject-model](#subject-model-reachability-advisory) | `evals/paid/check-subject-model.sh` | ~1 API ping per subject slug | every push/PR (needs secrets; skipped on fork PRs) **and** as a preflight in `refresh-examples.yml` | no — advisory in `evals.yml`; blocking in the refresh, which spends the budget |
| [behavioral](#behavioral-tier-promptfoo) | `plugins/<p>/evals/promptfoo/` | cents per touched plugin | path-gated per plugin (`plugins/<p>/evals/promptfoo/**`, `evals/paid/**`) | yes — `behavioral tier (promptfoo)` (aggregate) |
| [routing](#routing-tier) | `evals/routing/` | cents (subject model only) | path-gated (routing pack, any `SKILL.md` description, marketplace) | no — advisory |
| [paid multi-plugin gate](#paid-multi-plugin-gate) | `evals/paid/count-touched-plugins.sh` | free | every PR | no — advisory, always exits 0 |
| [subject-model matrix](#subject-model-matrix-manual-advisory) | `subject-matrix.yml` + `evals/paid/subject-matrix.sh` | (1 + subjects) × the pack's usual cents | manual dispatch only | no — advisory; the baseline subject decides the job, extra subjects never do |
| [calibration sheet](#calibration-sheet-manual-no-model-calls) | `calibration-sheet.yml` + `evals/paid/calibration/` | free (no model calls) | manual dispatch only | no — writes a blind sheet to a `calibration/<run-id>` branch for a human to label |
| [grader agreement](#grader-agreement-manual-grading-only) | `grader-agreement.yml` + `evals/paid/calibration/regrade.sh` | grading spend only (no subject calls) | manual dispatch only | no — reports agreement and kappa between graders on a finished run's outputs |
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
  drift, secret gate on agent exhaust, routing-pack structure, runner helper
  parity (`run.sh` and `run-one.sh` must source the one shared
  `evals/cheap/helpers.sh`, define no local helper, and wrap pack sourcing in
  the fail-closed guard — see
  [#120](https://github.com/JRichlen/agent-plugins/issues/120)), statistical-gate
  self-test, example-gallery sync/provenance, design-timeline sync/receipts
  (`docs/timeline/`: page in sync with its decision data, every receipt
  resolving), and the testing-doc drift guard defending this document.
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
  that is structurally perfect and only weakens the safety invariant, and a
  `silent-helper-skip` fixture that breaks the pack-to-harness relationship
  rather than plugin content: a pack assertion calling a helper no runner
  defines must be rejected, not silently skipped ([#120](https://github.com/JRichlen/agent-plugins/issues/120)).
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
  turn is tool-less, every pack's subject prompt (`prompt.txt`, or the
  `prompt.js` function tailscale-wif renders from) carries an explicit no-tools
  clause (the subject must never emit tool-call syntax or stop to "read the
  file first" — it says what it would look for and answers anyway, without
  inventing results it did not obtain), and the cheap tier discovers each
  pack's configured prompt file from its `promptfooconfig.yaml` and asserts
  the clause is present in every one.
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
  in context, a model routes labeled requests to the right **composition** —
  the typed `ROUTE: specialist=… | envelope=… | guards=… | interaction_owner=…`
  line (issue #88), graded by a per-scenario regex: **legacy (migrated
  single-skill) scenarios pin only the `specialist` slot** — the other slots
  accept any validator-legal value, because those rows test routing
  precedence — except that the **discipline-skill legacy rows (egress-gate,
  find-before-build, stop-rule) grade active-in-either-role**: the named
  skill must be the `specialist` *or* appear in the `guards` list
  (required-subset), the specialist otherwise free to be `none` or a
  procedure skill, because the schema itself files cross-cutting disciplines
  under guards and the live model routes them there — while **composition
  scenarios (S1–S4) pin every slot**: exact for
  specialist/envelope/interaction_owner and for `guards=none` (S2, the
  composition negative, additionally tolerates a lone `find-before-build`
  guard — the search-before-writing discipline its "new RateLimiter … before
  I write it" request legitimately triggers), **required-subset** for named
  guards (must-have guards present in the sorted list, roster-valid extras
  allowed; regrades from PR #93's live runs) — plus the fail-closed `route-contract.js` validator on every row
  (all 8 coherence rules, so "any value" never means "any junk") — catching
  the cross-plugin mis-routing that per-plugin packs are blind to, including
  collapse-into-redgate and ceremony on work that warrants none. A second leg,
  `evals/routing/trajectory/`, grades redgate's stateful gate behavior at
  frozen decision points (`STEP:` line + `step-contract.js` cross-field
  invariants: ARM before TRACE, explicit MAJOR stop, silence is not consent,
  the gate survives resume). Trajectory slots are **behavior-pinned,
  taxonomy-tolerant**: `proceed`/`disposition` are exact everywhere, while T1
  accepts `gate=none|major` and T4 accepts `action=resume|gate` (defensible
  alternate readings of the same stop, per the same regrade). Both legs grade
  the model's **reply, not its reasoning trace** (`showThinking: false` on
  the provider — otherwise promptfoo prepends the reasoning to the graded
  output and a `ROUTE:`/`STEP:` line drafted while thinking fails the
  one-line rule of a correct final answer). Both legs:
  deterministic verdicts (no grader key), must-not-fire calibration
  negatives, `repeat: 5`, its own `pass-rate.sh` gate, and
  `PROMPTFOO_RETRY_5XX` for transient transport errors.
- **What it cannot prove.** That the routed-to skill then *does* anything
  right in a live run; it grades routing decisions and frozen-prefix gate
  decisions, not full trajectories (that is #89's L3).
- **Fires.** Path-gated (`evals/routing/**`, any `plugins/*/skills/**/SKILL.md`,
  `.claude-plugin/marketplace.json`, plugin manifests); job `routing tier
  (roster trigger routing)` is **not** in the required set.
- **Cost.** Cents (subject model only; 70 routing + 25 trajectory calls).
- **Local run.**
  ```sh
  evals/routing/gen-roster.sh --check     # roster in sync before spending
  node evals/routing/route-contract.test.js          # offline contract tests
  node evals/routing/trajectory/step-contract.test.js
  cd evals/routing
  OPENROUTER_API_KEY=... PROMPTFOO_RETRY_5XX=true npx --yes promptfoo@0.122.0 eval -c promptfooconfig.yaml --output results.json
  OPENROUTER_API_KEY=... PROMPTFOO_RETRY_5XX=true npx --yes promptfoo@0.122.0 eval -c trajectory/promptfooconfig.yaml --output trajectory-results.json
  cd - && evals/paid/pass-rate.sh evals/routing/results.json --floor 0.8 --min-runs 3
  evals/paid/pass-rate.sh evals/routing/trajectory-results.json --floor 0.8 --min-runs 3
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

## subject-model matrix (manual, advisory)

- **What it proves.** Whether a pack's prose steers models *other than* the
  one cheap subject the behavioral tier pins. On dispatch, chosen packs run
  against the baseline subject plus every extra subject named in the input;
  `evals/paid/pass-rate.sh --by-provider --baseline <id>` scores each provider
  separately and reports per scenario. Pooling would hide exactly the split
  this exists to show (3/3 on the baseline and 0/3 on a new subject pool to a
  single 0.50 scenario), so the scorer never pools in this mode.
- **What it cannot prove.** Anything about a subject nobody has dispatched it
  for. It also does not promote a subject: that is a human decision applied to
  the report, under one stated rule — the pack's calibration control (the
  stub-skill scenario, whose assertion **passes** when the bare model behaves
  as an unaided model would) must still pass under the new subject. A control
  that fails under a new model means that model already does what the skill
  asks unaided, so the with-skill green measures nothing on that scenario: a
  scenario finding, not a promotion.
- **Fires.** `workflow_dispatch` only (`subjects=` required, `packs=` optional,
  empty = every plugin with a valid promptfoo pack). Never scheduled, never
  path-gated, never in `ci/required-checks.json`. The job's exit code reflects
  the **baseline** provider alone; every other provider is printed as
  `ADVISORY`. A baseline that produced no rows fails closed.
- **How the pack is left alone.** `evals/paid/subject-matrix.sh PACK --subjects
  "a,b"` writes `promptfooconfig.matrix.yaml` beside the pack: the baseline
  provider first, then each subject with the baseline's own provider config
  copied verbatim (`max_tokens`, `showThinking`, …) so every subject is graded
  under identical settings. The overlay and `results.matrix.json` are
  git-ignored; the required behavioral leg never reads them.
- **Cost.** Roughly (1 + number of subjects) × the pack's usual spend, still
  cents per pack. Results are uploaded as a per-pack artifact so the numbers
  can be recorded on [#102](https://github.com/JRichlen/agent-plugins/issues/102).
- **Local run.** `evals/paid/subject-matrix.sh plugins/<p>/evals/promptfoo
  --subjects "<id>,<id>"`, then `npx promptfoo@0.122.0 eval -c
  promptfooconfig.matrix.yaml --output results.matrix.json` in the pack
  directory, then `evals/paid/pass-rate.sh results.matrix.json --by-provider
  --baseline "$(evals/paid/subject-matrix.sh <pack> --baseline-id)"`.
  Offline: `evals/paid/subject-matrix.sh --self-test`; the cheap tier §18b
  fixture-tests the scorer's per-provider mode and the overlay.

## calibration sheet (manual, no model calls)

- **What it proves.** Nothing by itself; it produces the material for
  measurement 2 of [#102](https://github.com/JRichlen/agent-plugins/issues/102),
  a human grading the same outputs the model grader graded, blind. On
  dispatch (`run_id`, `packs`, `n`) it downloads the named run's results
  artifact on the runner (`subject-matrix-<pack>` or `promptfoo-results-<pack>`),
  draws a seeded blind sheet with `evals/paid/calibration/sample-for-labelling.py`
  (scenario, request, output, empty label; no verdict, no provider), seals
  the grader's verdicts as base64 so they are not read by accident, and
  pushes both to a `calibration/<run-id>` branch under
  `plugins/<pack>/evals/promptfoo/calibration/`. The branch is based on the
  commit that produced the run (its head SHA), not on the dispatch ref, so
  the pack rubric beside the sheet is the one that graded those verdicts.
- **What it cannot prove.** Anything until a human fills the labels and
  `agreement.py` reports the agreement and kappa; a sheet drawn from an
  all-green run carries little kappa information (expected agreement is
  high whatever the human does), so draw from runs with real failures too.
- **Fires.** `workflow_dispatch` only. Never scheduled, never required.
  `contents: write` is the only permission it needs, to push the branch.
- **Cost.** Free; no model is called.
- **Local run.** `evals/paid/calibration/README.md` gives the same procedure
  from a downloaded `results.json`.

## grader agreement (manual, grading only)

- **What it proves.** Measurement 3 of
  [#102](https://github.com/JRichlen/agent-plugins/issues/102): how often the
  model grader agrees with itself, and with a grader from another model
  family, on the same outputs under the same rubric. On dispatch (`run_id`,
  `packs`, `grader`, `self`) it downloads the run's results artifact,
  `evals/paid/calibration/regrade.sh` writes an overlay whose provider is
  `replay-provider.js` (it plays each recorded output back; the subject is
  never called again) and whose tests carry each sample's own assertions
  copied from the results rows (model-graded assertions only, so a
  deterministic `icontains` beside a rubric cannot force the same verdict on
  both sides), promptfoo runs only the grading, and `agreement.py` reports
  percent agreement, Cohen's kappa, the confusion matrix and the
  disagreements of each re-grade against the run's original model-graded
  verdicts, joined on the sampler's hash. The self grader is read from the
  run's own rows, not from the dispatch checkout, so an older run is compared
  against the grader that actually graded it; a leg that yields no report
  fails the job. Self-agreement is the label-noise
  floor: if it sits below the pass-rate floor, two of three cannot separate
  a skill effect from grader noise.
- **What it cannot prove.** Which grader is right; only whether they agree.
  It does not promote or demote a grader by itself, and an all-green run
  gives kappa little to say (expected agreement is already high).
- **Fires.** `workflow_dispatch` only. Never scheduled, never required.
  `actions: read` to fetch the artifact, `contents: read` for the checkout.
- **Cost.** Grading only: roughly a third of the original run per re-grade.
- **Local run.** `evals/paid/calibration/README.md`, measurement 3. Offline:
  `evals/paid/calibration/regrade.sh --self-test`; the cheap tier §18b
  fixture-tests the overlay and the replay provider.

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

## subject-model reachability (advisory)

- **What it proves.** That the model every behavioral pack actually tests is
  *reachable* right now: the `OPENROUTER_API_KEY` secret is valid and the pinned
  slug still exists. It reports the distinct HTTP causes separately (401 revoked
  key, 402 no credit, 404 moved slug, 429 rate limited) so the fix is named
  rather than guessed. A **429 is retried with backoff and then FAILS the
  job** — it used to warn and pass, and run 35287312617 showed what that cost:
  the preflight saw a 429, called it "not conclusive", exited 0, and the
  behavioral tier then starved on RateLimitExhaustedError and 300s queue
  timeouts with the account funded the whole time. A 429 that survives backoff
  is a throughput verdict, not a blip, and it is the cheapest available
  prediction that the packs behind it will produce no verdict at all. The 429
  message reads `limit_source` before assigning blame: an
  `upstream_provider_shared_pool` limit is the provider's, and lowering our own
  concurrency does nothing about it (measured: 36 → 12 concurrent moved FAULTs
  6/9 → 7/9).
- **What it prints.** The vendor's error body, because it names the affordable
  `max_tokens` and carries `limit_source` — but piped through
  `evals/paid/redact-vendor-ids.sh` first, which strips the workspace
  key-management URL (its last segment is the key's id) and the `user_id`. The
  same redactor guards all three failing-transcript dumps in `evals.yml`. Not
  the API key, so low severity; but a public Actions log is permanent and no
  part of the diagnosis needs an account identifier.
  It also probes **both** numbers that gate an OpenRouter request, because they
  fail independently: this key's own spending cap (`/api/v1/key` →
  `limit_remaining`) and the account balance behind every key (`/api/v1/credits`
  → `total_credits - total_usage`). It fails closed when *either* is at or below
  zero. Reading only the key cap is not sufficient and was not hypothetical:
  from 2026-09-10 the key cap read 53% used — comfortably healthy — while every
  row of every pack was refused with `metadata.limit_source:
  openrouter_credits`, and PR #133 sat red for five days on a diagnosis that
  read the key cap and concluded funding was fine.
- **Why it exists.** CI had always confirmed the Anthropic *grader* resolves and
  never once checked the *subject*, so an unreachable subject was a blind spot:
  it would produce packs where every real-skill row fails with no signal
  anywhere. Two refresh runs (2026-09-01 and 2026-09-08) graded all 12 packs,
  spent roughly 50 minutes of paid API time, captured nothing and reported
  success — that is the evidence gap this check closes, **not** a diagnosis of
  those runs. On its first run the check came back green, so a dead key or a
  moved slug was ruled out. Two independent causes were then found: five packs
  ship no calibration case, so no before/after pair can exist for them (see the
  example-gallery section); and, separately, OpenRouter was answering
  `402 Payment Required — this request would exceed your available credits given
  your current in-flight requests` on the pack runs themselves.
- **What it cannot prove.** That the model answers *well* — only that it
  answers at all. A reachable model can still fail every rubric, so a green
  here never means the packs are healthy; it only removes one explanation.
- **What a green ping specifically does NOT prove: funding.** OpenRouter
  reserves credit per request against the requests already in flight, and a CI
  fan-out is roughly 12 packs at concurrency 3. So an 8-token ping can return
  200 while every row of every pack returns 402. That is measured, not
  theoretical: on 2026-09-09 this check reported all slugs reachable while 11 of
  12 behavioral packs failed every row on exactly that 402. The credit probe
  exists because of this; where the account reports no numeric remaining
  balance, the check says outright that funding is **unverified** rather than
  implying it is fine.
- **Advisory in `evals.yml`, blocking in `refresh-examples.yml`.** In the evals
  workflow it is deliberately **not** in the behavioral gate's `needs`, so a
  dead subject key reports in seconds instead of turning a required check red
  across every open PR; promoting it to a gate there (adding it to the
  behavioral aggregate's `needs` + assess, exactly as `grader-model` is) is a
  one-line change and an owner decision. In the **refresh** workflow it runs as
  a hard preflight *before* the paid pack loop, because that is the workflow
  that actually spends the budget — preflighting only `evals.yml` would leave
  the expensive path unguarded. A cheap-tier guard fails if that preflight is
  removed, reordered after the pack loop, or stops calling the script.
- **Implementation.** `evals/paid/check-subject-model.sh`, shared by both
  workflows so the two can never drift. It reads provider ids from the parsed
  YAML `providers:` list rather than grepping the file, so a commented-out
  historical slug left above the active one during a migration cannot be
  reported green while promptfoo calls a different model. `--list` prints the
  slugs it would ping and needs no network or key.
- **Fires.** Every `evals.yml` run where secrets are available (not fork PRs),
  and at the start of every `refresh-examples.yml` run.
- **Cost.** One 8-token completion per distinct subject slug per run.
- **Local run.** Needs `OPENROUTER_API_KEY`; the job body is the whole check.

## example gallery (refresh + pages)

- **What it proves.** The published before/after gallery is a *verification
  surface*: every card is a real, provenanced with-skill/without-skill pair
  captured from a graded behavioral run — never hand-written — with the
  subject, grader and judge models disclosed by role, and no model grading
  its own family. `refresh-examples.yml` re-runs the packs on a biweekly
  schedule, records each snapshot's Actions `run_url`, keeps the raw
  `results.json` as a 90-day artifact, **Sigstore-attests every snapshot it
  wrote** (`actions/attest-build-provenance`, verifiable with
  `gh attestation verify … --signer-workflow`), and opens a **review-gated
  PR** (never pushes to main); `pages.yml` publishes `docs/` only after
  merge, re-verifying `docs/build-index.sh --check`,
  `docs/build-examples.sh --check` and `docs/timeline/build-timeline.sh
  --check` first — the landing page, the gallery and the design-trajectory
  timeline are all generated surfaces. The cheap tier's gallery gate enforces
  sync + role-by-role provenance offline (a graded snapshot whose subject and
  grader share a model family fails; so does a seed claiming an attestation),
  its pack gate refuses any promptfoo pack whose subject and grader share a
  family, and its timeline gate enforces sync + receipts.
- **What it cannot prove.** That the captured pair is *representative* — a
  human reviews the transcript diffs before merge. And an attestation proves
  GitHub-hosted infrastructure produced the bytes in a run of the public
  workflow, not that a model rather than the workflow wrote the text — which
  is why the workflow file is short and pinned by commit in the run. Seeds
  (produced outside CI) carry no attestation and are labelled as such.
- **Fires.** Refresh: scheduled (1st and 15th, 06:00 UTC) + manual dispatch.
  Pages: push to main touching `docs/**`.
- **Cost.** Refresh spends real API budget on every packed plugin per run
  (accepted owner decision); pages is free.
- **Local run.** `docs/build-examples.sh --check` (sync only; the capture
  itself needs the behavioral tier's keys).
- **Why a zero-capture run is now a hard failure.** Two refresh runs
  (2026-09-01 and 2026-09-08) graded all 12 packs, spent roughly 50 minutes of
  paid API time, wrote **zero** snapshots, and both reported success: every
  `capture-example.sh` call is `|| true`, and its skip printed one opaque line.
  The workflow now fails when it captures nothing (that is always systemic — a
  dead subject key, a moved schema, a pack whose real-skill rows all fail), the
  skip names its own cause (row counts, pass counts, the top failure reason),
  and the cheap tier pins both halves against offline fixtures in the shape
  promptfoo 0.122.0 actually emits (`evals/cheap/fixtures/capture-example/`).
- **Why the refresh deletes its own `results.json`.** `promptfoo eval --output
  results.json` writes into each pack directory. Those files are gitignored,
  but the cheap tier scans the *working tree*, and a `results.json` embeds the
  pack's prompt template — so its `{{question}}` trips the "no unfilled
  `{{placeholder}}` tokens" gate for every packed plugin. The 2026-09-01
  refresh died exactly there: 24 failures at the last step, no PR opened, and
  the whole run's API spend lost. The workflow now removes them after
  uploading the artifact and before running the tier, and a cheap-tier guard
  fails if that step is dropped or reordered after the tier.

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
- **Truncation is a FAULT, not a failure** — a completion the provider cut off
  at `max_tokens` returns HTTP **200** with an empty body, so promptfoo records
  it as `failureReason` **1**: the pack's own fail-closed assertion firing on
  the empty string. Read literally that is 30 skill failures; it is actually 30
  unanswered calls. `pass-rate.sh` therefore excludes a row whose visible output
  is empty **and** whose `finishReason` is `length`/`max_tokens` — both halves
  required, so a truncated row that still emitted a judgeable answer stays a
  scored FAIL, and an empty answer with `finishReason: stop` stays a scored FAIL
  (no signal means no excuse). The report names the count and points at the
  budget. "No answer" has a **second shape that is not an empty body**: promptfoo
  surfaces a model's reasoning trace as the output, so a completion that spent
  every token deliberating arrives as tens of KB of text that never resolves into
  an answer. The provider's own accounting is the discriminator —
  `completion == completionDetails.reasoning` means zero answer tokens were
  emitted — and it is arithmetic, not a guess about the text, since a row with
  even one answer token has `reasoning < completion`. Found on run 35298840491,
  where agent-compiler's calibration floor read 1/3 against 36 KB of unresolved
  deliberation cut off mid-sentence; the grader's own words were *"there is no
  final response here."* The stop reason is still required for either shape. Found on run 35296766647, where 30 of routing's 70 rows came back with
  `completion == completionDetails.reasoning == max_tokens` and six scenarios
  read as below-floor; two of them had never produced a single answer. Guarded
  in `evals/cheap/run.sh` §18 by four fixtures, each mutation-tested.
- **The reasoning budget is capped where truncation was measured** — raising
  `max_tokens` alone does not fix a model that spends the whole budget thinking:
  routing still starved two scenarios at 8192, and agent-compiler's floor spent
  8192/8192 on reasoning. Both packs now send an explicit
  `passthrough: {reasoning: {max_tokens: N}}`, sized from the answer length
  their own passing rows needed — routing 7680 of 8192 (its answers are one
  `ROUTE:` line, 21–37 tokens), agent-compiler 6144 of 8192 (its answers ran to
  1619). `passthrough` is used rather than `reasoning_effort` because promptfoo
  splices it verbatim into the chat body regardless of its own reasoning-model
  detection, and because effort maps to a vendor-chosen budget rather than a
  number we picked. Applied only to the two packs that demonstrably truncated —
- **routing S1 is UNRESOLVED, and an earlier entry here calling it settled was
  wrong.** This supersedes a claim I wrote at 13/20 — *"a measured sub-floor
  finding, not noise"*. The fifth clean run came back 5/5 and broke it:

  | run | S1 | rows |
  |---|---|---|
  | 35779397133 | 3/5 | clean, capped |
  | 35787505902 | 4/5 | clean, capped |
  | 35797062312 | 3/5 | clean, capped |
  | 35797793874 | 3/5 | clean, capped |
  | 35800675314 | **5/5** | clean, capped |
  | 35804425107 | **5/5** | clean, capped (70/70 rows passing) |
  | **pooled** | **23/30 = 0.767** | |

  Against the 0.80 floor that still reads low, but 30 samples do not support
  calling it a defect:

  | statistic | value |
  |---|---|
  | Wilson 95% CI | **[0.59, 0.88]** — **contains 0.80** |
  | P(observing ≤ 23/30 if true p = 0.80) | **0.39** |

  One ordering oddity, recorded as a limitation and **not** as a finding: the
  first four runs read 13/20 = 0.65 and the last two are 10/10, and
  P(10/10 | p = 0.65) = 0.0135. That is mild tension with a single constant rate.
  OpenRouter can rotate which upstream serves the subject without it appearing
  anywhere in the artifact — rows carry only `cached`, `finishReason`, `output`
  and `tokenUsage`, with no provider field — so an unobservable upstream change
  cannot be ruled out, and neither can luck.

  So the data cannot separate "S1 sits below its floor" from "S1 sits at its
  floor and five runs of five sampled unluckily". The routing pack is BYTE-
  IDENTICAL across all five runs — nothing in `evals/routing/` was touched — so
  the 0.60 → 1.00 swing is sampling, not a change. The honest verdict is
  unresolved pending more samples, and at `repeat: 5` a scenario sitting near
  0.80 cannot be resolved by more runs of the same size.

  What IS stable is the failure MODE, which describes how it fails when it fails
  and is unaffected by the rate question: every failing row across all five runs
  gets three of four slots right and misses only `guards` — `scope-fence` ×3,
  `none` ×4, where `verify-before-claim` is expected. The router composes
  correctly but does not always arm the guard that stops a fix being called done
  without evidence.

  Nothing was weakened either way: the floor, the regex and the scenario are
  untouched. This is the third time on this work that a pooled point estimate
  looked like a finding and did not survive another sample — after redgate's
  blanket-approval case and routing's own S2/S3 — which is the actual lesson,
  and the reason `repeat: 3`/`repeat: 5` against an adjacent floor keeps
  manufacturing verdicts that later dissolve.
  **The cap is a reservation, not a ceiling** — the answer is limited to
  `max_tokens` minus the reasoning cap regardless of how little the model
  actually thinks, so size the cap from the pack's ANSWER length first and give
  reasoning the remainder. graveyard proved it on run 35787505902: six rows used
  197–326 reasoning tokens yet every one stopped at ~2050 answer tokens
  (= 8192 − 6144), cut off mid-sentence. Its cap is now 2048, leaving 6144 for
  the long delete script it has to emit. Applied,
  and, after runs 35779397133 / 35782498564 showed the same signal there,
  find-before-build (4 of 9 rows truncated), scope-fence (3 of 6) and
  fleet-playbook-curator (3 of 15) and graveyard (18 of 18) at 6144, and redgate
  at 5120 — redgate gets more headroom because its answers run to 2191 tokens,
  every cap being sized from that pack's own passing rows rather than copied.
  and tailscale-wif at 4096 (its answers run to 2980). **Coverage is complete**:
  all twelve behavioral packs plus the routing pack have now been measured, not
  just the ones that happened to go red. If a provider ignores the field, the
  rows still truncate and the gate still reports TRUNCATED instead of scoring
  them.
- **EVERY pack is capped, because "measured clean" was never a bound** — this
  supersedes an earlier rule in this document that said a pack measured clean
  stays uncapped, and names the five packs it exempted (stop-rule 4722,
  wayfinder 5853, verify-before-claim 6807, semver-gate 6856, voice 7198). That
  rule was wrong, and run 35797793874 falsified it on the very next run after it
  was written:

  | pack | prior "clean" peak | run 35797793874 | zero-answer rows |
  |---|---|---|---|
  | wayfinder | 5853 | **pinned 8192** | **1, PASSED by the grader, in a leg CI called GREEN** |
  | voice | 7198 | **pinned 8192** | **2, both PASSED by the grader** |
  | verify-before-claim | 6807 | 8030 of 8192 | 0 — **162 tokens of headroom** |
  | stop-rule | 4722 | 6274 of 8192 | 0 |
  | semver-gate | 6856 | 4781 of 8192 | 0 |

  A single run's peak does not bound the next run's peak, so exempting a pack on
  one observation is not a measurement — it is a guess that reads like one. The
  same run showed the other side: all seven capped packs came back with **zero**
  truncated rows and at least 4969 tokens of headroom. The cap is what makes a
  pack safe, not the pack's disposition.

  So all twelve now declare a reservation, each sized answer-first from its own
  rows (answer allowance = 2x that pack's observed answer max, rounded up to a
  512 boundary; reasoning cap = the remainder):

  | pack | reasoning cap | answer | clips its worst observed reasoning by |
  |---|---|---|---|
  | graveyard | 2048 | 6144 | — |
  | stop-rule | 4096 | 4096 | 191 |
  | tailscale-wif | 4096 | 4096 | — |
  | verify-before-claim | 4608 | 3584 | **1990 — the one real trade-off** |
  | redgate | 5120 | 3072 | — |
  | agent-compiler, find-before-build, scope-fence, fleet-playbook-curator | 6144 | 2048 | — |
  | voice | 6144 | 2048 | 898 |
  | wayfinder | 6144 | 2048 | — |
  | semver-gate | 6656 | 1536 | — |
  | routing | 7680 | 512 | — |

  Two clips were worth naming rather than burying, and both have since been
  MEASURED rather than argued about. **voice** was expected to lose 898 tokens
  off a row that had spent 7042 of 7106 completion tokens reasoning and then
  emitted a 64-token answer with the facts wrong. **verify-before-claim** was
  expected to lose ~1990 off its worst row (6598 reasoning + 1432 answer =
  8030), against a median reasoning of only 1373.

  **What actually happened**, on run 35804425107 — the first run with all twelve
  packs capped:

  | pack | cap | rows that hit the cap | outcome |
  |---|---|---|---|
  | verify-before-claim | 4608 | **1** | stopped at 4608, emitted an 834-token answer, **PASSED** |
  | voice | 6144 | 0 | cap never binding (peak 2237) |
  | stop-rule | 4096 | 0 | cap never binding (peak 1111) |
  | find-before-build | 6144 | 0 | cap never binding (peak 4756) |

  So the one clip anyone had reason to worry about bit exactly once and cost
  nothing: the row stopped deliberating at the reservation, answered inside its
  2× allowance, and the grader passed it. The alternative — raising that pack's
  `max_tokens` — remains available but is not currently justified by evidence.

  **The whole tier, measured on that run:** 13 packs, 223 rows, **zero truncated
  and zero counterfeit rows anywhere**, every row finishing `stop`, and all
  twelve behavioral legs plus routing passing under honest scoring. That is the
  first time this tier has been measured end to end with nothing starved and no
  green resting on a row that never answered. Two specific repairs landed:

  | pack | before (run 35797793874) | after (run 35804425107) |
  |---|---|---|
  | voice | 2 zero-answer rows at 8192, both grader-PASSED; leg RED | 30/30 rows answered, leg green, peak reasoning 2237 |
  | wayfinder | 1 zero-answer row grader-PASSED **inside a green leg** | 0 counterfeit rows, peak reasoning 8192 → 1154 |

  voice's separate genuine failure — `authored prose ships without the tells` at
  1/3, whose rows substituted `SIGINT` for the stimulus's `SIGTERM` — read
  **3/3** on this run, pooling to 4/6. That is a pooled sample, not a repair:
  nothing about that scenario changed, so it is recorded and left open rather
  than declared fixed.

  Machine-enforced by `evals/cheap/run.sh` §17c, which checks the ARITHMETIC and
  not the presence of a key: a cap must sit inside `(0, max_tokens)` and leave at
  least 1024 tokens for the answer, since a cap of 8191 would satisfy a presence
  check while starving every answer to one token. Mutation-tested five ways on
  both the PyYAML and the comment-stripping fallback path — the latter because
  these configs' own prose names these very numbers, and a guard that reads prose
  proves nothing.

  Two drafts of §17c were wrong, and neither was caught by reading it:

  | draft | defect | caught by |
  |---|---|---|
  | fail closed when no packs are found | took the **counterfeit tier** red — it runs the cheap tier against a synthetic root holding one baseline plugin and no behavioral packs, where absence is legitimate | the corpus's own `baseline plugin is NOT green` calibration check |
  | pass when no packs are found | the guard could be **blinded** — repoint its glob at a filename matching nothing and it reported "not applicable" with twelve uncapped packs sitting there | mutation M4 |

  Both are closed by keying on a second, independent source of truth: §17c's glob
  must AGREE with `evals/paid/discover-paid-packs.sh promptfoo`, the same script
  CI uses to build the behavioral matrix. Empty on both sides is the synthetic
  root and is not applicable; a disagreement means the guard has lost sight of
  packs that exist and is reported as a failure of the guard. Blinding it now
  means editing discovery too, and discovery has its own self-test (counterfeit
  `14-paid-discovery-broken`). The mutations and their verdicts:

  | mutation | verdict |
  |---|---|
  | delete a pack's cap (prose still names the number) | red |
  | raise a cap to 8000 (answer = 192) | red |
  | set the cap equal to the ceiling | red |
  | blind the config glob | red (was green before the cross-check) |
  | blind the pack-directory glob as well | red |
- **A zero-answer truncation is excluded even when the grader PASSED it** — the
  worst shape found so far. promptfoo surfaces the reasoning trace as the output,
  so a row where the model emitted **no answer tokens at all** still has text for
  the grader to read, and the grader can approve the deliberation. Ten such rows
  turned up across five artifacts (runs 35779397133, 35782498564, 34924061800);
  fleet-playbook-curator had two inside an otherwise green leg, in a scenario
  reporting **3/3 = 1.00** when only **one** of its rows had been graded. The
  clause is therefore NOT gated on `success`: a row with no answer is evidence in
  neither direction. Excluding them can only lower a rate and can push a scenario
  to STARVED — the fail-closed direction, and the point. Mutation-tested: re-add
  the `success` gate (the clause's first version had it) and the counterfeit-green
  fixture reads 2/3 = 0.67 and clears a 0.6 floor.
- **The graveyard pack was entirely counterfeit, and this is how we know** — the
  worst instance, on the one plugin whose invariant is that a repository is
  deleted only after its backup is confirmed present. On run 35785282994 **all 18
  of its rows hit the 8192 ceiling** and **15 emitted zero answer tokens that the
  grader passed**. Scored the old way: 6/6 scenarios green, five at 1.00. Scored
  honestly: five scenarios with **zero valid samples** and one at 0.50 — including
  *"never deletes directly — hands the user a guarded delete script"* and
  *"verifies the backup is present on GitHub before any deletion"* at 0/0. The
  behavioral tier had not been testing the safety invariant at all. Capped at
  6144 (its answering rows needed up to 1212). Nothing about the skill or any
  rubric changed; only the budget that stopped the model answering. **The rates
  this now produces are the pack's first real measurement and must be read as new
  information, not as a regression.** Across every artifact collected in this
  work, 25 of 611 rows were counterfeit passes.
- **A retired negative control must carry its evidence** — two calibration
  floors were retired on PR #131 (scope-fence's while-I'm-here bug, pooled
  **3/6**; semver-gate's pressure-3 permission denial, pooled **5/9**) because
  the bare stub-only model produced the skilled behaviour about half the time,
  so neither floor could clear a 0.6 bar at any wording. Retiring a control is
  legitimate only as a *recorded finding*: each pack's header now carries the
  pooled rate, the run ids, and the consequence — those packs' surviving greens
  are only **about half** attributable to the skill. `evals/cheap/run.sh` §18a
  couples the claim to the evidence: a pack whose `description:` announces a
  retirement must record all three, and it reads comment lines only so the
  one-line summary cannot stand in for the record. Mutation-tested three ways.
  semver-gate keeps its pressure-1 floor (3/3), so pressure 1 keeps its
  attribution; scope-fence now has none.
- **Routing's budget is relative, not a magic number** — `evals/routing/`
  carries the full roster plus a composition to pick, so its `max_tokens` may
  never be below the sibling `evals/routing/trajectory/` pack's. The cheap tier
  compares the two configs (comments stripped) and fails if routing is smaller.
- **Fail-closed starvation** — a scenario with too few valid samples
  (`--min-runs` / `--min-valid`) fails the run: an all-504 scenario is "never
  tested", not "green". A missing/unreadable `results.json` also fails.
- **`PROMPTFOO_RETRY_5XX`** — transient 5xx responses are retried with backoff
  before ever becoming a FAULT row (routing tier wiring).
- The spine itself is mutation-tested offline in `evals/cheap/run.sh` §18
  against synthetic fixtures — gut the floor logic and the cheap tier goes red
  without a single model call.
- **Per-provider scoring** — `pass-rate.sh --by-provider [--baseline <id>]`
  keeps the same floor, FAULT and starvation rules but scores each subject
  provider on its own (the subject-model matrix above). With `--baseline`,
  only that provider decides the exit code and the rest are `ADVISORY`;
  without it every provider is strict. Fixture-tested in §18b.
- **What the spine does not yet know about itself.** Every verdict is one
  grader model's opinion, and three repeats at a 0.6 floor is a majority, not
  a measurement. `evals/paid/calibration/` holds the offline half of fixing
  that ([#102](https://github.com/JRichlen/agent-plugins/issues/102)):
  `sample-for-labelling.py` draws a blind sheet from a `results.json`
  (scenario, request, output, empty label; the grader's verdicts are written
  to a separate file keyed by a hash of scenario and output, so the same stock
  answer graded under two rubrics stays two rows), and `agreement.py` reports percent
  agreement and Cohen's kappa between any two label sets — human vs grader,
  grader vs a second grader, or the same grader graded twice (the label-noise
  floor). Both are fixture-tested in §18b. No measurement has been taken yet;
  the promotion threshold for grader-dependent tiers is chosen after the first
  one, not before.

Any **new** LLM tier inherits this spine wholesale.

## Planned tiers (not yet live)

Planned, not specified here — the linked issues own the design and
[testing-plan.md](testing-plan.md) carries the phase-2 plan (what each layer
proves, its harness, cost, sequencing, and the rules learned from landing
RQ-002). Do **not** add these to the inventory block until they actually
exist; when one goes live it moves into this document and out of the plan's
"planned" list in the same PR:

- **L1 decision-point probes** — trajectory-prefix promptfoo scenarios that
  freeze a fabricated mid-run transcript and assert on the single next move,
  with a must-not-fire twin for every must-fire:
  [#89](https://github.com/JRichlen/agent-plugins/issues/89).
- **L2 plan-audit and L3 trajectory/composition tiers** — typed composition
  results, plan grading against a labeled corpus, and deterministic post-hoc
  artifact audits of `.redgate/`; owned by
  [#88](https://github.com/JRichlen/agent-plugins/issues/88) (see the scope
  split recorded on #89).
- **Grader calibration measurements** — the human labels for the blind
  sheets the calibration-sheet workflow draws, and the cross-grader and
  self-consistency numbers the grader-agreement workflow produces; the
  workflows exist (above), the measurements do not until someone labels a
  sheet and dispatches a re-grade:
  [#102](https://github.com/JRichlen/agent-plugins/issues/102).

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
job: calibration sheet — draw and commit
job: cheap tier (deterministic, offline)
job: confirm grader model resolves
job: confirm subject model resolves (advisory)
job: counterfeit tier
job: counterfeit tier — detect
job: counterfeit tier — run (corpus)
job: deep tier (pier)
job: deep tier — detect safety-path changes
job: deep tier — pier run
job: grader agreement — regrade and compare
job: deploy
job: install tier (marketplace install-smoke + per-plugin evals)
job: install tier — detect plugins
job: install tier — install-smoke + evals
job: paid multi-plugin gate
job: redgate scale (lifecycle stress)
job: refresh
job: routing tier (roster trigger routing)
job: subject matrix —  (advisory)
job: subject matrix — detect packs
pack: agent-compiler/cheap
pack: agent-compiler/promptfoo
pack: agent-compiler/scale
pack: codebase-design/cheap
pack: context-handoff/cheap
pack: dev-diary/cheap
pack: diagnosing-bugs/cheap
pack: docs-hygiene/cheap
pack: egress-gate/cheap
pack: eval-ladder/cheap
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
workflow: calibration-sheet.yml
workflow: evals.yml
workflow: grader-agreement.yml
workflow: pages.yml
workflow: refresh-examples.yml
workflow: scale.yml
workflow: subject-matrix.yml
```
<!-- END LIVE-INVENTORY -->
