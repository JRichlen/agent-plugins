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
