# AGENTS.md — tracer-bullets

Ship the thinnest end-to-end slice through a system first, then widen it in place — for both software delivery and open-ended investigation/research. Use when scoping new work, de-risking unknowns, or planning how to explore an unfamiliar problem before committing to a full build.

## How to use it

Read `skills/tracer-bullets/SKILL.md` and follow it — it is the authoritative
description of this plugin's workflow and the invariant it defends.

The command `commands/tracer-bullets.md` is the entry point a user invokes.

## The invariant this plugin defends

A tracer bullet is a real, end-to-end, kept-and-built-upon slice through every layer of the system (or claim) — it must ALWAYS touch every layer for real, and it must NEVER be thrown away like a prototype/spike; a prototype/spike answers a question and gets discarded, a tracer bullet becomes the skeleton of the final thing.

The deterministic checks that defend it live in `evals/cheap/checks.sh` and run
as part of the marketplace cheap tier.
