# AGENTS.md — agent-plugins marketplace

This repository is a **cross-harness agent plugin marketplace**. It hosts
one or more plugins under `plugins/<name>/`, listed in the root
`.claude-plugin/marketplace.json` so each can be installed with:

```
/plugin marketplace add JRichlen/agent-plugins
/plugin install <name>@jrichlen
```

## Default operating mode

Route to the **most-specific applicable specialist skill or recipe** for the
work itself. Redgate is a working harness/protocol layer, not the universal
router: compose `plugins/redgate/skills/redgate/SKILL.md` around nontrivial
work when execution benefits from explicit falsifiable criteria, iterative
verified rounds, or a classified human gate. A specialist owns the domain
procedure; Redgate reinforces how that procedure is executed. Calibration
sends T0 work straight through, and work fully handled by a specialist with no
need for an evidence contract or classified gate does not acquire Redgate
ceremony merely because it is nontrivial.

For user decisions and confirmations, prefer the harness's native structured
choice/confirmation primitive when available. Present one decision per
interaction by default as multiple choice, multi-select, or a compact
confirmation, with the recommended option first. If no structured primitive
exists, present the same compact options in text and accept a short answer.
Never dump a long prose questionnaire or force a large typed response.
Subagents return ambiguities to the parent; only the parent interacts with the
user.

This `AGENTS.md` is the cross-harness entry point for the *repository* (its
layout and the eval discipline below). Each plugin ships its own `AGENTS.md`
describing that plugin's workflow — e.g. `plugins/graveyard/AGENTS.md`. Harnesses
that read `AGENTS.md` (or a symlink to it, like `CLAUDE.md`/`GEMINI.md`) will
find this governance here, and the plugin's own entry point inside its directory.

## Layout

```
.claude-plugin/marketplace.json   # lists every plugin (name, source path)
plugins/<name>/                    # one directory per plugin
  .claude-plugin/plugin.json       # that plugin's manifest
  skills/  commands/  docs/        # the plugin's contents
  AGENTS.md (+ CLAUDE.md/GEMINI.md symlinks)
evals/                             # the three-tier eval harness (see evals/README.md)
```

Adding a plugin: create `plugins/<new>/` with its own `.claude-plugin/plugin.json`
and add a matching entry to `marketplace.json` whose `source` is `./plugins/<new>`.
The cheap eval verifies that wiring.

## Eval discipline — REQUIRED around the graveyard skill

The graveyard skill deletes GitHub repositories. That is irreversible, so changes
to it are gated by evals rather than trust. Three tiers, defined in `evals/`
(full detail in `evals/README.md`). Run the tier that matches what you touched —
each tier is a superset of the confidence of the one above it, so a deep change
runs all three.

**1. cheap — always, before every commit that touches `plugins/**` or `evals/**`.**
Deterministic, offline, free, under a second:

```sh
evals/cheap/run.sh      # exit 0 required to commit
```

It proves the scripts parse, the manifests are valid, the marketplace is wired,
and — critically — that the delete-script generator still guards every bundled
deletion behind a bundle-existence check. Do not commit with this red.

**2. behavioral — when you change skill *prose* (`SKILL.md`, command markdown, this or the plugin `AGENTS.md`).**
Prose steers the model; a weaker instruction is a real regression even when no
script changed. Run promptfoo:

```sh
# OPENROUTER_API_KEY = cheap model under test; ANTHROPIC_API_KEY = the grader.
cd plugins/graveyard/evals/promptfoo && OPENROUTER_API_KEY=... ANTHROPIC_API_KEY=... npx promptfoo@latest eval
```

An LLM judge confirms a model *given the skill* still archives-then-verifies and
hands the user a guarded delete script instead of self-deleting.

**3. deep — when you change a safety invariant, the archive/delete scripts, or cut a release.**
Sandboxed, cross-harness, end-to-end. pier 0.3.0 runs one agent per invocation, so
`run.sh` loops the roster itself and asserts each agent's expected reward:

```sh
PIER_AGENTS="oracle nop" plugins/graveyard/evals/pier/run.sh   # calibration floor, no keys
plugins/graveyard/evals/pier/run.sh                            # full roster in Docker
```

This is the tier that proves the invariant holds no matter which harness
(claude-code, codex, gemini, cursor) drives the skill — the cross-harness
guarantee this repo exists to keep.

In CI the deep tier is a **required** check (`deep tier (pier)`) and the actual
pier run is gated: it fires only when a PR touches
`plugins/*/skills/**/scripts/**` or `plugins/*/evals/pier/**` — so nothing is
spent on trivial PRs. Non-safety PRs report the deep tier green instantly.

The tier runs **unattended**: `deep-run` carries no protected environment, so an
agent-driven PR reaches a verdict without waiting for a maintainer to approve the
run. The `deep-tier gate switch` step in `deep-detect` is the on/off control and
is currently `enabled=true`.

> [!WARNING]
> Setting that switch to `false` does not make the `deep tier (pier)` check
> disappear — it *cannot*, or branch protection would hang and the
> branch-protection drift guard would go red. The check keeps reporting, so it
> goes **green because the tier did not run**, not because the invariant below
> was proven. The aggregate emits a `::warning::` saying exactly that on every
> run. If you ever turn it off, run the tier locally before merging any
> safety-path change, and turn it back on as soon as you can.

### The invariant every tier defends

> A repository's original is deleted **only after** its backup bundle is
> confirmed present in the graveyard. The skill never deletes repos itself — it
> emits a guarded script the user reviews and runs; the graveyard repo is
> private by default; and full history is preserved via a mirror-clone bundle.

If a change would weaken any clause above, it must not merge until the relevant
tier is green. When in doubt, run the next tier down.

## Demonstration discipline — REQUIRED on every skill change

Any PR that creates or edits a skill — a `SKILL.md`, anything under a skill's
`references/`, or the command that invokes it — must carry a **PR comment
demonstrating that skill applied to real input**, with the before and after
visible in the comment.

The tiers above prove different things, and none of them proves this one:

| Tier | What it proves | What it cannot show |
|---|---|---|
| cheap | The load-bearing sentences are still present | Whether they mean anything |
| behavioral | A model given the skill changes its behaviour | Whether the change is worth having |
| deep | The safety invariant holds across harnesses | Anything about non-safety skills |
| **demonstration** | **What the skill actually does to real material** | Nothing a reviewer has to take on faith |

A reviewer can read a green check and still have no idea whether a skill earns
its slot. The demonstration is the only artifact that answers that, and it is
cheap: run the skill, paste what happened.

### What counts

- **Real input.** Prose, code, or a repo file that existed before you wrote the
  skill. Your own draft is fine and is often the best choice — you can edit it
  freely, and a skill catching its own author is worth more than one catching a
  strawman.
- **The actual run.** Apply the skill and paste the result. Show the input, the
  output, and the specific rule that produced each change.
- **The misses.** Say what the skill did not catch, got wrong, or flagged
  where you disagreed. A demonstration with no misses is a sales pitch.

### What does not count

- A description of what the skill *would* do.
- An example lifted from the skill's own documentation — the skill agreeing
  with itself proves nothing.
- A summary of the diff. That belongs in the PR body; this is the skill running.

> **Never post a demonstration you did not actually run.** This is the same
> clause `voice` defends twice — a fabricated validation, and a cleanup claimed
> over an unchanged draft. A demonstration is worse than either, because it is
> the evidence a reviewer merges on.

Not machine-enforced, and it cannot be: the cheap tier is offline and cannot
read a PR comment. This is a review gate — do not approve a skill change whose
demonstration comment is missing, and say so rather than merging around it.
