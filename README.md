# agent-plugins

**Jordan Richlen's Claude Code plugin marketplace.**

A single marketplace hosting a growing set of plugins. Each lives under
`plugins/<name>/` with its own manifest, and is registered in
[`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json) so it can be
installed by name.

## Install

The native path below is the primary, zero-dependency way to install from this
marketplace. [Install with APM](#install-with-apm) further down is an
alternative worth knowing about if you manage the same plugin set across
multiple machines and want it to resolve identically every time.

```sh
/plugin marketplace add JRichlen/agent-plugins
/plugin install <name>@jrichlen
```

## Plugins

| Plugin | What it does |
|--------|--------------|
| [**graveyard**](plugins/graveyard/) | Archive old GitHub repositories into a single private graveyard repo as restorable git bundles, then safely delete the originals. Captures full history (branches, tags, PR refs) and never deletes an original until its backup is verified. |
| [**orchestrate**](plugins/orchestrate/) | Two reusable multi-agent orchestration templates for research-and-verify work on Claude Code's Workflow tool: fan out research over dimensions, then adversarially verify the claims that research surfaces so plausible-but-wrong findings don't survive. Ships a shared skill, two workflow-script templates (derived-verify, pipelined-verdict-wins), and a worked example. |
| [**plugin-factory**](plugins/plugin-factory/) | Scaffold a new marketplace plugin skeleton in one command: a deterministic generator emits a valid plugin.json, an invariant-first SKILL.md, cross-harness AGENTS.md symlinks, a command stub, and a red-by-default eval that fails closed until you implement real checks — then wires it into the marketplace lockfile. |
| [**tailscale-wif**](plugins/tailscale-wif/) | Set up and troubleshoot secretless GitHub Actions → Tailscale auth via Workload Identity Federation (WIF): GitHub OIDC exchanged for short-lived Tailscale tokens, with no stored API keys or OAuth secrets. |
| [**fleet-playbook-curator**](plugins/fleet-playbook-curator/) | Deploy daily GitHub automation that curates a living, self-invalidating operating index (a 'fleet playbook') for a glob of repos — always pointing at the repos as the source of truth, never posing as it. |
| [**dev-diary**](plugins/dev-diary/) | Keep a scannable developer journal that writes itself: discover a day's work from local Claude Code sessions, git commits, and prompt history; interview the user about what mattered and why; and record a tight, dated entry. Ships /dev-diary (write today) and /dev-diary-review (revise a past day). The journal is a separate private repo; this plugin is just the tool. |
| [**voice**](plugins/voice/) | Route every response element to exactly one voice: prose to human-voice (verdict-first, confidence-tagged), machine-read artifacts to machine-voice (compressed traces, logs, status lines); plus second-opinion, an offer-only subagent validation pipeline that never runs unbidden. |
| [**grill-me**](plugins/grill-me/) | Interview the user about a plan before work starts, single-session and no subagents required, walking its design tree and scaling question depth to each branch's stakes (reversibility x blast radius) while offering a recommendation at almost every step. |
| [**tracer-bullets**](plugins/tracer-bullets/) | Ship the thinnest end-to-end slice through a system first, then widen it in place — for both software delivery and open-ended investigation/research. Use when scoping new work, de-risking unknowns, or planning how to explore an unfamiliar problem before committing to a full build. |
| [**semver-gate**](plugins/semver-gate/) | Classify a candidate action as PATCH/MINOR/MAJOR (semver-style blast-radius test) before acting — act silently on PATCH, flag-and-stage MINOR, stop for explicit human sign-off on MAJOR. |
| [**verify-before-claim**](plugins/verify-before-claim/) | Never assert a fact, completion, or reproduction claim without naming and running the specific check that would prove it false, first. |
| [**diagnosing-bugs**](plugins/diagnosing-bugs/) | Diagnose a bug by writing ranked, falsifiable hypotheses before any code change, tagging temporary debug instrumentation for a zero-tolerance sweep, and gating the regression test to a red-then-green proof at the confirmed seam. Use when fixing a bug, debugging a failure, triaging an error, or the user asks to diagnose/root-cause/troubleshoot an issue. |

Every plugin ships as a Claude Code plugin **and** works with any coding agent
(Codex, Cursor, Gemini, Aider, …) via a standard `SKILL.md` + `AGENTS.md` entry
point. The core logic is plain, portable `bash`.

## Install with APM

This section is an **alternative** install path, not a replacement for
`/plugin marketplace add` above, which stays the primary zero-dependency route.
Reach for this when you provision the same set of plugins on more than one
machine and want every machine to end up running identical plugin code.

[APM](https://github.com/microsoft/apm) (the Agent Package Manager) has a
first-class `marketplace_plugin` resolver that reads this repo's
[`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json) directly —
this marketplace needs no separate APM-specific manifest to be installable
with it.

```sh
apm install JRichlen/agent-plugins/plugins/<name>
```

That form is **unpinned**: it resolves against `main` at install/update time,
which means two machines running that exact command on different days can
silently end up with different plugin code — main moves. For a reproducible
setup, pin the dependency to a commit SHA instead:

```sh
apm install JRichlen/agent-plugins/plugins/<name>#<sha>
```

For example:

```sh
apm install JRichlen/agent-plugins/plugins/graveyard#621d9bae97200b8aeb2a9525a763c04fd126e203
```

Pinning writes that exact form into `apm.yml`/`apm.lock.yaml`, so every machine
that runs `apm install --frozen` resolves to the same plugin code — not
"whatever `main` happened to be that day."

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
