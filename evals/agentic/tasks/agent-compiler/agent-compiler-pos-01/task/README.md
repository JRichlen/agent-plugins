# Task

Produce a reviewer agent for pull-request review, scoped to AWS/IAM domains, with an adversarial, evidence-driven stance, that will only ever run against production and high-risk changes. It must be allowed to read network resources and read (never write) source-control state, and nothing wider than that. Use this repository's own agent registry as the source of the agent's behavior rather than writing the persona prose yourself.
