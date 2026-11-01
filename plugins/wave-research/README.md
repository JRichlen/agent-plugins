# wave-research

Stress-test a contested thesis with staged, adversarial research (rival hypotheses, ACH matrix, checkpoints), plus fan-out research-and-verify Workflow templates. Not for lookups.

## Install

```
/plugin marketplace add JRichlen/agent-plugins
/plugin install wave-research@jrichlen
```

## What is in it

- The staged method: `skills/wave-research/SKILL.md` (waves, checkpoints,
  pre-registered disconfirmers, rival hypotheses, an ACH matrix, a verified
  thesis). Entry point: `/wave-research`.
- A fan-out discipline and two Claude Code Workflow scripts for a one-pass
  research-and-verify run, under `skills/wave-research/`:
  `references/fan-out-discipline.md`, `templates/derived-verify.workflow.js`
  (a sensor: raw research and verdicts) and
  `templates/pipelined-verdict-wins.workflow.js` (a decider: one reconciled
  recommendation where refuting verdicts win), with annotated walkthroughs and
  a worked example in `references/`.

These were previously the separate `orchestrate` plugin, with the
`/derived-verify` and `/pipelined-verdict-wins` commands. If you have
`orchestrate@jrichlen` installed, uninstall it and install `wave-research`
(0.1.0 or later); ask for a derived-verify or pipelined-verdict-wins run in
plain words, or invoke `/wave-research`.

## Status

Implemented. `evals/cheap/checks.sh` carries real deterministic checks for
this plugin's invariant (see `AGENTS.md`) and runs as part of the marketplace
cheap tier. There is no behavioral (promptfoo) pack yet.

## License

MIT
