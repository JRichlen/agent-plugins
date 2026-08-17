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

## License

MIT
