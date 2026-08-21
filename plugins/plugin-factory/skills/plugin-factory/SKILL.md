---
name: plugin-factory
description: Scaffold a new plugin for this marketplace. Use this whenever the user wants to create, add, bootstrap, or start a new plugin — phrases like "new plugin", "scaffold a plugin", "add a plugin to the marketplace", or "I want to build a plugin that…". It runs a deterministic generator that emits a valid, wired-in, red-by-default skeleton, then guides the invariant-first interview to fill it in.
---

# plugin-factory

## Invariant

**Every plugin this factory produces starts valid, wired, and RED.** Valid: the
`plugin.json` parses and its name matches the directory. Wired: an entry is added
to the marketplace lockfile. Red: the generated `evals/cheap/checks.sh` fails
closed until a human replaces it with real checks. The factory never emits a
skeleton that could show green with zero safety coverage — a green new plugin
must be earned by writing its checks, not granted by scaffolding.

## What this does

Adding a plugin by hand means getting a dozen small things right: kebab-case
naming, a valid manifest, a SKILL.md with real frontmatter, the
AGENTS.md + CLAUDE.md/GEMINI.md symlinks that make it cross-harness, a command
stub, an eval pack, and the marketplace.json entry. Miss any one and the cheap
tier goes red (or worse, a plugin ships with no safety coverage). This skill runs
one deterministic script that gets all of it right every time.

## How to use it

### 1. Interview invariant-first

Before scaffolding, get the **invariant** — because a plugin's invariant is what
its eval defends, and it's far easier to write the checks when you named the
invariant first. Ask the user:

> What must **always** be true, and what must **never** happen, when this plugin
> runs?

Push for something *testable* by a deterministic script, not a vibe. Good:
"a repo's original is never deleted until its backup bundle is confirmed
present." Too vague: "it should be safe." If the user can't yet state one, that's
fine — scaffold anyway; the red-by-default stub is exactly the placeholder that
keeps the plugin honest until they can.

Also collect: the plugin **name** (kebab-case) and a one-line **description**
(what it does + when to reach for it — this is the primary trigger, so make it a
little pushy).

### 2. Run the generator

```sh
skills/plugin-factory/scripts/scaffold-plugin.sh <name> \
  --description "<one-line description>" \
  --invariant   "<the always/never you elicited>" \
  --author      "<author name>"
```

It creates `plugins/<name>/` with the full skeleton and appends the
marketplace.json entry. It refuses to clobber an existing plugin unless you pass
`--force`, and it rejects a non-kebab-case name. Run it from anywhere in the
repo — it auto-detects the marketplace root (or pass `--root DIR`).

### 3. Fill in the skeleton

The generator leaves clearly marked `TODO`s and a red eval on purpose. Walk the
user through, in priority order:

1. **The real invariant** in `skills/<name>/SKILL.md` (if step 1 was vague).
2. **Real deterministic checks** in `evals/cheap/checks.sh` — replace the stub
   body, then delete the sentinel line and the `bad` call. This is what turns the
   plugin green; until then `evals/cheap/run.sh` fails closed on it by design.
3. The remaining prose `TODO`s in `SKILL.md`, `AGENTS.md`, and the command. Once
   the TODOs are filled, run the two authoring-time passes in
   [`references/authoring-checklist.md`](references/authoring-checklist.md)
   over that prose before calling it done: the **No-Op Test** (delete a line;
   if agent behavior doesn't change, the line didn't earn its place) and
   **progressive disclosure** (every token of `SKILL.md`/`AGENTS.md` loads on
   every invocation, so budget it — push deep or rare-path detail out to
   `references/*.md`, add that directory only if the split is earned). These
   are about the plugin you're writing right now, not an audit of docs that
   already shipped elsewhere.

### 4. Confirm it's green

```sh
evals/cheap/run.sh
```

A newly scaffolded plugin is **expected to be red** until step 3.2 is done —
that's the point. Green means someone wrote real checks for the invariant.

### 5. Turn the red skeleton into a skill that beats a baseline

Scaffolding gets you *valid, wired, RED*. Making the skill actually improve a
model's behavior is a separate, iterative loop — and this plugin ships the
discipline for it rather than leaving you to improvise. See
[`references/skill-iteration.md`](references/skill-iteration.md): it wraps the
SHA-pinned upstream skill-creator (`vendor/skill-creator.pin`), hands off state
through the committed `templates/handoff/` files so the loop survives across
sessions and harnesses, scores each round's *lift* over a no-skill baseline with
`scripts/delta_gate.py` (advisory for one release), and keeps the loop honest and
bounded with `scripts/check_baseline_integrity.py`.

## Keep it portable

Prefer portable prose and deterministic bash over harness-specific machinery —
the *discipline* a good plugin encodes should be harness-agnostic. Claude-Code
primitives like hooks and subagents don't port to other harnesses, so if a plugin
genuinely needs one, say so in its prose with a caveat that the pattern still
ports even though that primitive doesn't. The cheap tier's portability linter
enforces exactly this.
