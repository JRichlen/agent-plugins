# Task

Produce a reviewer agent for pull-request review, scoped to AWS/IAM domains, with an adversarial, evidence-driven stance, that will only ever run against production and high-risk changes. It must be allowed to read network resources and read (never write) source-control state, and nothing wider than that. Use this repository's own agent registry as the source of the agent's behavior rather than writing the persona prose yourself.

## Paraphrase variants (holdout)

1. Build me a security reviewer persona for PR review, IAM-flavored, read-only network and SCM access, nothing else.
2. I want a compiled reviewer agent -- adversarial stance, AWS/IAM, capped to network + read-only scm -- sourced from the registry, not freehand.

## Baseline framing (no-skill arm)

The no-skill baseline arm gets the same registry files and the same task text, but no MCP kernel tools and no compiler hooks -- only plain filesystem read access to the registry markdown and a bash/text-editing capability, so it can still author a persona file by hand if it chooses to (a correct direct baseline is allowed to pass the negative card).
