# AGENTS.md — agent-plugins marketplace

This repository is a **cross-harness agent plugin marketplace**. It hosts
one or more plugins under `plugins/<name>/`, listed in the root
`.claude-plugin/marketplace.json` so each can be installed with:

```
/plugin marketplace add JRichlen/agent-plugins
/plugin install <name>@jrichlen
```

## Default operating mode

Apply the shared [operating contract](core/OPERATING.md). The
[ownership index](core/ownership.json) names the canonical owner and entry/exit
of each responsibility or service; load the selected method and its needed
references. [Host adapters](core/adapters/portable.md) describe explicit adoption
and capability limits without installing or duplicating global instructions.

This `AGENTS.md` is the cross-harness entry point for the *repository* (its
layout and the eval discipline below). Each plugin ships its own `AGENTS.md`
describing that plugin's workflow — e.g. `plugins/graveyard/AGENTS.md`. Harnesses
that read `AGENTS.md` (or a symlink to it, like `CLAUDE.md`/`GEMINI.md`) will
find this governance here, and the plugin's own entry point inside its directory.

## Layout

```
.claude-plugin/marketplace.json   # lists every plugin (name, source path)
plugins/<name>/                    # one directory per plugin
  .claude-plugin/plugin.json       # that plugin's manifest
  skills/  commands/  docs/        # the plugin's contents
  AGENTS.md (+ CLAUDE.md/GEMINI.md symlinks)
evals/                             # eval harness (see docs/testing.md)
```

Adding a plugin: create `plugins/<new>/` with its own `.claude-plugin/plugin.json`
and add a matching entry to `marketplace.json` whose `source` is `./plugins/<new>`.
The cheap eval verifies that wiring.

## Repository verification and review

[docs/testing.md](docs/testing.md) is the authoritative inventory of checks,
triggers, commands, cost and evidence limits. Use its applicable tiers rather
than treating any one plugin's checks as the whole repository's discipline.

- Before every commit touching `plugins/**` or `evals/**`, run
  `evals/cheap/run.sh`; exit 0 is normally required. Report failures and their
  scope, and do not present an authorized draft with known failures as ready.
- Skill prose changes require the applicable behavioral checks. Safety-invariant,
  safety-script and release changes require the applicable deep checks. Run the
  documented pinned tools, not an unpinned replacement. Model calls require
  authority for their cost and any disclosure; do not expand paid execution.
- Keep workflow gates and required-check names intact. A skipped check is not
  evidence that its target invariant passed. No finite harness roster proves
  universal host parity; report the hosts, conditions and limits actually tested.
- Changes that add, remove, rename or re-scope a tier, workflow job or plugin
  eval pack must update `docs/testing.md` in the same PR. Its inventory is
  checked by `evals/cheap/check-testing-doc.sh`.
- Every skill-change PR needs a demonstration comment using an actual run on
  pre-existing input, showing input, output, the responsible rule and misses.
  Follow [demonstration discipline](docs/testing.md#demonstration-discipline).
  A hypothetical example or diff summary is not a demonstration. Never claim
  a run that did not happen; a missing demonstration blocks approval.

For graveyard, preserve its safety invariant: deletion follows a confirmed
backup bundle; the skill emits a guarded script for user review rather than
self-deleting, the archive is private by default, and mirror bundles preserve
full history. A change weakening this invariant must not merge until the
relevant checks pass. Consult the plugin's entry point for its procedure.
