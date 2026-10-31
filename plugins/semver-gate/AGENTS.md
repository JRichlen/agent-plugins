# AGENTS.md — semver-gate

Classify a candidate action as PATCH/MINOR/MAJOR (semver-style blast-radius test) before acting, and rehearse the rollback of any irreversible one — name the restore path and exercise it. Act silently on PATCH, flag-and-stage MINOR, stop for explicit human sign-off on MAJOR; sign-off authorizes the action, the rehearsal proves the exit. Use mid-task when unsure how much autonomy to take: which path to pick, overwriting unreviewed state, disabling a safety toggle, deletes, drops, force-pushes, migrations, or any judgment call settings.json's autoMode patterns don't enumerate.

## How to use it

Read `skills/semver-gate/SKILL.md` and follow it — it is the authoritative
description of this plugin's workflow and the invariant it defends. The full
decision table (all three tiers, every property, worked examples) lives in
`skills/semver-gate/references/rubric.md` — load that when classifying an
edge case or justifying a specific tier call; SKILL.md stays lean and points
to it (progressive disclosure).

The command `commands/semver-gate.md` is the entry point a user invokes.

This plugin ships a second skill, `prove-the-undo`, triggered by the same
moment: any action `semver-gate` classifies as MAJOR, and any irreversible
action even before it is classified. The two run as sequential steps, not
competing procedures — `semver-gate` answers "may I do this?" (classify, then
stop for sign-off on MAJOR), `prove-the-undo` answers "if it is wrong, can I
actually get back?" (name the restore path, exercise it, attach the evidence).
Sign-off authorizes the action; it does not substitute for the rehearsal, and
a rehearsal does not substitute for sign-off. Run both before an irreversible
MAJOR action proceeds. Read `skills/prove-the-undo/SKILL.md` for the rehearsal;
its entry point is `commands/prove-the-undo.md`.

## What this plugin is NOT

It is not a replacement for, or a competitor to, two things that already
govern agent behavior in this environment and always take precedence:

1. The Claude Code system prompt's "Executing actions with care" section
   (the reversibility/blast-radius principle) — semver-gate operationalizes
   that principle into a memorized PATCH/MINOR/MAJOR vocabulary; it adds no
   new criteria on top of it.
2. settings.json's `autoMode` block (`hard_deny`/`soft_deny`/`allow` pattern
   matches) — a coded rule there always wins over whatever this skill's
   table concludes. semver-gate covers only the judgment-call space no
   pattern rule enumerates.

## The invariants this plugin defends

### semver-gate

A MAJOR-classified action must never be taken without explicit, specific prior human sign-off on that exact action and mechanism — not inferred from a prior adjacent confirmation, not assumed from a general instruction, not skipped under time pressure or retry pressure, and never routed around when a separate structural block (classifier, permission denial, API-level policy) fires after sign-off was already given. Every eval for this skill exists to defend this one rule; everything else in the design (PATCH silence, MINOR flagging, staging behavior) is allowed to be approximate, but this rule is never allowed to soften.

### prove-the-undo

An irreversible action is ALWAYS preceded by a named restore path that was actually exercised (restored, diffed, or dry-run-verified) in this session — and NEVER justified by the mere existence of an unverified backup.

The deterministic checks that defend both invariants live in
`evals/cheap/checks.sh` and run as part of the marketplace cheap tier. Only the
`semver-gate` invariant has a behavioral (promptfoo) pack; `prove-the-undo`
deliberately has none (see `README.md`).
