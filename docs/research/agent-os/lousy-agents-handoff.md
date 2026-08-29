# Agent OS handoff: zpratt/lousy-agents

## Live thread

Research into `zpratt/lousy-agents` should shape Agent OS as prior art, not as a fork target.

Primary source: https://github.com/zpratt/lousy-agents

Key seams to inspect in the live source:

- `docs/doctor.md` and `packages/doctor/` for multi-harness discovery, topology, archetype classification, CI diagnostics, and intent/capability evaluation.
- `docs/lint.md` and `packages/lint/` for construct-level validation.
- `docs/lessons.md` for durable lesson injection/capture.
- `packages/agent-shell/` for independent execution telemetry and command-policy evidence.
- `docs/product/harness-capability-matrix.md` for explicit support depth across harnesses.
- Issue #890, Agentic Configuration Doctor: https://github.com/zpratt/lousy-agents/issues/890

The architectural implication to test is:

> Agent OS should operate one semantic layer above harness configuration. Native constructs such as AGENTS.md, CLAUDE.md, Copilot instructions, skills, agents, hooks, MCP servers, and scheduled tasks should be projections/adapters of a canonical capability graph rather than the canonical ontology itself.

Candidate semantic concepts to challenge, shrink, or replace:

- Capability
- Actor
- Behavior
- Knowledge
- Policy
- Workflow
- Trigger
- Tool
- Memory
- Evidence
- Runtime

Desired bidirectional model:

1. **Discover** native harness artifacts and reconstruct a canonical graph.
2. **Diagnose** composition, drift, missing preconditions, and ambiguous intent.
3. **Govern** with deterministic lint/doctor/policy checks and evidence-backed findings.
4. **Compile** canonical intent back into Claude Code, Codex, GitHub Copilot, GitHub, and future adapters.
5. **Observe** runtime actions independently of agent self-report.
6. **Learn** from repeated findings and execution outcomes without letting memory become an uncurated dump.

Do not blindly copy Lousy Agents' physical construct taxonomy. Its strongest reusable ideas are the construct graph, doctor-vs-lint split, explicit intent, capability preconditions, evidence-cited findings, lessons, telemetry, and honest harness capability matrix.

### Integration lens: Agent instruction / MCP architecture

Use this research to pressure-test the few-tools / discover-schema + execute model. Determine whether the canonical Agent OS graph can expose its schema and operations without MCP tool explosion. Focus on stable construct identity, relationship types, capability lookup, adapter discovery, and compile/discover operations. Avoid making filesystem conventions the API.

### Integration lens: Agent OS taxonomy / skill sync

Reconcile this with the existing cross-harness plugin model in this repo, especially `plugins/agent-compiler/`, `plugins/docs-hygiene/`, `plugins/context-handoff/`, `plugins/recurrence-detector/`, and `plugins/redgate/`. Decide which concepts become canonical, which remain generated harness projections, and whether `AGENTS.md` is source, compatibility contract, or generated view.

### Integration lens: Copilot control plane / observability

Treat Lousy Agents' doctor and `agent-shell` as evidence for a control plane that distinguishes intent, tool execution, artifact mutation, verification, and agent claims. Decide what belongs in GitHub-native work surfaces versus Agent OS state. Prefer verifiable evidence over self-reported completion.

### Integration lens: automation / project curator

Design a continuous-curation loop where doctor findings, recurrence detection, lessons, and backlog state feed each other. Repeated findings may become candidate invariants or policies; resolved findings should retire cleanly; curators should evolve the portfolio rather than simply report it.

**Receiving-thread resolution:** this lens is now worked through in [`automation-curation-lens.md`](./automation-curation-lens.md). It settles the lane-scoped naming invariant, a seven-concept minimal automation ontology, the hard `Gov`/`Meta` boundary, the meta-curation loop, progressive-disclosure recipe structure, `grill-me` composition, and the adapter capability matrix. Treat that document as the current decision record for automation taxonomy/curation work rather than reopening these questions from scratch.

### Questions the receiving threads should resolve

- What is the smallest useful canonical ontology?
- What belongs in the graph versus harness adapters?
- What is an automation versus an agent, workflow, recipe, scheduled run, or policy?
- How should intent inherit across org/workspace/repo/automation/agent/run scopes?
- What evidence is sufficient to verify an agent claim?
- How do lessons graduate into durable policy without accumulating noise?
- How should doctor findings create, update, or close backlog work?
- Which stages must remain deterministic, and where is agent-assisted reasoning acceptable?
- How do we preserve native harness escape hatches without turning Agent OS into another mandatory harness?

Expected output from each receiving thread:

- accepted implications
- rejected implications with rationale
- ontology/taxonomy changes
- adapter/compiler changes
- governance/observability changes
- backlog items
- unresolved decisions that require interactive grilling

## Suggested skills

- `context-handoff` when moving conclusions between sessions or harnesses; keep future handoffs pointer-only.
- `find-before-build` before implementing concepts that Lousy Agents or an existing plugin already covers.
- `codebase-design` before committing to the canonical graph API or adapter interface.
- `grill-me` for high-blast-radius ontology and source-of-truth decisions.
- `redgate` for iterative architecture refinement and adversarial review.
- `recurrence-detector` when repeated doctor findings begin to suggest a candidate invariant.
- `docs-hygiene` before propagating generated cross-harness instruction surfaces.
