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

The red-by-default sentinel is a **generator-to-human handoff protocol**: the
scaffolder hands the author a stub that visibly refuses to pass until they've
done real work. The behavioral probe that measured this plugin's other claims
could not test this half honestly — a single agent played both the generator
and the human filling in the stub, so the handoff never actually crossed a
role boundary. Treat the sentinel's *mechanism* (the eval fails closed until
edited) as verified by the cheap tier's own dogfood check below, but treat
its *purpose* (stopping a human from shipping the stub unnoticed) as
un-probed, not proven.

## What this does

<!-- MEASURED: a capable model asked to scaffold a plugin for this marketplace
cold, with no skill loaded, wrote 59 real deterministic checks and drove the
suite to exit 0 — the discipline of writing checks is not what's missing. What
it got wrong was this marketplace's OWN layout, 6 times out of 6: plugin.json
and SKILL.md at the root instead of .claude-plugin/ and skills/<name>/, no
AGENTS.md + CLAUDE.md/GEMINI.md symlinks, a bespoke evals/run.sh instead of
evals/cheap/checks.sh, no marketplace.json entry, version 0.1.0 instead of
0.0.1. None of that is inferable from first principles — it's this repo's
convention, and only this repo knows it. That is the plugin's real job. -->

This marketplace's plugin layout — where `plugin.json` lives, that SKILL.md
sits under `skills/<name>/`, the AGENTS.md + CLAUDE.md/GEMINI.md symlink
trio, `evals/cheap/checks.sh` as the entry point, the marketplace.json
lockfile entry, starting at version `0.0.1` — is a local convention, not
something derivable from general plugin-authoring knowledge. A model asked to
scaffold a plugin cold, without having read this repo's other plugins, gets
the actual content right (real checks, a real invariant) but gets this
repo-specific wiring wrong, every time. This skill runs one deterministic
script that encodes the convention so it's never re-guessed.

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

## References

- [`references/judge-calibration.md`](references/judge-calibration.md) — the
  contract for a judged verifier when no deterministic check can defend an
  invariant: one judge per dimension, hard negatives built in, a mandatory
  calibration stub, and a failing calibration treated as a finding rather than
  silenced.
