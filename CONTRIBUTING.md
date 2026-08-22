# Contributing

Thanks for contributing a plugin or a fix. The [eval suite](evals/README.md) gates
every change; run `evals/cheap/run.sh` (free, offline, must exit 0) before you push,
and read `AGENTS.md` for the layout and the eval discipline.

## ⚠️ Maintainers: the paid tiers do NOT run on fork PRs

This is a real gap you must account for when reviewing external contributions.

The **behavioral (promptfoo)** and **deep (pier)** tiers cost API spend, so their CI
jobs are gated on the PR coming from this repo, not a fork:

```yaml
if: github.event.pull_request.head.repo.full_name == github.repository
```

(`grader-model`, `behavioral-run`, and `deep-run` in `.github/workflows/evals.yml`.)
Their required aggregation gates use `if: always()`, and GitHub treats a **skipped**
required check as **green**. So on a PR from a fork:

- the cheap + counterfeit + install tiers still run and gate normally, but
- the two tiers that judge **prose** (`SKILL.md`, command markdown, `AGENTS.md`) and
  **safety scripts** (pier tasks) are **skipped and report green** — no LLM ever grades
  the change, and no adversarial sandbox ever runs it.

**Therefore: a fork PR that weakens a skill's prose or a pier guard can pass all
required checks.** When reviewing an external PR that touches any `SKILL.md`,
command/agent markdown, or `plugins/*/evals/pier/**`, a maintainer must **manually
run the paid tiers** (check out the branch and run `plugins/<name>/evals/promptfoo` /
`evals/pier/run.sh` with keys) or push the branch to this repo so CI runs them, before
merging. Green required checks on a fork are necessary, not sufficient.

## Cross-harness coverage: what CI actually runs

The deep (pier) tier's task docs advertise that a safety invariant "holds no matter
which harness drives the skill" (`claude-code`, `codex`, `gemini-cli`, `cursor-cli`).
That is the **design intent**, but **CI does not re-verify it** — `evals.yml` runs the
deep tier with `PIER_AGENTS="claude-code oracle nop"` (the driven harness plus the
oracle/nop calibration floor). The full cross-harness roster runs only on a **manual /
release** invocation:

```sh
plugins/<name>/evals/pier/run.sh            # full roster, needs each provider's key
```

So the cross-harness guarantee is a trust-based practice, not something every PR proves.
Run the full roster locally before a release, or when a change plausibly affects
harness-specific behavior.

## Adding a plugin

Use the plugin-factory scaffold (`/new-plugin`), fill the TODOs, replace the
red-by-default `evals/cheap/checks.sh` stub with real checks for your plugin's
invariant, and add a counterfeit fixture that proves the gate bites. See
`plugins/plugin-factory/` and `evals/counterfeits/README.md`.

## The tier boundary: what "cheap" can prove, and when to reach for "behavioral"

Read this before writing a check in `evals/cheap/checks.sh`. Seven rounds of
building plugins in this repo produced the same defect over and over: a check
greps `SKILL.md` for a load-bearing phrase, but that phrase also appears in a
summary section, a heading, an explanatory comment, or the check's own prose —
so the operative rule can be **deleted or inverted** and the check still
passes. Adversarial verification found this in six separate plugins. The most
recent repair pass fixed six such checks in one plugin
(`plugins/wayfinder/evals/cheap/checks.sh`, PR #54) and introduced five *new*
ones in the same pass, including one inside the very group just rewritten to
fix the defect. This is what the pattern produces by default, not a one-off.

**What a cheap-tier check actually proves.** It is a regression detector for a
*known wording*: it proves a specific string is still present somewhere in the
file. It does **not** prove the surrounding prose still means what it
claimed — any string a check greps for can be satisfied by a restatement
elsewhere in the file: a summary section, a heading, a comment, even the
check's own description text.

**The real example.** Before PR #54, one group in
`plugins/wayfinder/evals/cheap/checks.sh` (originally lines 190-213) was
titled *"wayfinder's 'Not this' claims check out against the real neighbouring
plugins"* — but it never opened wayfinder's own `SKILL.md`. It grepped the
**neighbour plugins'** files for strings wayfinder cannot influence, so no
edit to wayfinder could ever turn it red. Confirmed by rewriting wayfinder's
differentiation section to claim two flatly false things about its
neighbours; the pack stayed green (697 passed / 0 failed, unchanged).

**Two mitigations that work at the cheap tier**, both proven in that repair:

1. **Anchor to structure, not substring** — match `^### Step 4( |—)`, not the
   bare string `Step 4`, so a passing mention three paragraphs away can't
   satisfy it.
2. **Scope the scan to the section that owns the rule**, not the whole file,
   so a `## Summary` restatement can't stand in for the operative step. Known
   limit: a section-scoped check whose `awk` range marker is a *prose
   sentence* breaks the moment that sentence gets reworded — found live
   inside the very repair that introduced it.

**When to reach for the behavioral tier instead.** If what you're defending is
what the skill *means* — whether it actually steers a model's behavior, not
just whether a string survives — that's not a cheap-tier question. Three
plugins had exactly this kind of undefended invariant and now have behavioral
packs as worked examples:

- `plugins/wayfinder/evals/promptfoo/` — ticket type is fixed at creation
  (a scope surprise closes-and-links to a new, correctly-typed ticket rather
  than being relabeled in place), and dispatch requires every dependency to
  be CLOSED, recomputed fresh, never a cached flag. (PR #57)
- `plugins/semver-gate/evals/promptfoo/` — a MAJOR-classified action never
  proceeds without explicit, specific human sign-off on that exact action,
  quoted verbatim from SKILL.md's `## Invariant` section. (PR #56)
- `plugins/verify-before-claim/evals/promptfoo/` — a claim of fact or
  completion is always backed by the specific check that would prove it
  false, performed this turn, never asserted as settled. (PR #55)

Read `plugins/voice/evals/promptfoo/promptfooconfig.yaml` in full before
writing a new pack — it's the best-documented example: `SKILL.md` is injected
as a `file://` var, the subject model is cheap (OpenRouter), the grader is a
strong Anthropic model so pass/fail is trustworthy, and rubrics grade the
worst failure hardest. `evals/templates/behavioral/` is the copy-and-fill
starting point.

**The calibration requirement.** A behavioral eval that passes because the
*base model* already behaves correctly — with no skill injected, or a gutted
one — is measuring the model, not the skill. That's the same fake-check
disease one tier up, paid instead of free: a pack that stays green forever
regardless of what SKILL.md says. Every pack in this repo's behavioral tier
therefore includes a negative control: a second `skill` var pointing at a
small, generic, invariant-free stub — `calibration-stub.md`, shipped
alongside `promptfooconfig.yaml` in each of the three packs above — asserting
the invariant behavior is **absent** when that stub is injected instead of
the real skill. The deep (pier) tier already encodes this idea: see the
`oracle`/`nop` calibration floor in `evals/README.md` and `AGENTS.md`, which
CI runs on every invocation.

**Mutation testing is the acceptance criterion**, at every tier, for any new
check: break what the check defends, watch it go RED, restore it, watch it go
GREEN. A check nobody has watched fail is not a check, it's a guess. That's
how PR #54's six repaired checks were verified (each: GREEN-before on the
original `checks.sh` against the exact mutation, RED-after the fix,
restored-GREEN), and it's how `evals/counterfeits/` mutation-tests the cheap
tier itself.

One hard limit, stated plainly: **behavioral packs cannot be mutation-tested
locally**, because `OPENROUTER_API_KEY` and `ANTHROPIC_API_KEY` are CI-only
secrets — not present in a contributor's, or an agent's, local environment.
You cannot break-and-watch-red a promptfoo pack the way you can a shell
check. This is exactly why the calibration case above is mandatory, not a
nice-to-have: it's the one piece of mutation evidence a behavioral pack can
carry without ever calling the API. The "mutation" — gutting the skill — is
baked into the pack itself, and CI proves the RED side every time it runs.

## PRs touching marketplace.json: rebase and re-run before merge

`.claude-plugin/marketplace.json` is a single shared array, and every
plugin-adding PR appends to it. Two such PRs open at once will not conflict on
CI — each branch is internally consistent — but they **will** conflict on
merge, because both diffs touch the same insertion point. This has already
happened for real (semver-gate vs. tracer-bullets landed the same day) and
required manual resolution; do not assume it's a one-off.

If your PR adds, removes, or reorders a `marketplace.json` entry:

1. **Rebase onto latest `origin/main`** immediately before merge — not when you
   opened the PR. A green run from days ago proves nothing about a
   `marketplace.json` that has since moved under you.
2. **Re-run `evals/cheap/run.sh` from repo root** after the rebase, and confirm
   it exits 0. A rebase can silently drop or duplicate an entry; only a fresh
   run catches that.
3. **On a merge conflict inside the `plugins` array, keep BOTH entries.** Never
   resolve by picking one side and dropping the other — that silently
   unregisters someone else's plugin (and, per the reverse-lockfile check in
   `evals/cheap/run.sh`, orphans its directory from CI coverage entirely).
   Entry order in the array does not matter — the wiring checks in
   `evals/cheap/run.sh` are order-independent — so the safe resolution is
   always additive: keep every entry from both sides, then re-run the cheap
   tier to confirm the merged file is still valid and fully wired.
