---
name: agent-compiler
description: >-
  Compile deterministic, content-hashed agents from small behavior modules
  instead of hand-writing persona prompts. Use when the user asks to build,
  compose, or reproduce an agent/persona/reviewer from reusable behavior
  ("compile an agent", "make me a security reviewer from the registry",
  "why does this agent behave this way", "add a rule to the registry"), or
  when agent behavior needs provenance, an effect ceiling, or byte-for-byte
  reproducibility.
---

# agent-compiler

## Invariant

Given the same registry revision, query, and compiler version, compilation produces a byte-identical canonical AgentImage and identical hash; every emitted unit carries provenance to a source module; unresolved conflicts, missing dependencies, dependency cycles, and effects above the query's ceiling fail compilation.

The deterministic kernel (`scripts/compile.py`) enforces all of that. This
skill governs the one step the kernel cannot: turning fuzzy intent into a
typed AgentQuery — and refusing to smuggle behavior past that boundary.

## The boundary rule

Natural language may **select** behavior; it may not silently **define** it.

- You may interview, infer, and search fuzzily while building the query.
- Once the query exists, only the kernel decides what the agent is.
- If the user's intent needs behavior no registry module provides, the move
  is **author a module, then recompile** — never paste prose into the
  rendered agent, and never edit a rendered artifact by hand (each one says
  so in its header).
- "Just write me the persona file" is an agent-building request, not a
  writing task. Decline the freehand shortcut and normalize it in the same
  reply: the deliverable is a compiled, rendered artifact — never
  hand-authored persona prose, with or without a disclaimer.

## Two ways in: MCP tools or the CLI

Installed as a Claude Code plugin, the bundled MCP server (`kernel`, from
`scripts/mcp_server.py`) starts automatically and exposes the same four pure
operations as tools: `inspect`, `compile`, `explain`, `render`. Prefer them
when available — same kernel, same guarantees, no shell round-trip. The CLI
below is the identical fallback on any harness without MCP; the server is a
convenience, not a dependency, and it never performs an effectful action
(`render` returns markdown text; writing the file stays with you).

Two hooks reinforce this mechanically on Claude Code (a convenience, not a
dependency — on any other harness these rules bind through this prose alone):
agent-building prompts get a context pointer to the MCP tools, and any
hand-edit of a file carrying the renderer's imageHash header is denied with
the recompile instruction.

## Workflow

1. **Normalize intent into an AgentQuery.** Ask or infer until these are
   explicit: `role`, `task`, `domains`, `views`, `stance`, and the effect
   ceiling (`effectCeiling` in the query, or a view's `max_effects`). Show
   the user the query JSON before compiling. A compile with no ceiling from
   either source is refused (`NO_EFFECT_CEILING`) — an unconstrained agent
   must be asked for by listing its effects, never implied by omission.
   Ceiling first, in plain words: before you inspect the registry or call
   `compile`, either ask the user to fix the agent's allowed effects (e.g.
   read-only `scm:read` vs. commenting `scm:write`) or state the ceiling you
   will compile under — a passing mention that "the compiler enforces a
   ceiling" is not a ceiling. Then show the draft query (`role`, `task`,
   `domains`, `views`, `stance`, `effectCeiling`) as JSON, with placeholders
   marked wherever you still need an answer. Registry `inspect` calls refine
   the draft; they never replace showing it — a reply that ends at inspection
   has not normalized anything.
2. **Discover module IDs** with
   `python3 scripts/compile.py inspect --registry <dir> [--kind|--tag|--id]`.
   Fuzzy discovery may suggest IDs; the compile step consumes exact IDs only.
3. **Compile:**
   `python3 scripts/compile.py compile --registry <dir> --query <query.json> --out <image.json>`
   The output is a canonical AgentImage whose `hash` identifies the agent.
4. **On diagnostics, fix the source, not the check.** Relay the structured
   diagnostics and resolve them in the registry (add a `supersedes` edge,
   split a module, drop a capability) — never by suppressing or downgrading
   the failure.
5. **Render** the image into a harness-native agent definition:
   `python3 scripts/render_claude_agent.py --image <image.json> --out .claude/agents/<name>.md`
   PORTABILITY: `.claude/agents/` is Claude Code's location; the AgentImage,
   not the rendered file, is the contract, and the same image renders for any
   other harness (the discipline ports even where the path does not).
6. **Explain on demand:** every line of a rendered agent carries its unit ID;
   `python3 scripts/compile.py explain --image <image.json> --unit <id>`
   traces it to module, version, source file, and lines.

## Authoring modules

The module format (Markdown + restricted frontmatter + semantic blocks) is
specified in `references/language.md`. Keep modules small and addressable:
one concern per module, stable IDs, explicit `requires`/`conflicts_with`/
`supersedes` edges, semantic versions. A module's filesystem location never
carries meaning — only its `id` does.

## Where the registry lives

This plugin ships a starter `registry/`. `--registry` accepts any directory,
so a repository can carry its own registry (e.g. `registry/` at its root) and
compile agents from it; the kernel treats both identically.
