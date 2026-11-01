# delegated-intelligence

Run large or multi-part work in background subagents so the main thread keeps talking with the user. Covers model tiers, briefs, handbacks, budgets and recovery. Not for small known-file jobs.

## Install

```
/plugin marketplace add JRichlen/agent-plugins
/plugin install delegated-intelligence@jrichlen
```

## What is in it

- The coordinator method: `skills/delegated-intelligence/SKILL.md` (an
  inline-or-delegate rule, Haiku/Sonnet/Opus tiers, a self-contained brief
  contract, tool scoping, search budgets, short handbacks to files, disjoint
  outputs, a task board, recovery after failure or restart, verification and a
  trust boundary). Entry point: `/delegated-intelligence`.
- Templates and the recovery playbook under
  `skills/delegated-intelligence/references/`.

PORTABILITY: prose and files only. On a harness without background subagents, one
agent runs each brief as a separate pass that starts from the files.

## Neighbours

`jori` coordinates complex work with bounded agents, evidence and dashboards;
`context-handoff` decides at a phase boundary whether to delegate;
`wave-research` supplies a staged research plan. This skill is how a delegated
job is briefed, budgeted, handed back and recovered. See the skill's
`## Not this`.

## Status

Implemented. `evals/cheap/checks.sh` carries deterministic checks for this
plugin's invariant (see `AGENTS.md`) and runs as part of the marketplace cheap
tier. There is no behavioral (promptfoo) pack yet.

## License

MIT
