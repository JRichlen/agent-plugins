---
name: docs-hygiene
description: >-
  Audits CLAUDE.md/AGENTS.md/SKILL.md instruction files against current repo state, catches claims that have gone stale (a renamed path, a dropped command, a policy that changed) before they get trusted or acted on, and resolves contradictions between layered instruction files (root vs nested, SKILL.md vs its parent AGENTS.md) down to one explicit kept version instead of leaving both to stand. Use before trusting or propagating any instruction-file claim you haven't personally re-checked, whenever onboarding a repo's docs for the first time, right after a refactor/rename/policy change that could invalidate what's documented, or whenever two instruction files (or an instruction file and the actual repo) say different things about the same fact. Trigger phrases: 'audit the docs', 'is AGENTS.md still accurate', 'clean up CLAUDE.md', 'these instructions contradict each other', 'refactor the AGENTS.md files'.
  Use this skill whenever the user is working with docs-hygiene.
---

# docs-hygiene

## Invariant

A claim in an instruction file (CLAUDE.md/AGENTS.md/SKILL.md) is never trusted or propagated forward without being re-verified against current repo state first. Once observed reality contradicts an instruction, the contradicted instruction is never left in place — it is corrected or explicitly flagged in the same pass, not carried forward for later. When two or more layered instruction files disagree with each other, the audit always resolves the disagreement to one explicit kept version — it never leaves the contradiction standing for the next reader (human or agent) to trip over and silently pick a side.

Everything below exists to keep that true.

## Why this matters

For an AI agent that reads instruction files on every request, stale information doesn't just mislead once the way a stale doc misleads a skimming human — it actively **poisons the context**, because the agent has no built-in skepticism toward a file that's checked into the repo and formatted like every other doc. A human skimming CLAUDE.md brings background doubt ("is this still true?"); an agent treats every claim in an instruction file as authoritative on every single read, so one stale sentence misleads on every subsequent turn until something forces a re-check.

This is the exact same failure shape as a GitOps controller that stays green — `Ready: True` — while quietly reconciling against a stale artifact, because the controller never re-diffs its own claim of freshness against what's actually live. An instruction file fails the same way: it sits there looking authoritative — present, well-formatted, checked in — while the fact it asserts has silently diverged from reality. **Present and well-formatted is not evidence of current.** That gap is exactly why this audit exists as its own repeatable step instead of a one-time write nobody revisits.

Two real, in-repo instances of this exact failure, not hypotheticals:

- This marketplace's own root `README.md` names only 2 of the 11 plugins that actually exist in `marketplace.json` (`graveyard` and `tailscale-wif` — see the install table). It reads as complete, is well-formatted, and has been quietly wrong since roughly the third plugin was added.
- `plugins/fleet-playbook-curator/README.md` asserted a "Freshly scaffolded... intentionally RED" status long after its evals were written and green across all three tiers — stale status text asserting something demonstrably false, in a plugin whose entire purpose is refusing to assert uncited claims. (That plugin's README now records the correction in place rather than quietly editing it away — a worked example of the "explicitly flagged" half of this skill's invariant.)

## When to use this

- Before trusting or acting on any instruction-file claim you have not personally re-checked this session — a path, a command, a policy statement.
- Reading a repo's instruction files for the first time (onboarding).
- Right after any refactor, rename, move, or policy change that could invalidate something documented.
- Whenever two instruction files in the same repo could plausibly disagree — a root `AGENTS.md` vs a nested per-package/per-plugin `AGENTS.md`, a `SKILL.md` vs the `AGENTS.md` above it, or `CLAUDE.md`/`GEMINI.md` symlink targets that have drifted from what they point at.
- On explicit request: "audit," "clean up," "refactor," or "is this still true" applied to any instruction file.

## Staleness-detection heuristic

This is a per-claim checklist applied the moment a claim is about to be trusted or propagated — a fast triage, not a multi-step workflow.

1. **Does the claim have a checkable target at all?** A pure policy/judgment statement ("PRs require review") or an invariant ("X must never happen") isn't "stale" in this sense unless it asserts a *fact about current repo state* — "PRs require review, enforced by branch protection" IS checkable, because of that enforcement clause. Skip verification for claims with no checkable target; staleness detection is for factual/structural claims, not policy or judgment.

2. **Tier by drift risk, check in this order, stop once satisfied:**
   - **Paths** (highest risk — a rename or move breaks these silently and completely): does the named file/directory exist, right now, at that exact path? One `ls`/`rg`/`find` call. If a claim says "X lives in `path/to/file`," confirm the path resolves before trusting anything built on top of it.
   - **Commands** (second-highest): does the named command actually exist and do what's claimed — check the real script/Makefile target/CLI entry, not just whether the words sound plausible. `grep '"scriptname"' package.json`, `which`, or reading the actual script.
   - **Behavior/architecture claims** ("X always happens when Y"): spot-check against the real code path with one grep/read — verify against the code, never against the doc's own restatement of itself.
   - **Domain-concept/vocabulary claims** ("we call it a 'workspace,' not an 'org'"): lowest drift risk, but check when something else already smells off — e.g. the code visibly uses different terminology than the doc.

3. **Freshness cross-check:** when available cheaply, compare the instruction file's last-touched date/commit against the code path it describes — `git log -1 --format=%ai -- <doc>` vs `git log -1 --format=%ai -- <path it names>`. If the code changed more recently than the paragraph describing it, treat that paragraph as suspect by default — verify it explicitly rather than extending it good faith.

## Fixing what you find

This ties directly back to the invariant's "never left in place" clause:

- **Unambiguous fix** — the old path/command literally doesn't exist and there's one obvious current replacement (e.g. `git log --follow`, or a grep for the moved file's basename, resolves it deterministically): fix it in place immediately, in the same pass. Don't just flag it and move on — a flagged-but-unfixed stale claim is still a stale claim on the next read.
- **Ambiguous fix** — unclear which of several candidates is correct, or it's a judgment call about intent: do not guess. Surface it explicitly — name the specific claim, the specific contradiction with observed reality, and ask which is correct — rather than silently picking one or leaving it untouched "for later."

## Resolving contradictions across layered instruction files

This is a **separate, heavier procedure** from the single-claim staleness-checking above, because it means comparing multiple files against each other, not just one file against the repo. Load [`references/refactoring-workflow.md`](references/refactoring-workflow.md) **only when this audit finds — or is asked to find — two or more instruction files that could conflict**: a root `AGENTS.md` plus one or more nested `AGENTS.md`/`SKILL.md` files, or `CLAUDE.md`/`GEMINI.md` that have drifted apart from what they symlink to. For a single-file, single-claim staleness check, the inline heuristic above is sufficient — don't load the reference file for that case.

## What this isn't

- **Not fleet-playbook-curator.** That plugin builds and automatically maintains a new, separate, cron-driven index repo describing a *glob of other repos* from the outside, via `repo@sha:path` citations, and explicitly declares `source-of-truth: false` — a router that says "go check the real repo," and it never edits the fleet members' own instruction files. docs-hygiene is the inverse: it audits and edits the actual `CLAUDE.md`/`AGENTS.md`/`SKILL.md` files that already live *inside* one target repo, in place, on demand — a human or agent invokes it in the moment, no cron, no separate repo, no citation-ledger schema. Its whole point is to make those files themselves trustworthy — the opposite of fleet-playbook-curator, which is designed to never be mistaken for the source of truth in the first place. Want a standing, automated, cross-repo index that watches a fleet and stays current on its own? That's fleet-playbook-curator. Want the instruction files already sitting in this one repo fixed, de-duplicated, and de-contradicted right now? That's this skill. Asked to do this across many repos, docs-hygiene runs as N independent per-repo passes — it has no glob/fleet discovery, no cron, no citation schema, and doesn't try to grow one.
- **Not plugin-factory.** plugin-factory generates a brand-new plugin's `SKILL.md`/`AGENTS.md` skeleton at scaffold time, scoped to this one marketplace repo. docs-hygiene audits *existing* instruction files, at any later time, in any repo — general-purpose, not authoring-time, not marketplace-specific. It is not "the thing that fixes what plugin-factory generated" — it fixes any instruction file, generated by anything, any time after it's written.

## Keep it portable

The procedure above is prose, grep, and `git log` judgment — no harness-specific mechanism. It works identically whether invoked as a Claude Code skill, run by hand, or run under any other agent harness that can read a repo and run shell commands.
