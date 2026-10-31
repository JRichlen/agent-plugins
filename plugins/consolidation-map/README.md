# consolidation-map

Map a catalog consolidation by unit of work, not by file: one verb per entity, counts that must reconcile. Use for a "meta diff" or when merging or pruning plugins, skills, services or packages.

## Install

```
/plugin marketplace add JRichlen/agent-plugins
/plugin install consolidation-map@jrichlen
```

## Status

Implemented. `evals/cheap/checks.sh` carries real deterministic checks for
this plugin's invariant (see `AGENTS.md`) and runs as part of the marketplace
cheap tier. There is no behavioral (promptfoo) pack yet.

## License

MIT
