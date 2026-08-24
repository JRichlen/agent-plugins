# egress-gate

Before any call that transmits repo or user content off-machine (posting a comment, pushing a branch, calling an external API with file contents in the payload), state what is being sent and to whom — permission modes gate the call, this gates the content. Use whenever output leaves the machine to a destination the user didn't name in this task.

## Install

```
/plugin marketplace add JRichlen/agent-plugins
/plugin install egress-gate@jrichlen
```

## Status

Implemented. `evals/cheap/checks.sh` carries real deterministic checks for
this plugin's invariant (see `AGENTS.md`) and runs as part of the
marketplace cheap tier.

No behavioral (promptfoo) pack ships for this plugin, deliberately: its
invariant (caution about what rides in outbound content) sits squarely inside
base-model safety training, the exact non-discriminating shape documented
six-for-six in verify-before-claim's pack header — a calibration stub would
pass unaided and the pack would measure the model, not the skill. Add one
only with a scenario argued in writing to genuinely diverge from the
naturally-helpful/naturally-cautious default.

## License

MIT
