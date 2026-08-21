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
what this plugin exists to close, and this marketplace already has two live
examples of it happening for real:

- **This repo's own root `README.md`** names only 2 of the 11 plugins that
  actually exist in `.claude-plugin/marketplace.json` (`graveyard` and
  `tailscale-wif` — check the install table). It's been quietly wrong since
  roughly the third plugin shipped, and nothing caught it because nothing
  re-checks a README's claims against the marketplace manifest it's
  describing.
- **`plugins/fleet-playbook-curator/README.md`** asserted a "Freshly
  scaffolded... intentionally RED" status long after its evals were written
  and green across all three tiers. Its README now records that correction
  in place instead of quietly editing it away — the "explicitly flagged"
  half of this plugin's invariant, demonstrated by a sibling plugin before
  this one existed to formalize it.

Neither of those is contrived for this README. Both are real, currently
verifiable state in this repository.

## What this isn't

- **Not fleet-playbook-curator.** That plugin builds and maintains a
  separate, cron-driven index repo describing a *glob of other repos* from
  the outside — it never edits a fleet member's own instruction files, and
  explicitly declares `source-of-truth: false`. docs-hygiene is the inverse:
  it audits and edits the instruction files that already live *inside* one
  target repo, in place, on demand, with no cron and no separate repo.
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
