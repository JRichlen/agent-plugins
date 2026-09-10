# AGENTS.md — jori

Coordinate complex work with bounded agents, evidence, and proportional dashboards.

## How to use it

Read `skills/jori/SKILL.md` and follow it — it is the authoritative
description of this plugin's workflow and the invariant it defends.

The command `commands/jori.md` is the entry point a user invokes.

For portable activation context, read `context/AGENTS.fragment.md`. Installing
this plugin does not by itself modify a global AGENTS file; apply the fragment
to global instructions only when the user explicitly requests persistent activation.

## The invariant this plugin defends

The coordinator delegates substantive work through bounded real agents, preserves user authority over deep or wide changes, and never claims work or monitoring that did not happen.

The deterministic checks that defend it live in `evals/cheap/checks.sh` and run
as part of the marketplace cheap tier.
