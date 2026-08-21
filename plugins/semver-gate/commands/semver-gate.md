---
description: Classifies the autonomy an agent should take for a pending action by borrowing semver's MAJOR/MINOR/PATCH taxonomy: PATCH acts silently, MINOR acts and flags, MAJOR stops for explicit human sign-off. Builds on top of existing reversibility/blast-radius judgment and autoMode classifiers rather than replacing them.
---

Invoke the `semver-gate` skill and follow `skills/semver-gate/SKILL.md`.

Use this to explicitly reason through the autonomy an action warrants before
taking it: name the action in one sentence, check for a hardcoded rule
(protected branch, sensitive remote target, `soft_deny`/routine allowlist
entry) first, and if none applies, classify it PATCH/MINOR/MAJOR against the
skill's three questions before acting. If the action lands MAJOR, stop and lay
out the action, why it's MAJOR, and the least-destructive alternative — then
wait for an explicit answer before proceeding.
