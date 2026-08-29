---
id: discipline.build-run-verify
kind: behavior
version: 1.0.0
domains: [engineering-discipline]
---

# Build, run, verify

From this repository's own working practice: the best way to refine a design
is to build it, run it, and verify it — the agent-compiler kernel's hash bug
was found by execution, not review (see docs/designs/agent-compiler-plugin.md,
"Design corrections forced by running it").

<rule id="prefer-execution-over-review" strength="must">
When a design claim can be tested by building and running a thin slice,
do that before extending the design on paper.
</rule>

<example id="hash-bug">
The compiler's first image hash covered the registry revision; one metamorphic
run showed an unrelated module changing an existing image's hash — a defect no
amount of re-reading the design had surfaced.
</example>
