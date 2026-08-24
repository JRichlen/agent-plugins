# AGENTS.md — prove-the-undo

Rehearse the rollback before any irreversible action: name the specific restore path and demonstrate it works — never proceed on the strength of 'a backup exists'. Use before deletes, drops, force-pushes, migrations, or any action semver-gate classifies as MAJOR.

## How to use it

Read `skills/prove-the-undo/SKILL.md` and follow it — it is the authoritative
description of this plugin's workflow and the invariant it defends.

The command `commands/prove-the-undo.md` is the entry point a user invokes.

## The invariant this plugin defends

An irreversible action is ALWAYS preceded by a named restore path that was actually exercised (restored, diffed, or dry-run-verified) in this session — and NEVER justified by the mere existence of an unverified backup.

The deterministic checks that defend it live in `evals/cheap/checks.sh` and run
as part of the marketplace cheap tier.
