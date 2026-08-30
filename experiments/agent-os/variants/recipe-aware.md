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

# Recipe-aware composition

A **Recipe** is a reusable workflow blueprint: ordered or conditional steps, capability requirements, suggested skills, evidence expectations, and optional execution policies. A human may invoke it and many Automations may bind it, but the Recipe itself never acquires an independent Trigger.

An **Automation** is the deployed binding: stable identity, Trigger, one or more Recipes, relationships, Adapter intent, execution participants, and expected evidence. Reusing a Recipe or compiled Actor does not reuse Automation identity; independently enabled, disabled, scheduled, or inspected jobs are distinct Automations.

A **Workflow** is a harness-native execution graph or implementation detail. A **Skill** is a reusable behavior or procedure a Recipe may reference. An **Actor/agent** is a compiled execution participant whose deterministic composition belongs to `agent-compiler`. Agent OS owns why and when that participant runs and how the Automation fits the portfolio.

Working disciplines such as `diagnosing-bugs`, `scope-fence`, or Redgate remain generic references. Redgate may be an optional `executionPolicy` on a Recipe or Automation when the work warrants it; it is not required by Agent OS and is not a canonical node.
