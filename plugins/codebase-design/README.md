# codebase-design

Before writing a new interface (module boundary, class API, function signature, or service contract) that at least two call sites will depend on, that crosses a module/service/team/persistence boundary, or that will be expensive to change later — produce 3+ radically different candidate designs and compare them on depth, locality, and seam placement before picking one. Use on "before committing to an interface", "design this API/module/class boundary", "how should this be structured", "compare interface designs", "is this the right abstraction", "design it twice", reviewing a proposed interface shape in a PR — or self-trigger whenever about to write a new interface meeting that bar.

## Install

```
/plugin marketplace add JRichlen/agent-plugins
/plugin install codebase-design@jrichlen
```

PORTABILITY: harness-agnostic. The core design-it-twice procedure is plain
reasoning and prose comparison — no subagent-spawning tool, no Workflow
tool, no hooks required on any harness. An optional parallel-subagent
escalation exists only where a subagent-spawning tool happens to be
present; it is a convenience, never a dependency.

## How it works

Full procedure lives in `skills/codebase-design/SKILL.md` (kept lean,
always resident). In short: Step 0 gates on whether the interface in front
of you is actually interface-shaped (2+ dependents, crosses a boundary,
expensive to change later, or a genuinely new abstraction) — trivial code
skips the rest. If it clears the gate, Step 1 generates 3+ radically
different candidate designs for the same functionality (varying where
state lives, the call shape, the surface size, or who owns error
handling), Step 2 scores each candidate on three named axes — depth,
locality, seam placement — and picks a winner with a cited rationale. Step
3 names the chosen design's seams and runs the two-adapter check on each
one; Step 4 classifies its dependencies into four categories to decide
what gets a test double and flags any interface that exists only for
testability. Step 5 ships the chosen design, its rationale, and its named
seams — not the full debate.

Deeper technique detail — the exact axis definitions, a comparison-table
template, and two fully worked examples — lives in
`skills/codebase-design/references/design-it-twice.md`. How to judge a
single interface once chosen — Module Depth Analysis, the deletion test,
the two-adapter check, and the Seam-Based Design & Test Agreement — lives
in `skills/codebase-design/references/deep-modules.md`. Both load only
when the corresponding step is actually reached, not up front.

## Not this

Three plugins in this marketplace sit near this one. None of them does
what codebase-design does:

- **orchestrate** fans subagents out over RESEARCH dimensions and
  adversarially verifies the CLAIMS that research surfaces. codebase-design
  compares DESIGN ALTERNATIVES the agent itself generates — no Workflow
  tool, no per-stage schema, no adversarial verifier required.
- **second-opinion** (`plugins/voice/skills/second-opinion`) is post-hoc
  and offer-only: it validates a verdict that already exists. codebase-design
  is pre-hoc and self-triggering — it runs before an interface is written.
- **grill-me** is a live conversational interview of the user about a
  plan. codebase-design never interviews the user as its core mechanism —
  it generates and self-compares concrete interface designs against
  objective axes. The two are complementary: grill-me's frontier loop can
  hand off to codebase-design at a branch that is an interface decision.

See `skills/codebase-design/SKILL.md`'s own "Not this" section for the full
contrast.

## Status

Implemented. The cheap eval (`evals/cheap/checks.sh`) defends the
invariant mechanically: the five numbered steps in order, the "Not this"
differentiation naming all three adjacent plugins, both reference files
existing and being loaded by relative path, and the four Module Depth
Analysis categories plus the two-adapter check surviving in
`deep-modules.md`.

## License

MIT
