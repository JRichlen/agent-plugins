# Cost-Isolated Eval Architecture — Design

**Date:** 2026-07-10
**Status:** Approved (brainstorming) — pending implementation plan
**Author:** Jordan Richlen (JRichlen)
**Repo:** `JRichlen/agent-plugins`

## Problem

As the marketplace grows past its three current plugins (`graveyard`,
`orchestrate`, `plugin-factory`), the CI eval harness in
`.github/workflows/evals.yml` will run *every* plugin's evals on *every* PR.
That is fine for the free tiers, but it is a real cost problem for the tiers
that spend money on model calls.

The concrete failure mode: an author edits several plugins in one PR, gets most
of their evals green, and gets stuck debugging the last one. Every push
re-runs the already-passing plugins' **paid** evals — burning API budget to
re-confirm work that was already done. Multiply that across a growing plugin
count and the waste compounds.

**Goal.** A single-plugin PR only ever *pays* for that one plugin's evals.
Spanning multiple plugins on a paid tier is still possible, but it becomes a
deliberate, friction-ful, consciously-costed decision rather than an accidental
default. Fleet-wide change is expressed as many small (AI-generated) PRs, each
with isolated risk and isolated cost. The free tiers keep full coverage, and
nothing weakens the frozen branch-protection contract.

## Organizing principle

**Isolation is scoped to cost, not to tier.**

- **Free tiers** (cheap, counterfeit) — deterministic, offline, ~seconds, no
  API spend. Optimize these for *coverage and readability*. Batching them
  across all plugins costs nothing, so there is no reason to fragment them for
  cost; the only pressure is serial wall-clock, addressed where it actually
  bites.
- **Paid tiers** (behavioral via promptfoo LLM-rubric, deep via pier) — every
  run spends money. Optimize these for *spend control*: run only what a PR
  actually changed, and make multi-plugin fan-out a conscious choice.

An earlier round of analysis mistakenly aimed the isolation at the cheap tier.
The cheap tier is free; isolating it saves nothing. The cost lever is the
behavioral and deep tiers, and that is where every enforcement mechanism below
is aimed.

## Design

### 1. Cheap tier (free) — unchanged coverage, better ergonomics

- Stays a **single job**. It continues to run every *global* check
  unconditionally: the shell-syntax sweep, JSON validity, the marketplace ↔
  plugin wiring in both directions (forward wiring and the reverse lockfile
  check), and the #15 branch-protection lock.
- The per-plugin portion (section 10, which sources each
  `plugins/<name>/evals/cheap/checks.sh`) gets each plugin wrapped in a
  `::group::plugin <name>` fold so a single plugin's failure is readable in the
  Actions log without matrixing the job.
- Fail-closed auto-discovery is preserved unchanged: a newly added plugin with
  no cheap pack still turns the tier red by design.
- The stale header comment in `evals/cheap/run.sh` ("well under a second") is
  corrected to the measured figure (~1.9s at three plugins).

**Rationale.** The cheap tier is free and fast. Its only real scaling pressure
is readability of failures, which log-grouping solves without the complexity,
dynamic-name churn, and #15-incompatibility that a matrix would introduce.

### 2. Counterfeit tier (free) — matrixed now

The counterfeit tier is a whole-corpus meta-test: it copies the full cheap
tier and runs it against a set of mutated fixtures plus a baseline. Its cost is
O(plugins × fixtures) and it is already the slowest serial step (~11s today,
plausibly 30–40s at ~10 plugins). It does heavy, independent per-unit work, so
it is the one free tier where a matrix earns its runner cost.

Restructure it into the same three-job shape the deep tier already proves:

```
counterfeit-detect   → determines the matrix axis (fixtures / plugin units)
counterfeit-run      → matrix; each leg independent; NEVER individually required
counterfeit          → aggregate; needs:[detect, run]; if: always(); REQUIRED
```

The matrix legs get dynamic names (e.g. `counterfeit-run (fixture-x)`). The
**static aggregation gate** `counterfeit` is the sole required status check for
the tier, and it is what gets frozen in `required-checks.json`.

### 3. Behavioral + deep tiers (paid) — where the cost rule lives

This is the substantive work of the design.

**3a. Per-plugin paid-eval convention (new structure).**
Each plugin may ship its own paid-eval packs:

- `plugins/<name>/evals/promptfoo/` — behavioral tier
- `plugins/<name>/evals/pier/` — deep tier

Discovery is fail-closed in the same spirit as the cheap packs: the harness
knows which plugins declare a paid pack, and a plugin that declares one but
whose pack is missing/broken fails rather than silently passing. A plugin with
*no* paid pack simply contributes no paid legs (there is nothing to spend on).

Today these packs live at repo root (`evals/promptfoo/`, `evals/pier/`) and are
graveyard-specific. As part of this work, graveyard's packs move under
`plugins/graveyard/evals/`, and the harness is updated to discover packs
per-plugin. Establishing this convention is the bulk of the implementation.

**3b. Path-filtered per-plugin execution.**
Using `dorny/paths-filter` (already used by the deep tier), a PR that touches
one plugin runs only that plugin's paid evals. A failing plugin never forces
re-paying for the others' paid evals on subsequent pushes — which is the exact
waste this design exists to eliminate.

**3c. Aggregation gate, never per-leg required.**
Each paid tier follows the `detect → run(matrix, conditional) →
aggregate(if: always())` pattern. The per-plugin legs are **never** individually
required — a required check that gets skipped (because its plugin wasn't
touched) would deadlock the PR forever. Instead a single always-running
aggregation gate per paid tier is the sole required status check. This is the
only shape that simultaneously avoids the skipped-check deadlock and stays
compatible with the #15 static-name lock.

The deep tier keeps its existing manual-approval `deep-evals` environment gate;
per-plugin structuring composes with it.

**3d. Red-but-dismissible multi-plugin gate — scoped to paid tiers only.**
When a PR touches more than one plugin's *paid* surface (or a shared
paid-harness file that would fan paid evals across all plugins), a dedicated
gate check goes **red** with a message along the lines of: "This PR would run
paid evals across N plugins. Consider splitting into single-plugin PRs to keep
cost and risk isolated — or dismiss this gate to consciously proceed."

- **Dismissible**, not a hard block. This means it never vetoes its own
  introducing PR, and it needs no shared-file allowlist carve-out.
- **Scoped to paid tiers only.** A multi-plugin PR that touches only free-tier
  surfaces never trips this gate. The free tiers cost nothing, so there is no
  signal to raise there.

This gate *is* the "limit" from the original intent: it makes fleet-wide change
deliberate and costed rather than accidental, nudging toward the many-small-PRs
workflow, without imposing a hard merge-block.

### 4. #15 branch-protection reconciliation

The #15 contract freezes required-check names as literal strings in
`ci/required-checks.json`, verified by `ci/check_branch_protection.py` (literal
substring match against `evals.yml`) and applied to GitHub by
`ci/apply-branch-protection.sh`.

Every new aggregation-gate name introduced here — the counterfeit aggregation
gate, the behavioral aggregation gate, the deep aggregation gate (already
present), and the paid-tier multi-plugin gate — is a **static** name and gets
frozen in `required-checks.json`. The guard keeps asserting the static gate
names appear verbatim in the workflow; it must **never** reference the dynamic
matrix-leg names. `apply-branch-protection.sh` pushes the updated static list
into GitHub's `required_status_checks.contexts`.

## Non-goals / out of scope

- **PR #3 is not retroactively re-litigated** by this rule. Its diff spans two
  plugins, but the merge decision for it is handled separately from this design.
- **No hard merge-block** on multi-plugin PRs. The dismissible gate is the only
  enforcement mechanism; there is deliberately no rule that outright prevents a
  multi-plugin PR from merging.
- **No new behavioral/deep coverage** is written for plugins that don't have it
  yet. This design establishes the *structure* for per-plugin paid evals;
  populating it for plugins beyond graveyard is future work.

## Risks & mitigations

- **Skipped-check deadlock.** A path-filtered required check that gets skipped
  blocks a PR forever. Mitigated by making per-plugin legs never-required and
  gating on always-running aggregation jobs (§3c) — the pattern the deep tier
  already validates in production.
- **#15 drift.** A matrix redesign could tempt freezing a dynamic leg name,
  which would break on the next plugin. Mitigated by the explicit rule in §4:
  only static aggregation-gate names are ever frozen.
- **Fork PRs lack secrets.** Paid tiers already guard for this (the
  `grader-model` job is fork-guarded); per-plugin structuring preserves those
  guards.
- **Discovery false-green.** A plugin declaring a paid pack that is
  missing/broken must fail, not silently pass — mirroring the cheap tier's
  fail-closed reverse-lockfile behavior (§3a).

## Success criteria

1. A PR touching exactly one plugin runs that plugin's paid evals and no other
   plugin's paid evals.
2. A PR touching two or more plugins' paid surfaces produces a red (but
   dismissible) gate; a PR touching two or more plugins' free surfaces only does
   not.
3. No required status check can be permanently skipped into a deadlock.
4. `ci/check_branch_protection.py` passes with only static aggregation-gate
   names frozen; no dynamic matrix-leg name appears in `required-checks.json`.
5. The cheap tier's global checks still run unconditionally on every PR, and
   fail-closed discovery still reddens an unregistered/under-covered plugin.
