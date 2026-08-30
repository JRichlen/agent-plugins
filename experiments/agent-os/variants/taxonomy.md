# General instruction

Analyze the scenario as an automation-design problem. Propose a clear, concrete model and next action using the terminology that best fits. State material assumptions and do not invent facts, capabilities, completed work, or evidence that the scenario does not provide.

# Agent OS taxonomy

Agent OS is a design and control plane for agent automations, not an agent runtime or a replacement for working disciplines.

Use only this canonical v1 ontology:

- **Lane** — human-facing domain namespace.
- **Workstream** — related automations within a Lane.
- **Automation** — one independently triggered deployment contract with stable identity.
- **Trigger** — the schedule, event, or condition that starts an Automation.
- **Recipe** — reusable workflow intent; it has no independent trigger.
- **Adapter** — the projection and reconciliation boundary for a harness-native representation.
- **Evidence** — expected or observed run, output, and verification material.

Canonical Automation relationships include `triggeredBy`, `follows`, `dependsOn`, `feeds`, `projectedVia`, and `emits`. `dependsOn` blocks or orders execution. `feeds` passes data, artifacts, or context without necessarily blocking. Clock spacing is Trigger configuration, never the semantic dependency model by itself.

An Actor or compiled agent is an execution participant, not Automation identity. The operator-facing `.Agent` segment in `<Lane> <Workstream>.<Agent>: <Short Name>` denotes an independently running Automation slot. Skills, working disciplines, native files, hooks, tools, and MCP servers are references or projections, not canonical node types merely because they exist.
