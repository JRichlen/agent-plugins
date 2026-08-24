# AGENTS.md — scope-fence

Keep every hunk of the diff traceable to the stated task: anything discovered outside scope is recorded as a finding (ticket, note, diary entry) — never fixed in the same change. Use when starting any bounded task, when tempted to 'fix it while I'm here', or when reviewing whether a diff crept beyond its mandate.

## How to use it

Read `skills/scope-fence/SKILL.md` and follow it — it is the authoritative
description of this plugin's workflow and the invariant it defends.

The command `commands/scope-fence.md` is the entry point a user invokes.

## The invariant this plugin defends

Every hunk in the produced diff ALWAYS traces to the stated task; out-of-scope discoveries are ALWAYS recorded as findings and NEVER folded into the same change.

The deterministic checks that defend it live in `evals/cheap/checks.sh` and run
as part of the marketplace cheap tier.
