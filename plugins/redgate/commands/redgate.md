---
description: >-
  Run work through Red Gate when it needs explicit falsifiable criteria,
  verified ARM/TRACE/JUDGE rounds, or classified human gates. Compose it with
  the most-specific applicable specialist skill or recipe; Redgate reinforces
  execution and verification rather than replacing the domain procedure. Use
  structured choices and confirmations when available, compact textual choices
  otherwise.
---

Invoke the `redgate` skill and follow `skills/redgate/SKILL.md`.

Take the idea given as the argument. Route first to the most-specific
applicable specialist skill or recipe for the work itself. Use Redgate as the
working harness when the task needs an explicit evidence contract, iterative
verified rounds, or classified human gates; do not wrap work in Redgate merely
because it is complex.

**Calibrate first** per `skills/redgate/references/calibration.md`: set tier,
domain, scope, taste, and orchestration (infer, label stated/inferred, ask only
load-bearing unknowns). Prefer the harness-native structured question/choice
primitive when available; otherwise present the same compact 2-3 options in
text. Ask one decision per interaction by default with the recommendation
first, multi-select for independent choices, and compact confirmations for
binary gates. Never emit a long prose question list or require a large typed
response. A T0 task is done directly with no run — say so and do it.

For T1+, apply the round-zero rule to pick the round type (scout / plan /
build / widen), then drive one round: ARM via the `criteria-contract` skill
(interview ≤5 questions total including calibration, emit criteria + verifier,
prove red, ratify, pin), TRACE as one writer flipping one criterion through all
layers it names, JUDGE via a party that did not do the work, then classify the
round gate with semver-gate's four-property test: PATCH (strictly derived from
an approved plan slice, verifier green, no escalator) auto-passes and is logged
to gates.log; MINOR auto-passes with a prominent flag and standing veto; MAJOR
— scout decisions, plan approval, first ratification, WITNESS
countersignatures, fence/budget changes, anything irreversible — stops for an
explicit structured human confirmation. Funding rounds beyond the manifest
budget are always MAJOR.
