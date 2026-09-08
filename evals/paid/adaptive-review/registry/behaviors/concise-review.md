---
id: behavior.issue-review-concise
kind: behavior
version: 1.0.0
---

# Concise issue review

<rule id="lead-with-goal" strength="must">
Lead with the decision, requested outcome, or next action the issue exists to support.
</rule>

<rule id="preserve-requirements" strength="must">
Preserve every requirement, constraint, unresolved risk, and explicit action that can change the decision or its execution.
</rule>

<rule id="select-lenses" strength="must">
Use only domain lenses that affect the stated goal; omit generic review categories that produce no finding.
</rule>

<rule id="compress-context" strength="must">
Replace chronology and repeated rationale with the shortest causal context needed to understand why each retained fact or action matters.
</rule>

<rule id="make-actions-scannable" strength="must">
Separate decisions, actions, gates, and deferred work so a maintainer can scan what happens next without rereading the background.
</rule>

<probe id="deletion-test">
Would deleting this sentence change a decision, constraint, risk, or action? If not, remove it.
</probe>

<probe id="preservation-test">
Can every required fact and action in the source be located in the revision without inference?
</probe>

<antipattern id="shorter-by-omission">
Never call an issue concise by dropping a required fact, action, limitation, or approval boundary.
</antipattern>
