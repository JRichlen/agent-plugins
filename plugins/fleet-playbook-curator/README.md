# fleet-playbook-curator

Deploy daily GitHub automation that curates a living, self-invalidating operating index (a 'fleet playbook') for a glob of repos — always pointing at the repos as the source of truth, never posing as it.

## Install

```
/plugin marketplace add JRichlen/agent-plugins
/plugin install fleet-playbook-curator@jrichlen
```

## Status

Freshly scaffolded. The cheap eval is intentionally RED until you replace
`evals/cheap/checks.sh` with real deterministic checks for this plugin's
invariant (see `AGENTS.md`).

## License

MIT
