---
description: >-
  Audits CLAUDE.md/AGENTS.md/SKILL.md instruction files against current repo state, catches claims that have gone stale (a renamed path, a dropped command, a policy that changed) before they get trusted or acted on, and resolves contradictions between layered instruction files (root vs nested, SKILL.md vs its parent AGENTS.md) down to one explicit kept version instead of leaving both to stand. Use before trusting or propagating any instruction-file claim you haven't personally re-checked, whenever onboarding a repo's docs for the first time, right after a refactor/rename/policy change that could invalidate what's documented, or whenever two instruction files (or an instruction file and the actual repo) say different things about the same fact. Trigger phrases: 'audit the docs', 'is AGENTS.md still accurate', 'clean up CLAUDE.md', 'these instructions contradict each other', 'refactor the AGENTS.md files'.
---

Invoke the `docs-hygiene` skill and follow `skills/docs-hygiene/SKILL.md`.

Audit the instruction files in scope (default: every `CLAUDE.md`, `AGENTS.md`,
and `SKILL.md` reachable from the current repo root; or the specific file(s)
named by the user). For each factual, checkable claim — a path, a command, a
behavior, a policy enforcement clause — run the staleness-detection heuristic
before trusting it: tier by drift risk (paths, then commands, then
behavior/architecture, then vocabulary), check the highest-risk tier first,
and stop once satisfied.

Fix what you find in the same pass:

- **Unambiguous** (one obvious current replacement, confirmed by `ls`/`rg`/
  `git log --follow`): correct it in place immediately.
- **Ambiguous** (a genuine judgment call): do not guess — surface the
  specific claim, the specific contradiction with observed reality, and ask
  which is correct.

If two or more instruction files disagree with each other on the same fact,
switch to the heavier procedure in
`skills/docs-hygiene/references/refactoring-workflow.md`: enumerate the full
layered set, find the contradiction, resolve it to one explicit kept version
(auto-resolving when the repo state settles it deterministically, asking when
it doesn't), and dedupe ownership so the same fact isn't restated at two
layers.

Report back which claims were checked, which were stale and fixed, which
contradictions were found and how each was resolved, and which — if any —
still need the user's judgment call.
