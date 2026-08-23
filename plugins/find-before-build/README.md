# find-before-build

Search for the existing implementation before writing a new one: name the searches you ran for an existing helper, abstraction, or pattern and what they returned, before introducing anything new. Use before adding a utility, wrapper, config knob, or dependency to a codebase you did not write end-to-end.

## Install

```
/plugin marketplace add JRichlen/agent-plugins
/plugin install find-before-build@jrichlen
```

## Status

Implemented. `evals/cheap/checks.sh` carries real deterministic checks for
this plugin's invariant (see `AGENTS.md`) and runs as part of the
marketplace cheap tier.

## License

MIT
