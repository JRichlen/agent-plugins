# docs-hygiene

Audits CLAUDE.md/AGENTS.md/SKILL.md instruction files against current repo state, catches claims that have gone stale (a renamed path, a dropped command, a policy that changed) before they get trusted or acted on, and resolves contradictions between layered instruction files (root vs nested, SKILL.md vs its parent AGENTS.md) down to one explicit kept version instead of leaving both to stand. Use before trusting or propagating any instruction-file claim you haven't personally re-checked, whenever onboarding a repo's docs for the first time, right after a refactor/rename/policy change that could invalidate what's documented, or whenever two instruction files (or an instruction file and the actual repo) say different things about the same fact. Trigger phrases: 'audit the docs', 'is AGENTS.md still accurate', 'clean up CLAUDE.md', 'these instructions contradict each other', 'refactor the AGENTS.md files'.

## Install

```
/plugin marketplace add JRichlen/agent-plugins
/plugin install docs-hygiene@jrichlen
```

## Why this exists (with real examples, not hypotheticals)

An instruction file that's checked into the repo and formatted like every
other doc *looks* authoritative whether or not it's still true. That gap —
present and well-formatted is not the same thing as current — is exactly
what this plugin exists to close, and this marketplace has two real,
git-verifiable incidents of it happening — one of them history rather than
present tense, because a present-tense claim about a table that gets
rebuilt every time a plugin ships would itself go stale the next time one
did:

- **This repo's own root `README.md`, historically.** Right before the fix
  commit `1d6d73f`, the plugin table named only 2 of the 11 plugins then
  registered in `.claude-plugin/marketplace.json` (`graveyard` and
  `tailscale-wif`) — present, well-formatted, and quietly wrong since
  roughly the third plugin shipped, and nothing caught it because nothing
  re-checked the README's claim against the manifest it was describing. The
  fix commit `1d6d73f` found it, rebuilt the table from `marketplace.json`,
  and added a permanent regression guard in `evals/cheap/run.sh` (the
  "README documents every registered plugin" check): every plugin
  registered in `marketplace.json` must be named in `README.md` or the
  cheap tier fails closed. That fix landed *before this plugin existed*, so
  the incident is history, not a live bug — verify it yourself with
  `git show 1d6d73f^:README.md` against
  `git show 1d6d73f^:.claude-plugin/marketplace.json`.
- **[The retired fleet-playbook-curator README](https://github.com/JRichlen/agent-plugins/blob/0f0eb6f172e1e2d06396011a78e689f06ca48969/plugins/fleet-playbook-curator/README.md)** asserted a "Freshly
  scaffolded... intentionally RED" status long after its evals were written
  and green across all three tiers. Its README now records that correction
  in place instead of quietly editing it away — the "explicitly flagged"
  half of this plugin's invariant, demonstrated by a sibling plugin before
  this one existed to formalize it.

Neither of those is contrived for this README. Both are real, git-verifiable
incidents in this repository's history.

## What this isn't

- **Not a scheduled cross-repo index.** Such an index points to other repositories and may declare `source-of-truth: false`; docs-hygiene repairs the actual instruction files in one repo on demand. The former fleet-playbook-curator package is retired; this skill does not replace its discovery, cron, or citation-ledger automation.
- **Not plugin-factory.** plugin-factory generates a new plugin's
  `SKILL.md`/`AGENTS.md` skeleton at scaffold time. docs-hygiene audits
  *existing* instruction files, at any later time, in any repo.

See `skills/docs-hygiene/SKILL.md` for the full boundary statement and the
staleness-detection heuristic.

## Status

Implemented and green on the cheap eval tier — deterministic fixture-backed
checks that assert stale claims get corrected or flagged (never silently
repeated) and that cross-file contradictions resolve to one explicit kept
version (never left standing for both to survive).

## License

MIT
