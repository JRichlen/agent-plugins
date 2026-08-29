# AGENTS.md — agent-compiler

Compile deterministic, content-hashed agents from small behavior modules: a skill turns fuzzy intent into a typed AgentQuery, a stdlib-only kernel resolves modules, expands dependencies, fails closed on conflicts and over-ceiling effects, and emits an immutable AgentImage plus a rendered harness-native agent definition — never inventing behavior text without provenance.

## How to use it

Read `skills/agent-compiler/SKILL.md` and follow it — it is the authoritative
description of this plugin's workflow and the invariant it defends. The module
authoring format and selection semantics are specified in
`skills/agent-compiler/references/language.md`.

The commands a user invokes are `commands/agent-compile.md` and
`commands/agent-inspect.md`. The deterministic kernel is `scripts/compile.py`
(compile/inspect/explain) and `scripts/render_claude_agent.py` (AgentImage →
agent definition file). A starter registry lives in `registry/`; a golden
query/image pair in `examples/`.

`scripts/mcp_server.py` is the read-only MCP facade over the same kernel —
declared in `.claude-plugin/plugin.json` under `mcpServers.kernel`, so Claude
Code starts it automatically when the plugin is enabled, exposing `inspect`,
`compile`, `explain`, and `render` as tools. It is stdlib-only JSON-RPC over
stdio and deliberately has no `execute`: nothing on the server can perform an
effectful action. On a harness without MCP the CLI is the identical surface —
the server is a convenience, not a dependency.

The kernel lives in `scripts/`, not under `skills/**/scripts/**`, deliberately:
that glob is this marketplace's deep-tier safety surface (deletion-guard
scripts), and this kernel performs no effectful action — its invariant is fully
provable by the offline cheap tier below.

## The invariant this plugin defends

Given the same registry revision, query, and compiler version, compilation produces a byte-identical canonical AgentImage and identical hash; every emitted unit carries provenance to a source module; unresolved conflicts, missing dependencies, dependency cycles, and effects above the query's ceiling fail compilation.

The deterministic checks that defend it live in `evals/cheap/checks.sh` and run
as part of the marketplace cheap tier: a committed golden image compared
byte-for-byte, repeated and discovery-order-reversed compiles diffed,
unrelated-module hash invariance, one fixture per fail-closed diagnostic
(`CONFLICT`, `MISSING_DEPENDENCY`, `DEPENDENCY_CYCLE`, `EFFECT_CEILING`,
`NO_EFFECT_CEILING`, `BAD_MODULE_KEY`) under `evals/cheap/fixtures/`, and a
full MCP stdio round-trip asserting the facade returns the same golden hash
and the same fail-closed diagnostics as the CLI.
