---
description: "Browse a behavior registry: list modules by kind or tag, show a module's units and edges, or trace a compiled unit back to its source."
argument-hint: "[module id | kind | tag | image unit id]"
---

Invoke the `agent-compiler` skill and follow `skills/agent-compiler/SKILL.md`.

Pure discovery, no compilation: run `scripts/compile.py inspect` against the
registry (filtering by $ARGUMENTS as an id, kind, or tag when given) and
summarize what exists — module IDs, versions, units, requires/conflicts edges,
capabilities and effects. For a unit inside a compiled image, use
`scripts/compile.py explain` to show its provenance chain.
