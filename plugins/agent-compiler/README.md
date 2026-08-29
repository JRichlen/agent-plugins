# agent-compiler

Agents are compiled, not stored. Humans author small, addressable behavior
modules; a model may turn fuzzy intent into a typed AgentQuery, but everything
after that boundary is deterministic: the kernel resolves modules, expands
dependencies, fails closed on conflicts and over-ceiling effects, and emits an
immutable, content-hashed AgentImage that renders into a harness-native agent
definition — every line traceable to its source module.

## Install

```
/plugin marketplace add JRichlen/agent-plugins
/plugin install agent-compiler@jrichlen
```

## Try it

```sh
cd plugins/agent-compiler
python3 scripts/compile.py compile \
  --registry registry \
  --query examples/queries/security-pr-review.json \
  --out /tmp/image.json
python3 scripts/render_claude_agent.py --image /tmp/image.json
```

Compile it twice — the bytes and the hash are identical. Add an unrelated
module — the hash does not move. Ask for a write capability under a read-only
ceiling — compilation fails with `EFFECT_CEILING` instead of shipping a
quietly over-privileged agent.

Installed as a Claude Code plugin, the bundled MCP server starts
automatically and exposes the same operations as tools — `inspect`,
`compile`, `explain`, `render` — read-only by construction (no `execute`,
ever). The CLI above is the identical surface for any harness without MCP.

## Pieces

- `skills/agent-compiler/SKILL.md` — the boundary discipline: natural language
  may *select* behavior, never silently *define* it.
- `skills/agent-compiler/references/language.md` — the module format and exact
  selection semantics.
- `scripts/compile.py` — the deterministic kernel (stdlib-only python3):
  `compile`, `inspect`, `explain`.
- `scripts/render_claude_agent.py` — AgentImage → Claude Code agent definition
  (the image is the contract; other harnesses get sibling renderers).
- `scripts/mcp_server.py` — the auto-started MCP facade (stdlib-only JSON-RPC
  over stdio), declared under `mcpServers` in `.claude-plugin/plugin.json`.
- `registry/` — starter modules; `--registry` accepts any directory, so your
  repo can carry its own.
- `evals/cheap/` — golden, metamorphic, and fail-closed checks run by the
  marketplace cheap tier.

Design history: `docs/designs/agent-compiler-plugin.md` at the repo root.
