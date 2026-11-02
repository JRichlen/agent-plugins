# Ask your agent to install one method

Copy the base prompt, then add one route below. Start with
`find-before-build`; it needs search tools, not a server, hook or worker.
For choices and support limits, see [Installation](installation.md).

## Base prompt

> Help me try one method from JRichlen/agent-plugins. Inspect my host, version,
> OS, project and existing installations first, without changing them. Read
> the current official host guidance and the selected source revision. Choose
> the smallest useful session or project-local trial, and ask only for choices
> or authority I have not already supplied. Do not silently substitute user-wide
> installation or overwrite an existing skill/configuration.
>
> Resolve and record a full source commit. Inspect the entire selected unit:
> required resources, references, hooks, lifecycle scripts, services, network
> access and writes. Show the specific change/removal plan before any action
> requiring approval. Preserve unrelated settings and my edits; never use force
> or trust bypasses as a repair shortcut. Do not adopt Core globally, start a
> service, add credentials or run paid evaluation suites without authorization.
>
> Within the authorized scope, complete the trial. Verify discovery and one
> harmless read-only invocation, then report exact identifiers, changed paths,
> source/host versions, results, limitations and how to undo these changes.
> Registration, installation, enablement and invocation need separate receipts.

## Claude session trial

> Use a disposable, pinned repository clone. Check that this Claude version
> supports `--plugin-dir`, inspect `plugins/find-before-build`, and load only
> that plugin for this session. Apply the read-only exercise from
> `docs/getting-started.md`. Disclose precedence over any installed copy. End the
> session to stop loading the trial; do not remove an unrelated installed copy.

## Codex project skill

> Confirm the destination project. Inspect the starter SKILL for required files;
> copy only its checked instruction file plus the repository LICENSE into a new
> `.agents/skills/find-before-build/` directory. Refuse an existing directory or
> symlink until we decide how to preserve it. Do not use a user-wide skills path.
> Verify discovery, then apply it to this project's task using two distinct
> read-only searches; show the commands, findings and reuse recommendation. If
> the task is unknown, ask for it or use the disposable clone's first-task guide.
> For undo, preserve edits and remove only the recorded new files and empty
> directory, then refresh discovery. Do not apply this folder-copy recipe to
> delegated-intelligence or another method
> without checking its dependencies separately.

## Native marketplace

> Inspect the installed host's help and the source's actual manifests. Separate
> marketplace registration from package installation and enablement. Pin the
> registration where supported. Explain user-cache/settings effects, choose one
> method, and use the host's supported installer/UI. Do not invent a Codex
> plugin-install CLI command or edit global configuration as a shortcut. Verify
> the installed identifier and invocation, then give scope-matched removal steps.

## APM project route

> Inspect APM's version/help, project manifest/lock, target settings and lifecycle
> scripts. Select one target explicitly; start with the find-before-build skill
> subpath at a full commit and package-only `--only apm` scope. Explain planned
> writes and lifecycle effects. After authorized installation, keep the lock and
> verify frozen replay without positional additions. Inspect removal scripts and
> local edits before uninstalling; do not treat uninstall `--dry-run` as harmless.
