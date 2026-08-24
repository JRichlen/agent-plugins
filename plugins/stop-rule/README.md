# stop-rule

A halting discipline for iterative fix loops: after a bounded number of failed attempts at the same objective, stop and report the state with hypotheses — never make attempt N+1 on momentum. Use when re-pushing to fix CI, retrying a flaky repro, or any loop where each retry is a guess rather than a diagnosis.

## Install

```
/plugin marketplace add JRichlen/agent-plugins
/plugin install stop-rule@jrichlen
```

## Status

Implemented. `evals/cheap/checks.sh` carries real deterministic checks for
this plugin's invariant (see `AGENTS.md`) and runs as part of the
marketplace cheap tier.

## License

MIT
