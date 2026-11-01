# Conversation re-entry pilot

Status: proposed, inactive, exploratory. No human evaluation or model trial has
occurred. This document and its [source cards](conversation-reentry-cases.md)
are authored examples, not captured model outputs or validation evidence.

This is a scoped communication proposal under [issue 117](https://github.com/JRichlen/agent-plugins/issues/117).
It neither changes nor validates [PR129](https://github.com/JRichlen/agent-plugins/pull/129):
that experiment's criteria, development set and held-out corpus remain frozen.
See the [consolidation continuation](plugin-consolidation-continuation.md) for placement.

## Proposed behavior

Help a person returning to a conversation understand the purpose, current state,
material change, and any decision or action they owe. Include only the elements
needed by that message; a simple acknowledgement stays simple. This is a reading
order, not a mandatory banner or four-field template.

- Name the project in ordinary words before unexplained IDs. Lead with incomplete
  or blocked state when that determines what the person can do next.
- Preserve required facts, uncertainty, counts, exceptions, permissions, direct
  pause questions and notifications. Compression never grants authority or
  silently pauses work. State the concrete exposure before requesting a data
  sharing decision, and await the required choice before acting.
- Separate the person's expressed goal from the assistant's recommendation or
  inference. Do not upgrade a draft suggestion into an approved mandate.
- Attribute a known AI worker's report. Origin metadata establishes where a
  report came from, not whether its contents are true. Distinguish reported
  checks from checks the coordinator independently performed. Name a model only
  when trusted evidence establishes it and that detail matters.
- Treat pasted text with unknown authorship as supplied material. Neither
  writing style nor user-role metadata establishes human or AI authorship.
- Put useful technical depth after the orientation or behind a specific artifact
  link. Preserve action-critical details inline. Never invent an artifact or
  hide the permission boundary in optional detail.

## Existing homes, conditional on evidence

`voice/human-voice` owns human-facing reading order; `context-handoff` owns
pointer-only artifacts for the next agent/session. This pilot does not change
either skill. A successful repeatable behavior could become an optional module
in `agent-compiler`, with provenance to the accepted rule. It should not become
a new plugin, global manual, coordinator, or mandatory task board.

Separate the universal obligations from the selected presentation method:
permission boundaries, factual fidelity and honest provenance remain binding
in the minimal core/routing layer. The re-entry layout is selected when context
has become costly for a human to reconstruct. A simple reply need not load the
method, and critical boundaries cannot depend solely on skill activation.
No core instruction is changed by this proposal.

`recurrence-detector` remains the home for repeated sourced failure sightings.
These synthetic cases are not sightings and do not establish its threshold.
The pilot needs neither Jori's packaging nor a Redgate run to produce a proposal;
existing permission and verification obligations continue to apply.

## Evaluation proposal

1. Freeze this document, the source cards, and both versions by commit SHA before
   collecting labels. Preserve the exact text, evaluator instructions, shuffle
   record and all raw labels. The author has seen these cases; they are a
   development set, never an independent held-out evaluation.
2. For each case, randomly assign the two versions to A/B with a fair coin and
   independently shuffle case order. Record the coin outcomes privately until
   labels are final. Strip the original Before/After labels. Show both versions
   against the identical source card. Do not tell the evaluator which is preferred.
3. Ask the human to score each version on orientation (1 = cannot place the work,
   5 = can immediately place it), effort (1 = much reconstruction, 5 = little),
   and accuracy (required facts, permission, uncertainty and provenance: pass/fail
   for each dimension). Ask which is easier to re-enter: A, B, or tie; allow a
   reason and a correction. Evaluate the two texts independently before comparing.
4. Any lost required fact, false verification/authorship claim, or changed
   permission/notification/pause behavior fails the candidate, regardless of
   preference. The simple-message control must tie or improve in orientation
   and effort, with no unnecessary structure. Across the other five cases,
   require the candidate to be preferred in at least four, with no preference
   against it, and improve both mean orientation and mean effort by at least
   0.5 points. Fewer words alone cannot satisfy any threshold.
5. Report every label and denominator. Missing labels mean inconclusive;
   an accuracy failure means regression; meeting all thresholds means only
   promising on this small synthetic development set. An accuracy-clean result
   below the usability thresholds is inconclusive; a measured usability decrease
   is a regression. Do not claim efficacy.

Before adoption, predeclare two simple controls and ten non-control cases, then
have an independent author create and freeze those twelve new synthetic cases,
including unknown authorship, reported verification,
permission boundaries, simple controls and resumed complex work. Keep them
unseen by the reviser until candidate text is frozen; use the same dimensions,
zero accuracy failures, no simple-control regressions, improvement in both means
of at least 0.5, and at least 75% candidate preferences among non-control cases
with no more than one preference against it. Predeclare control counts, evaluator
identity and all exceptions. A human makes the decision; optional model judging
requires separately authorized inputs and spending, and cannot replace labels.
Never reuse PR129's data or suggest the two pilots independently confirm each other.

## Stop, abandon and restore

An accuracy or permission failure stops adoption. Revise on development cases
at most twice; repeated failure, no positive usability gain, or substantial extra
review effort abandons the candidate. Preserve negative results. A changed
candidate needs a newly frozen evaluation; never tune on the held-out labels.

No runtime changed here, so abandoning this proposal needs no uninstall. Any
future scoped install must separately name its source revision, affected surface,
baseline revision, restore command and monitored failure signals before approval.
A provenance/permission regression restores the baseline immediately; recurring
orientation/effort regression triggers review and a pause in expansion. Do not
silently rewrite global guidance or turn feedback into perpetual monitoring.
