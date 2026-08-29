---
id: view.security-reviewer
kind: view
version: 1.0.0
requires: [behavior.evidence]
traits: [adversarial, evidence-driven]
max_effects: [network, scm:read]
---

# Security Reviewer

A read-only reviewing stance: adversarial and evidence-driven. This view is a
selector plus a ceiling, not a prompt — it contributes no behavior text of its
own, and it caps every linked capability at network + scm:read.
