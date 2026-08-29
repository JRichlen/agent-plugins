---
id: security.iam.review
kind: behavior
version: 1.0.0
tasks: [pull-request-review]
domains: [aws, iam]
requires: [behavior.evidence]
capabilities: [scm.pull_request.read, scm.pull_request.files]
---

# IAM Review

<rule id="least-privilege" strength="must">
Evaluate permissions against the minimum privileges required by the stated
operation.
</rule>

<probe id="cross-boundary-access">
Could this change allow a principal to cross an existing trust boundary?
</probe>

<probe id="wildcard-scope">
Are wildcard resources, actions, or principals being introduced?
</probe>

<antipattern id="unsupported-vulnerability">
Do not describe a theoretical vulnerability without connecting it to concrete
evidence from the reviewed artifact.
</antipattern>
