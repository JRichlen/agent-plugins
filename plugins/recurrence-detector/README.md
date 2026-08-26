# recurrence-detector

Close the growth loop's DETECT step: read the exhaust every run already sheds — stop-reports, scope-fence findings, unmet criteria, diary entries — cluster it by failure shape, and surface any shape seen at least N times as a named candidate invariant with its sightings cited. Proposes; never scaffolds. Use when asking what keeps going wrong, or before adding a skill on a hunch.

## Install

```
/plugin marketplace add JRichlen/agent-plugins
/plugin install recurrence-detector@jrichlen
```

## Status

Freshly scaffolded. The cheap eval is intentionally RED until you replace
`evals/cheap/checks.sh` with real deterministic checks for this plugin's
invariant (see `AGENTS.md`).

## License

MIT
