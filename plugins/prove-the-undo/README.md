# prove-the-undo

Rehearse the rollback before any irreversible action: name the specific restore path and demonstrate it works — never proceed on the strength of 'a backup exists'. Use before deletes, drops, force-pushes, migrations, or any action semver-gate classifies as MAJOR.

## Install

```
/plugin marketplace add JRichlen/agent-plugins
/plugin install prove-the-undo@jrichlen
```

## Status

Implemented. `evals/cheap/checks.sh` carries real deterministic checks for
this plugin's invariant (see `AGENTS.md`) and runs as part of the
marketplace cheap tier.

## License

MIT
