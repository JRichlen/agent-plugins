---
id: security.iam.strict
kind: behavior
version: 1.0.0
tasks: [pull-request-review]
conflicts_with: [security.iam.review]
---

# Fixture: unresolved active conflict

<rule id="deny-all" strength="must">
Reject any IAM change outright.
</rule>
