# Agent OS integration lens: automation curation

## Decision

Agent OS should present itself as a **meta-framework for curating automations across agent harnesses**, not as another agent runtime.

Its primary contract is the automation taxonomy. Harness-native scheduled tasks, GitHub workflows, Claude Code loops, Codex jobs, Copilot agents, and future automation surfaces are adapters/projections of that taxonomy.

This lens resolves the automation/project-curator questions from the Lousy Agents handoff and gives the future `agent-os` skill a concrete shape.

## The invariant

Every independently-running automation has one stable human-facing identity:

`<Lane> <Workstream>.<Agent>: <Short Name>`

Rules:

- The **lane key is the namespace** and stays short and distinct: `Blog`, `Gov`, `Ops`, `Meta`, etc.
- Numbering resets within each lane.
- The first number identifies a workstream inside the lane.
- The second number identifies an independently scheduled/triggered agent inside that workstream.
- Internal subagents do **not** get hierarchy numbers unless they independently run.
- New lanes are earned by distinct recurring work, not created speculatively.
- Stable names stay stable while their meaning remains valid; curation should reduce churn, not produce it.

Example shape:

```text
Blog 1.1: Editorial
Blog 1.2: Projects
Blog 1.3: Direction
Gov 1.1: Curator
Ops 1.1: Plugin Sync
Meta 1.1: Curator
Meta 1.2: Skill Sync
```

The concrete lane vocabulary is evolvable. The durable thing is the namespacing rule and the relationship it encodes.

## Smallest useful automation ontology

Do not import every physical construct from every harness into the canonical model. Start with seven semantic concepts:

1. **Lane** — human-facing domain namespace.
2. **Workstream** — related automations inside a lane.
3. **Automation** — one independently triggered execution contract.
4. **Trigger** — schedule, event, or condition that starts an automation.
5. **Recipe** — reusable process an automation or human can invoke; not independently scheduled by definition.
6. **Adapter** — projection between the canonical automation and a harness-native representation.
7. **Evidence** — run/output/verification material used to judge health and drive future curation.

Relationships:

```text
Lane
  -> contains Workstream
      -> contains Automation
          -> triggeredBy Trigger
          -> follows Recipe*
          -> projectedVia Adapter+
          -> emits Evidence*
```

Treat **Actor/agent** as an execution detail of an Automation or Recipe in v1, not a competing top-level identity. `agent-compiler` can own actor composition. Agent OS owns why/when that actor runs and how the resulting automation fits the portfolio.

Likewise, keep these out of the v1 top-level ontology unless evidence forces promotion:

- `Policy` is a constraint on nodes/edges.
- `Capability` is a requirement/provision edge used by recipes/adapters.
- `Memory` is curated state/evidence, not a universal bucket.
- `Runtime` is adapter/run metadata.
- native `AGENTS.md`, `CLAUDE.md`, Copilot instructions, workflow YAML, hooks, and MCP servers are projections or referenced capabilities, never canonical taxonomy nodes merely because they are files.

## Lane boundary: `Gov` versus `Meta`

Keep this distinction hard:

- **Gov** governs the user's content/workspace/project portfolio: lifecycle, taxonomy of projects, privacy boundaries, archive/delete recommendations, and related knowledge hygiene.
- **Meta** governs the automation system itself: lane taxonomy, job design, overlap, cadence, tool discovery, dependencies, reliability, and synchronization of Agent OS guidance.

This prevents a workspace curator from silently gaining authority to rewrite the machinery curating it.

## Meta loop

The canonical automation-curation loop is:

```text
discover -> normalize -> diagnose -> propose diff -> grill -> apply approved diff -> verify -> record evidence
```

### Discover

Inspect the actual automation inventory and currently available tools/connectors/capabilities. Prefer native read APIs over remembered task lists. Discovery should also find newly available capabilities that could remove recurring manual work.

### Normalize

Map harness-native jobs into Lane / Workstream / Automation / Trigger / Recipe / Adapter / Evidence without erasing native escape hatches.

### Diagnose

Look for:

- duplicates and overlapping responsibilities
- repeated full rescans that should share a ledger
- bad sequencing or hidden race conditions
- fixed schedules that should be condition watches
- noisy notification policies
- stale/completed jobs
- work that is too broad and should split, or too narrow and should merge
- naming/numbering drift
- public/private boundary leaks
- unverified jobs whose effectiveness cannot be demonstrated
- opportunities to convert rediscovery into persistent state

### Propose diff

Express changes as explicit operations: create / rename / merge / split / retire / reschedule / change trigger / change notification policy / change dependency. Prefer a small high-value diff over perpetual reorganization.

### Grill

Structural changes remain human-gated. Use the existing `grill-me` interaction model rather than inventing a second interview protocol.

### Apply

Only approved operations mutate the harness-native automation surfaces. Never treat a neighboring approval as permission for a materially different mutation.

### Verify

Re-read the resulting inventory and confirm the proposed relationships/schedules actually exist. Where available, inspect execution evidence instead of accepting self-reported completion.

### Record evidence

Persist enough state that the next curator run can operate on deltas instead of rediscovering the world.

## Progressive disclosure: the `agent-os` skill

The eventual `agent-os` plugin should be deliberately small at the front door.

### Main skill owns only

- the lane/workstream/automation taxonomy
- the naming invariant
- the minimal ontology
- the `Gov`/`Meta` boundary
- the curation loop
- recipe routing
- the human-gated mutation rule

Deep workflows live as progressively disclosed recipes/references.

### Recipe set

Proposed first recipes:

| Recipe | Purpose |
|---|---|
| `classify-new-automation` | Decide lane/workstream/key, trigger type, and whether the work deserves its own automation at all. |
| `grill-my-automations` | Interactive choose-your-own-adventure audit of the current automation portfolio. |
| `dedupe-and-consolidate` | Find overlapping jobs, shared ledgers, merge/split opportunities, and better sequencing. |
| `health-audit` | Diagnose stale/noisy/unverified automations and evidence gaps. |
| `tool-scout` | Discover available tools/connectors and propose automations grounded in repeated work or a clear system gap. |
| `bootstrap-portfolio` | First-run inventory and taxonomy normalization without assuming existing structure is correct. |
| `sync-agent-os-skill` | Diff durable taxonomy/design against the public skill and propose a review-gated update only when meaningfully changed. |

Recipes are not automatically scheduled agents. A scheduled task may follow a recipe, but the recipe itself stays reusable.

## Interactive management: `grill-my-automations`

The desired experience is a choose-your-own-adventure book crossed with an interactive terminal.

Do **not** emit a wall of open-ended questions.

Interaction contract:

1. Infer and show the current portfolio map first.
2. Find the highest-leverage unsettled branch.
3. Prefer the harness's **native structured question/choice primitive** when one exists. Discover the primitive available in the current harness; do not invent a tool name.
4. Present compact single-select or multi-select options with a recommended route.
5. Let the answer reveal the next branch.
6. Repeat until the user chooses to stop or the decision frontier is empty.
7. End with a proposed automation diff, not a prose transcript of the interview.

When no native structured-question primitive exists, fall back to the same compact option menu in text. Portability is behavioral, not dependent on a specific UI API.

`grill-my-automations` should **compose with `grill-me`**, not fork it:

- Agent OS supplies the automation-domain decision tree and current inventory.
- `grill-me` supplies anchor/path-consent, stakes triage, frontier iteration, recommendations, and termination discipline.
- Structural or high-blast-radius automation mutations are STANDARD/DEEP branches.
- Low-risk classification or naming choices can remain LIGHT.

## Lousy Agents mapping

Use Lousy Agents as prior art at these seams without copying its physical taxonomy:

| Lousy Agents idea | Agent OS automation use |
|---|---|
| Doctor | Portfolio-wide automation diagnosis and topology findings. |
| Lint | Deterministic naming/schema/trigger/adapter invariants. |
| Lessons | Candidate durable rules, promoted only after recurrence/evidence. |
| Agent shell telemetry | Independent run/action evidence where adapters can expose it. |
| Harness capability matrix | Honest adapter matrix: what each harness can discover, mutate, schedule, question, observe, and verify. |

This also sharpens the distinction between **lint** and **curation**: lint proves local invariants; the curator reasons about portfolio shape and proposes changes.

## Existing plugin boundaries

Do not duplicate sibling plugins:

- **`agent-compiler`** owns deterministic actor/behavior composition. Agent OS may request an actor shape but does not recompile personas itself.
- **`grill-me`** owns the general interactive design-tree interrogation. Agent OS provides the automation-specific tree/recipes.
- **`redgate`** owns verified iterative execution and classified human gates for implementation work.
- **`recurrence-detector`** turns repeated failure shapes into candidate invariants; Agent OS decides whether those belong in automation policy/taxonomy.
- **`docs-hygiene`** checks generated/propagated instruction surfaces against current repo reality.
- **`context-handoff`** keeps cross-session/harness continuation pointer-first.
- **`find-before-build`** remains the guard against creating a new automation/recipe/plugin when one already exists.

## Skill-sync rule

The public `agent-os` skill is a **projection of settled automation design**, not the source of truth for a user's live automation inventory.

Sync flow:

```text
live inventory + latest Meta curator decisions
  -> extract durable principles
  -> diff agent-os skill/recipes
  -> validate
  -> review-gated PR
```

No meaningful design change means no PR. Never copy private conversation content, secrets, private project details, or transient task state into the public skill.

## Adapter capability matrix

Before claiming cross-harness support, each adapter should state whether it can:

- discover existing automations
- read schedules/triggers
- create/update/disable/delete automations
- inspect recent run evidence
- emit condition watches
- ask structured interactive questions
- preserve human approval gates
- project/import the Agent OS taxonomy

Support depth should be explicit (`native`, `partial`, `prose-only`, `unsupported`) rather than implied by the existence of an instruction file.

## Implementation order

1. Land this automation-curation lens as the receiving-thread decision record.
2. Design the `agent-os` main skill around taxonomy + recipe routing.
3. Implement `grill-my-automations` as the first recipe/skill composition with `grill-me`.
4. Add deterministic cheap checks for the naming invariant, progressive-disclosure links, and sibling-plugin boundaries.
5. Add an adapter capability matrix before promising cross-harness mutation support.
6. Only then wire actual harness mutation adapters/tool schemas.

The first release should be useful even when it can only **discover, classify, diagnose, and propose**. Mutation support can deepen adapter by adapter without changing the canonical taxonomy.
