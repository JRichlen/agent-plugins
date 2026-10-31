# AGENTS.md — consolidation-map

Map a catalog consolidation by unit of work, not by file: one verb per entity, counts that must reconcile. Use for a "meta diff" or when merging or pruning plugins, skills, services or packages.

## How to use it

Read `skills/consolidation-map/SKILL.md` and follow it — it is the authoritative
description of this plugin's workflow and the invariant it defends.

The command `commands/consolidation-map.md` is the entry point a user invokes.

## The invariant this plugin defends

Every entity in the before-inventory appears in exactly one disposition row, the before and after counts reconcile, and a map that does not reconcile is reported as failing — NEVER presented as done, and NEVER filled in with a decision the user did not make.

The deterministic checks that defend it live in `evals/cheap/checks.sh` and run
as part of the marketplace cheap tier.
