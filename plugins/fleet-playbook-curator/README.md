# fleet-playbook-curator

Deploy daily GitHub automation that curates a living, self-invalidating operating index (a 'fleet playbook') for a glob of repos — always pointing at the repos as the source of truth, never posing as it.

## Install

```
/plugin marketplace add JRichlen/agent-plugins
/plugin install fleet-playbook-curator@jrichlen
```

## Status

Implemented and green across all three eval tiers: a deterministic cheap pack
with fixtures, a behavioral promptfoo suite, and a sandboxed `pier` task that
plants a prompt injection in a fleet member's README and asserts the curator
refuses it.

Note that the README previously claimed this plugin was "freshly scaffolded"
with an "intentionally RED" eval long after the evals were written and passing —
stale status text asserting something demonstrably false, in a plugin whose
entire purpose is refusing to assert uncited claims. Left recorded here rather
than quietly corrected.

**No fleet is currently deployed against it.** The tool works; it is between
targets. `owner` + `glob` is all it needs to run against any real fleet.

## License

MIT
