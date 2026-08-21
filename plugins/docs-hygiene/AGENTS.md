# AGENTS.md — docs-hygiene

Audits CLAUDE.md/AGENTS.md/SKILL.md instruction files against current repo state, catches claims that have gone stale (a renamed path, a dropped command, a policy that changed) before they get trusted or acted on, and resolves contradictions between layered instruction files (root vs nested, SKILL.md vs its parent AGENTS.md) down to one explicit kept version instead of leaving both to stand. Use before trusting or propagating any instruction-file claim you haven't personally re-checked, whenever onboarding a repo's docs for the first time, right after a refactor/rename/policy change that could invalidate what's documented, or whenever two instruction files (or an instruction file and the actual repo) say different things about the same fact. Trigger phrases: 'audit the docs', 'is AGENTS.md still accurate', 'clean up CLAUDE.md', 'these instructions contradict each other', 'refactor the AGENTS.md files'.

## How to use it

Read `skills/docs-hygiene/SKILL.md` and follow it — it is the authoritative
description of this plugin's workflow and the invariant it defends.

The command `commands/docs-hygiene.md` is the entry point a user invokes.

For the heavier, multi-file contradiction-audit procedure, SKILL.md points to
`skills/docs-hygiene/references/refactoring-workflow.md` — load it only once
two or more instruction files are in scope, not for a single-file check.

## The invariant this plugin defends

A claim in an instruction file (CLAUDE.md/AGENTS.md/SKILL.md) is NEVER trusted or propagated forward without being re-verified against current repo state first. Once observed reality contradicts an instruction, the contradicted instruction is NEVER left in place — it is corrected or explicitly flagged in the same pass, not carried forward for "later." When two or more layered instruction files disagree with each other, the audit ALWAYS resolves the disagreement to one explicit kept version — it NEVER leaves the contradiction standing for the next reader (human or agent) to trip over and silently pick a side.

The deterministic checks that defend it live in `evals/cheap/checks.sh` and run
as part of the marketplace cheap tier.
