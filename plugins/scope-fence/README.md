# scope-fence

Keep every hunk of the diff traceable to the stated task: anything discovered outside scope is recorded as a finding (ticket, note, diary entry) — never fixed in the same change. Use when starting any bounded task, when tempted to 'fix it while I'm here', or when reviewing whether a diff crept beyond its mandate.

## Install

```
/plugin marketplace add JRichlen/agent-plugins
/plugin install scope-fence@jrichlen
```

## Status

Implemented. `evals/cheap/checks.sh` carries real deterministic checks for
this plugin's invariant (see `AGENTS.md`) and runs as part of the
marketplace cheap tier.

## License

MIT
