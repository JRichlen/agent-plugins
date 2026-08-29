---
id: practice.llm-engineering.karpathy
kind: behavior
version: 1.0.0
domains: [llm-engineering, prompting]
requires: [behavior.evidence]
---

# LLM engineering (Andrej Karpathy)

Distilled from Karpathy's primary sources: "A Recipe for Training Neural
Networks" (Apr 2019), the Software 3.0 / "Software Is Changing (Again)" talk
(Jun 2025), the context-engineering post (Jun 2025), and his vibe-coding and
nanochat commentary (2025). Paraphrased with attribution.

<rule id="one-verified-piece-at-a-time" strength="must">
Never stack unverified complexity: add one change at a time and verify it
before the next — a pile of unverified changes hides bugs that take forever
to find.
</rule>

<rule id="assume-silent-failure" strength="must">
Assume failures are silent: running code is not correct code, so verify
behavior empirically — inspect inputs and outputs, compare against a
baseline, confirm expected values.
</rule>

<rule id="tight-leash-small-chunks" strength="must">
Keep the model on a tight leash: hand it small, well-scoped increments and
optimize the workflow so verifying its output is fast — never pin the
autonomy slider to maximum.
</rule>

<rule id="dont-be-a-hero" strength="should">
Start from the simplest proven approach — copy the known-good baseline —
before attempting anything custom.
</rule>

<rule id="look-at-the-data" strength="should">
Look at the raw data or material yourself before writing code that processes
it; what actually enters the system is the only source of truth.
</rule>

<rule id="specific-then-generalize" strength="should">
Write the specific version first, prove it, then generalize while checking
you still get the same result.
</rule>

<rule id="engineer-the-context" strength="should">
Treat the context window as the engineered resource: fill it deliberately
with exactly the right information for the next step, and externalize durable
knowledge as explicit notes — the model consolidates no memory between
sessions.
</rule>

<antipattern id="vibe-code-the-core">
Do not hand the novel, precision-critical core to an agent on vibes; agents
earn boilerplate first, and code far off the training distribution is where
they quietly mislead.
</antipattern>

<rule id="fix-the-seed" strength="must">
In any experiment loop, fix the random seed and disable unnecessary
variation so a re-run gives the same answer.
</rule>
