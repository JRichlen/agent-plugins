---
id: practice.llm-engineering.willison
kind: behavior
version: 1.0.0
domains: [llm-engineering, prompting]
requires: [behavior.evidence]
---

# LLM engineering (Simon Willison)

Distilled from Simon Willison's primary-source posts: "Here's how I use LLMs
to help me write code" (Mar 2025), "Not all AI-assisted programming is vibe
coding" (Mar 2025), "The lethal trifecta for AI agents" (Jun 2025).

<rule id="never-outsource-verification" strength="must">
Test what the model writes yourself; if you have not seen it run, it is not a
working system.
</rule>

<rule id="explain-or-dont-commit" strength="must">
Never commit code you could not explain to somebody else.
</rule>

<rule id="avoid-the-lethal-trifecta" strength="must">
Never combine private-data access, exposure to untrusted content, and an
external communication channel in one agent — avoid the combination
entirely rather than trusting guardrails.
</rule>

<rule id="manage-context-deliberately" strength="should">
Know exactly what is in the context, seed it with existing code and working
examples, and reset the conversation when it sours.
</rule>

<rule id="prefer-boring-libraries" strength="should">
Prefer stable, well-trodden libraries the model has deep training exposure
to; ask for options with usage examples before committing to an approach.
</rule>

<antipattern id="vibe-coding-in-production">
Do not ship unreviewed model-written code outside low-stakes sandboxes; once
you review and test it, it is ordinary software development — hold it to that
standard.
</antipattern>
