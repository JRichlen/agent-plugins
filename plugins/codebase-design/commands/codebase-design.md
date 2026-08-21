---
description: >-
  Design a new interface twice (or more) before committing to it — produce
  3+ radically different candidate designs and compare them on depth,
  locality, and seam placement before picking one. Use before writing a new
  module boundary, class API, or function signature that other code will
  depend on, or to re-examine an interface someone else already wrote.
---

Invoke the `codebase-design` skill and follow
`skills/codebase-design/SKILL.md`.

Run Step 0 first: confirm the interface in front of you is actually
interface-shaped (2+ dependents, crosses a boundary, expensive to change
later, or a genuinely new abstraction) — if none of those hold, say so and
skip straight to implementation instead of manufacturing a comparison. If it
is interface-shaped, load `skills/codebase-design/references/design-it-twice.md`
and produce 3+ radically different candidate designs (Step 1), score each on
depth, locality, and seam placement (Step 2), name and two-adapter-check the
chosen design's seams using
`skills/codebase-design/references/deep-modules.md` (Step 3), classify its
dependencies into the four Module Depth Analysis categories to decide what
gets a test double (Step 4), then ship the chosen design, its one-paragraph
rationale, and its named seams — not the full debate (Step 5).

This command works the same way whether the interface is one you are about
to write or one already sitting in a diff/PR you're reviewing — the
procedure doesn't care who typed the first draft.
