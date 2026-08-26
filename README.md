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
| [**docs-hygiene**](plugins/docs-hygiene/) | Audits CLAUDE.md/AGENTS.md/SKILL.md instruction files against current repo state, catches claims that have gone stale (a renamed path, a dropped command, a policy that changed) before they get trusted or acted on, and resolves contradictions between layered instruction files (root vs nested, SKILL.md vs its parent AGENTS.md) down to one explicit kept version instead of leaving both to stand. Use before trusting or propagating any instruction-file claim you haven't personally re-checked, whenever onboarding a repo's docs for the first time, right after a refactor/rename/policy change that could invalidate what's documented, or whenever two instruction files (or an instruction file and the actual repo) say different things about the same fact. Trigger phrases: 'audit the docs', 'is AGENTS.md still accurate', 'clean up CLAUDE.md', 'these instructions contradict each other', 'refactor the AGENTS.md files'. |
| [**context-handoff**](plugins/context-handoff/) | Walk the ordered continue, clear, handoff, delegate, compact decision tree at a phase boundary, and keep any handoff artifact pointer-only — settled specs, plans, ADRs, issues, commits, and diffs referenced by path or URL, never copied inline. |
| [**codebase-design**](plugins/codebase-design/) | Before committing to a new interface — a module boundary, class API, or function signature that 2+ call sites will depend on, that crosses a service/team/persistence boundary, or that's expensive to change later — produce 3+ radically different candidate designs and compare them on depth, locality, and seam placement before picking one. Never let the first workable interface ship unexamined, and never a test at an unconfirmed seam. |
| [**wayfinder**](plugins/wayfinder/) | Chart a multi-session effort as a labeled map of typed decision tickets (grilling / prototype / research / task) with explicit dependencies and an open frontier agents self-assign into. Plans; never executes. |
| [**prove-the-undo**](plugins/prove-the-undo/) | Rehearse the rollback before any irreversible action: name the specific restore path and demonstrate it works — never proceed on the strength of 'a backup exists'. The general form of graveyard's archive-then-verify discipline. |
| [**scope-fence**](plugins/scope-fence/) | Keep every hunk of the diff traceable to the stated task: anything discovered outside scope is recorded as a finding — never fixed in the same change, and the fence widens only on the user's explicit instruction. |
| [**find-before-build**](plugins/find-before-build/) | Search for the existing implementation before writing a new one: name the searches you ran and what they returned before introducing any helper, wrapper, utility, or dependency — and never build a parallel version of a found, usable equivalent. |
| [**egress-gate**](plugins/egress-gate/) | Before any call that transmits repo or user content off-machine, state what is being sent and to whom — permission modes gate the call, this gates the content; secrets and out-of-scope content never ride in an outbound payload. |
| [**stop-rule**](plugins/stop-rule/) | A halting discipline for iterative fix loops: declare an attempt bound up front, count honestly, and at the bound stop and report state with ranked hypotheses — never attempt N+1 on momentum. |
| [**redgate**](plugins/redgate/) | Run any idea through Red Gate: human-gated rounds, each a BEGIN/MIDDLE/END process whose BEGIN emits a verifier proven able to fail before work starts, and whose END is that pinned verifier run by a party that did not do the work. Cross-harness (Claude Code, Codex, Copilot via APM); the red gate is executed, not asked. |

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
