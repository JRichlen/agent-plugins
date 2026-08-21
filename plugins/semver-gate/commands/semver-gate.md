---
description: >-
  Classify a candidate action as PATCH/MINOR/MAJOR (semver-style blast-radius test) before acting — act silently on PATCH, flag-and-stage MINOR, stop for explicit human sign-off on MAJOR. Use whenever you're mid-task and unsure how much autonomy to take on the next action: which of several implementation paths to pick, whether to overwrite unreviewed state, whether to disable a safety toggle, or any judgment call settings.json's autoMode patterns don't enumerate.
---

Invoke the `semver-gate` skill and follow `skills/semver-gate/SKILL.md`.

Classify the action you're about to take (or the one the user just described)
as PATCH, MINOR, or MAJOR using the four-property test and the tie-break rule,
then apply the matching behavior: act silently on PATCH, act-and-flag on
MINOR (staged as its own next step), or stop and ask for explicit sign-off on
the specific mechanism on MAJOR. Consult
`skills/semver-gate/references/rubric.md` for the literal decision table when
the call is close. Remember precedence: a settings.json `autoMode` pattern
match always wins over this classification, and the system prompt's
"Executing actions with care" section is the principle this table serves.
