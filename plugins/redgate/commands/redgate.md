---
description: >-
  Run work through Red Gate's calibrated ARM/TRACE/JUDGE loop. This is
  Jordan's default for nontrivial planning, research, design, building,
  debugging, refactoring, review, deployment, multi-agent coordination, and
  risky external actions. Use the interactive ask-question tool for every
  decision and confirmation; never emit a long prose questionnaire.
---

Invoke the `redgate` skill and follow `skills/redgate/SKILL.md`.

Take the idea given as the argument. **Calibrate first** per
`skills/redgate/references/calibration.md`: set tier, domain, scope, taste,
and orchestration (infer, label stated/inferred, ask only load-bearing
unknowns through the interactive question tool). Ask one decision per call by
default with 2-3 tap-ready options, the recommendation first, multi-select for
independent choices, and compact confirmations for binary gates. Never emit a
long prose question list or require a large typed response. A T0 task is done
directly with no run — say so and do it. For
T1+, apply the round-zero rule to pick the round type (scout / plan /
build / widen), then drive one round: ARM via the
`criteria-contract` skill (interview ≤5 questions total including
calibration, calibration block written into the CRITERIA.md header,
scaffold `.redgate/<slug>/` with `skills/criteria-contract/scripts/scaffold-run.sh`,
write 3–7 criteria, prove the gate red, ratify, pin), TRACE as one
tracer-bullet slice with a single writer, JUDGE by running the pinned
`check.sh` from a context that did not do the work. At the round gate, classify with
semver-gate's four-property test: PATCH (strictly derived from an approved
plan slice, verifier green, no escalator) auto-passes and is logged to
gates.log; MINOR auto-passes with a prominent flag and standing veto; MAJOR —
scout decisions, plan approval, first ratification, WITNESS
countersignatures, fence/budget changes, anything irreversible — stops for an
interactive tool confirmation. Funding rounds beyond the manifest budget is
always MAJOR.
