# AGENTS.md — find-before-build

Search for the existing implementation before writing a new one: name the searches you ran for an existing helper, abstraction, or pattern and what they returned, before introducing anything new. Use before adding a utility, wrapper, config knob, or dependency to a codebase you did not write end-to-end.

## How to use it

Read `skills/find-before-build/SKILL.md` and follow it — it is the authoritative
description of this plugin's workflow and the invariant it defends.

The command `commands/find-before-build.md` is the entry point a user invokes.

## The invariant this plugin defends

A new abstraction (helper, wrapper, utility, dependency) is ALWAYS preceded by named searches for an existing equivalent with their results shown — and NEVER introduced when an existing equivalent was found and usable.

The deterministic checks that defend it live in `evals/cheap/checks.sh` and run
as part of the marketplace cheap tier.
