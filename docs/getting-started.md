# Find the existing implementation

Try one small task before adopting more instructions: find the existing gallery
capture helper so you can reuse it. This task reads public source and needs no
model-evaluation API keys, paid test run, hook, worker or global Core adoption.
Your usual assistant session may still have its normal usage cost.

## 1. Open the repository, then choose a host

Both routes use this repository's files. Prerequisites: Git, ripgrep (`rg`),
a Bash shell (Git Bash on Windows), and an existing assistant session. Run this from a
directory where `agent-plugins-first-task` does not already exist:

```sh
git clone https://github.com/JRichlen/agent-plugins.git agent-plugins-first-task
cd agent-plugins-first-task
```

**Demonstrated route — source-loaded Codex:** open that clone in Codex. Ask it to
read `AGENTS.md` and
`plugins/find-before-build/skills/find-before-build/SKILL.md`, then apply that
method only to the task below. This is explicit source loading, not a native
plugin installation or persistent host configuration.

<details>
<summary>Alternative: Claude session trial (not qualified by this demonstration)</summary>

From the same clone, check that `claude --help` supports `--plugin-dir`, then:

```sh
claude --plugin-dir ./plugins/find-before-build
```

Apply the same read-only task below. This loads the local plugin for one session;
native end-to-end use was not run for this guide. For persistent installation,
scope, existing-copy precedence and removal, use the [installation chooser](installation.md)
or [guided-install prompt](guided-installation.md).

</details>

## 2. Give it a concrete task

> Before adding another gallery capture helper, find the implementation we
> already have. Search by purpose and by file layout. Show the searches and
> findings, then recommend reuse or a new helper. Do not edit files, install
> packages, run models or change settings.

A good answer names the searches and the usable source it found. In the recorded
Codex source-loaded application for this guide, these actual searches found:

```sh
rg -n 'capture-example|preflight_refresh' .github/workflows/refresh-examples.yml evals/paid ci/tests/test_workflows.py
rg --files evals ci .github | rg 'capture|refresh|preflight'
```

| Finding | What to do with it |
|---|---|
| `evals/paid/capture-example.sh` | Reuse the existing results-to-snapshot tool |
| `evals/paid/preflight_refresh.py` | Validate selection, tracked mode and launcher before spending |
| `.github/workflows/refresh-examples.yml` | Keep scheduled orchestration here |
| `ci/tests/test_workflows.py` | Exercise launch failures and comparison eligibility without models |

The decision was to extend the existing capture path, not create a parallel
capture helper. That is a real application of the skill's search-before-build
rule. It does not measure whether the skill improves an unaided assistant.

## 3. Check and undo

Ask for source links, then inspect them yourself. Run `git status --short` in
the disposable clone: this task should not have changed tracked files. If the
assistant changed files despite the task boundary, inspect the diff before
choosing any discard operation; do not reset unrelated work.

For source-loaded use, end the task/session; no plugin or global instruction was
installed. Keep or remove only your disposable clone after checking its path.
For the Claude session route, end the trial session. An existing installed copy
is separate; do not uninstall it as part of ending this trial. If you chose
persistent installation, use the scope-matched [removal guidance](installation.md#use-native-marketplace-packaging).

## What is qualified?

| Route | Available mechanism | Evidence here | Limits |
|---|---|---|---|
| Codex, explicit source load | Read repository instructions and selected SKILL, search with tools | This first-task search was actually performed in Codex on Windows | No native plugin install or universal host claim |
| Claude Code | Marketplace manifest, skills and commands | CI structurally resolves registered packages; command syntax follows host docs | Native end-to-end installation/use was not run for this guide |
| APM | Source/package resolution, including pinned revisions | Repository install guidance exists | No APM runtime was available in this demonstration; resolution does not supply hooks or worker tools |
| Other hosts | Read selected source when supported | Inspect the [portable adapter](../core/adapters/portable.md) | Tool invocation, hooks, enforcement and independent workers need separate qualification |

Need a real change next? Follow the [bug fix](guides/bug-fix.md),
[small feature](guides/small-feature.md) or [handoff](guides/handoff.md).
For deeper control, inspect [Core and host adapters](../core/OPERATING.md).
