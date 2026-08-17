# agent-plugins

**Jordan Richlen's Claude Code plugin marketplace.**

A single marketplace hosting a growing set of plugins. Each lives under
`plugins/<name>/` with its own manifest, and is registered in
[`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json) so it can be
installed by name.

## Install

```sh
/plugin marketplace add JRichlen/agent-plugins
/plugin install <name>@jrichlen
```

## Plugins

| Plugin | What it does |
|--------|--------------|
| [**graveyard**](plugins/graveyard/) 🪦 | Archive old GitHub repos into a single private repo as restorable git bundles, then safely delete the originals — never deleting one until its backup is verified. `/plugin install graveyard@jrichlen` |
| [**tailscale-wif**](plugins/tailscale-wif/) 🔐 | Set up and troubleshoot secretless GitHub Actions → Tailscale auth via Workload Identity Federation: GitHub OIDC exchanged for short-lived Tailscale tokens, with no stored API key or OAuth secret. `/plugin install tailscale-wif@jrichlen` |

Every plugin ships as a Claude Code plugin **and** works with any coding agent
(Codex, Cursor, Gemini, Aider, …) via a standard `SKILL.md` + `AGENTS.md` entry
point. The core logic is plain, portable `bash`.

## Repository layout

```
agent-plugins/
├── .claude-plugin/marketplace.json   # registry: every plugin, name + source path
├── AGENTS.md                         # cross-harness entry point + eval governance
├── plugins/
│   └── graveyard/                    # one directory per plugin (self-contained)
│       ├── .claude-plugin/plugin.json
│       ├── skills/  commands/  docs/
│       └── README.md
└── evals/                            # three-tier eval suite (see evals/README.md)
```

## Adding a plugin

1. Create `plugins/<new>/` with its own `.claude-plugin/plugin.json`.
2. Add a matching entry to `marketplace.json` whose `source` is `./plugins/<new>`.
3. Run `evals/cheap/run.sh` — it verifies the wiring resolves.

## Evals

Changes are gated by a three-tier eval suite, cheapest first — deterministic
checks, then behavioral (promptfoo) LLM grading, then deep sandboxed
cross-harness runs (pier). This is how the marketplace keeps safety-critical
behavior (like graveyard never deleting an unbacked repo) from regressing. See
[`evals/README.md`](evals/README.md) and the governance section of
[`AGENTS.md`](AGENTS.md).

## License

MIT — see [LICENSE](LICENSE).
