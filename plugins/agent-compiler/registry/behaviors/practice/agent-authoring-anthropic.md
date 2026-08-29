---
id: practice.agent-authoring.anthropic
kind: behavior
version: 1.0.0
domains: [agent-authoring, prompting]
requires: [behavior.evidence]
---

# Agent authoring (Anthropic)

Distilled from Anthropic's published engineering guidance: "Claude Code best
practices" (Apr 2025, since revised), "Building effective agents" (Dec 2024),
"Writing effective tools for agents" (Sep 2025), and the Agent Skills post
(Oct 2025). Paraphrased with attribution; provenance carries this file.

<rule id="give-a-runnable-check" strength="must">
Give the agent a check it can run — tests, a build exit code, a linter, a
screenshot diff — so the loop closes without a human as the verifier.
</rule>

<rule id="be-specific-in-task-prompts" strength="must">
Name the file, the scenario, the constraint, and what done looks like;
vague goals buy correction rounds.
</rule>

<rule id="point-at-an-existing-pattern" strength="should">
Point at a concrete example in the codebase rather than describing the
pattern in prose.
</rule>

<rule id="keep-persistent-instructions-lean" strength="must">
In persistent instruction files, cut any line whose removal would not cause
mistakes — bloat teaches the agent to ignore the file. (Task prompts are the
opposite: there, more specificity is better.)
</rule>

<rule id="simplest-thing-first" strength="should">
Start with the simplest solution that works; add agentic complexity only
when it measurably improves outcomes.
</rule>

<rule id="progressive-disclosure" strength="should">
Load context progressively: a short always-loaded core with on-demand detail —
the context window is the scarcest resource.
</rule>
