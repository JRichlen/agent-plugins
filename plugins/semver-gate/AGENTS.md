# AGENTS.md — semver-gate

A judgment lens, not a tool: classifies the autonomy an agent should take for
a pending action by borrowing semantic versioning's precise MAJOR/MINOR/PATCH
taxonomy and applying it to blast radius instead of a public API. PATCH acts
silently and mentions it in the summary. MINOR acts but flags it prominently
and names the alternative when one is genuinely live. MAJOR stops and requires
explicit human sign-off for that specific action before proceeding. It builds
on top of an existing reversibility/blast-radius instruction and an `autoMode`
permission classifier where one is configured — a hardcoded rule in either
always wins — rather than replacing them; see `skills/semver-gate/SKILL.md`
for exactly how the layers compose and why semver's own wording (not a loose
analogy) is what the mapping is anchored to.

## How to use it

Read `skills/semver-gate/SKILL.md` and follow it — it is the authoritative
description: the exact semver.org and Conventional Commits quotes the mapping
is grounded in, how it composes with pre-existing judgment infrastructure, the
mapping table, a worked calibration example (the `enforce_admins` episode),
and the four-step decision procedure to run in the moment.

The command `commands/semver-gate.md` is the entry point a user invokes.

## The invariant this plugin defends

A MAJOR-class action (irreversible, destroys/overwrites state, changes what is
visible to others, or breaks a contract someone else depends on) is NEVER
taken on an assumption; it always gets an explicit stop and an explicit human
answer to that specific action before proceeding — even under time pressure,
even after an adjacent "yes," and even when a block on it could technically be
routed around. PATCH-class actions never block. Where classes collide, MAJOR
always dominates, the same way a `BREAKING CHANGE` footer overrides `feat` in
Conventional Commits.

The deterministic checks that defend it live in `evals/cheap/checks.sh` and
run as part of the marketplace cheap tier — they hold the SKILL.md's quoted
spec language, its mapping table, and its tie-break rule to exact, load-bearing
substrings so a rewrite can't quietly soften any of them. The prose-level
behavior — that a model actually stops for a MAJOR-class action and doesn't
gate on a PATCH-class one — is defended by the behavioral tier in
`evals/promptfoo/promptfooconfig.yaml`.
