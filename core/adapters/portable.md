# Portable adapter

Repository-only integration notes; no global file or setting is changed.

Explicitly load the [operating contract](../OPERATING.md), then the selected
method and only its relevant references. Use [ownership.json](../ownership.json)
as the owner/interface index, not as an autonomous router or authorization engine.

Selected-method packages contain generated `context/OPERATING.md` and
`context/ownership.json` projections. Edit the canonical repository sources and
run `python core/sync.py`; `--check` detects missing or edited copies. These local
files make the baseline available to a selected method. They do not activate it
as always-on instructions; that still needs approved host integration. The owner
index describes repository sources, not capabilities proven installed in a host.

Report which filesystem, process, worker, question and verification tools the
host actually supplies. Use compact textual decisions when structured questions
are unavailable. Work directly when delegation is unnecessary; where a required
independent check or integrity guarantee is unavailable, stop that gated action
and return the exact missing capability.

Each registered plugin also ships a generated Agent Plugins 1.0 root
`plugin.json` (and `mcp.json` for MCP servers) from `ci/agent_plugins.py`, so a
client implementing that spec discovers its `skills/` and MCP servers. Commands,
hooks and agents stay in the Claude Code layout; the spec's v1 component types
do not cover them, so a spec-only client loads skills and MCP servers only.
Spec validity is checked offline; loading in each named client is not.

Treat path ordering, line endings, executable bits, symlinks and script dependencies
as qualification concerns. Portable prose alone does not prove portable execution.
No adapter grants permissions, spends money, installs globally or runs a monitor.
