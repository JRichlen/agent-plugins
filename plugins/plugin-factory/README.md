# plugin-factory

Scaffold a new plugin for this marketplace in one command. A deterministic
generator emits a valid, wired-in, **red-by-default** skeleton so adding a plugin
is a solved step instead of a dozen hand-edits.

## Install

```
/plugin marketplace add JRichlen/agent-plugins
/plugin install plugin-factory@jrichlen
```

## Use

Invoke the skill — `/new-plugin`, or just describe the plugin you want to build
and the `plugin-factory` skill will trigger. It runs an invariant-first interview
(what must always/never happen?) and then the generator:

```sh
skills/plugin-factory/scripts/scaffold-plugin.sh my-plugin \
  --description "What it does and when to reach for it." \
  --invariant   "The one thing that must always hold."
```

That produces `plugins/my-plugin/` and adds its marketplace entry.

## What you get

```
plugins/my-plugin/
  .claude-plugin/plugin.json      # valid manifest, name matches dir, v0.0.1
  skills/my-plugin/SKILL.md        # frontmatter + invariant-first "## Invariant"
  commands/my-plugin.md            # command stub
  AGENTS.md                        # cross-harness entry point
  CLAUDE.md, GEMINI.md             # symlinks -> AGENTS.md
  README.md
  evals/cheap/checks.sh            # RED-BY-DEFAULT stub (fails closed)
```

and a new entry appended to `.claude-plugin/marketplace.json`.

## Why red-by-default

The generated eval fails closed on purpose: a plugin only shows green once a
human replaces the stub with real deterministic checks for its invariant. That
guarantees no plugin ever ships with zero safety coverage. Run `evals/cheap/run.sh`
— a freshly scaffolded plugin is *expected* to be red until you write its checks.

## Reconcile marketplace changes

When `.claude-plugin/marketplace.json` conflicts with another contribution:

1. Compare the current source and both changes by plugin name and source path.
   Preserve distinct intended active registrations, deduplicate the same
   identity, and resolve version/description differences against the owning
   plugin manifest. Never keep conflicting duplicates or restore retired entries
   just to remove conflict markers.
2. Check that each retained source resolves to one matching plugin manifest and
   that its name, version and description agree. Do not discard a distinct new
   plugin merely because another entry was added nearby.
3. From the repository root, run `bash ci/install-smoke.sh` and
   `bash evals/cheap/run.sh`. Report actual failures and inspect the resulting diff.

Fetch and inspect trunk before choosing how to integrate it. For a published
stack, coordinate any rebase/history rewrite first; the
[CI stack guide](../../ci/README.md#working-in-a-pr-stack) owns those operations.

## License

MIT
