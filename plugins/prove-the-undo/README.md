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

No behavioral (promptfoo) pack ships for this plugin, deliberately: its
invariant (caution before irreversible/outbound actions) sits squarely inside
base-model safety training, the exact non-discriminating shape documented
six-for-six in verify-before-claim's pack header — a calibration stub would
pass unaided and the pack would measure the model, not the skill. Add one
only with a scenario argued in writing to genuinely diverge from the
naturally-helpful/naturally-cautious default.

## License

MIT
