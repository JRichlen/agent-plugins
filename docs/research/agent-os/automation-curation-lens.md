# Agent OS integration lens: automation curation

## Decision

Agent OS is a **design and control plane for agent automations**. It guides the
creation, classification, composition, and ongoing curation of automations and
reusable recipes around workflows. It is not another agent runtime and it is
not a replacement for the working disciplines used while an agent executes a
task.

Harness-native scheduled tasks, GitHub workflows, Claude Code loops, Codex
jobs, Copilot agents, and future automation surfaces are observed/projected
through adapters. Agent OS gives them stable human-facing identity,
relationships, recipes, and desired evidence contracts.

**Redgate is deliberately a different layer.** Redgate is a harness/protocol
used while doing nontrivial work: it reinforces falsifiable criteria,
ARM/TRACE/JUDGE, independent verification, scope/attempt discipline, and
classified human gates. An Agent OS Recipe or Automation may recommend or use
Redgate as an execution policy, but Agent OS does not depend on Redgate for its
taxonomy, recipe authoring, interactive curation, or portability.

## The invariant

Every independently-running automation has one stable human-facing identity:

`<Lane> <Workstream>.<Agent>: <Short Name>`

Rules:

- The **lane key is the namespace** and stays short and distinct: `Blog`, `Gov`, `Ops`, `Meta`, etc.
- Numbering resets within each lane.
- The first number identifies a workstream inside the lane.
- The second number identifies an independently scheduled/triggered automation slot inside that workstream.
- The display token `.Agent` is an operator-facing convention for that independently-running slot; it is **not** the same semantic object as an Actor compiled by `agent-compiler`.
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

The concrete lane vocabulary is evolvable. The durable thing is the
namespacing rule and the relationship it encodes.

## Smallest useful automation ontology

Do not import every physical construct from every harness into the canonical
model. Start with seven semantic concepts:

1. **Lane** — human-facing domain namespace.
2. **Workstream** — related automations inside a lane.
3. **Automation** — one independently triggered execution contract.
4. **Trigger** — schedule, event, or condition that starts an automation.
5. **Recipe** — reusable workflow blueprint that can be invoked by a human or bound into one or more Automations; a Recipe is not independently scheduled by definition.
6. **Adapter** — projection/reconciliation boundary between Agent OS and a harness-native representation.
7. **Evidence** — run/output/verification material used to judge health and drive future curation.

Canonical relationships:

```text
Lane
  -> contains Workstream
      -> contains Automation
          -> triggeredBy Trigger
          -> follows Recipe*
          -> dependsOn Automation*
          -> feeds Automation*
          -> projectedVia Adapter+
          -> emits Evidence*
```

`dependsOn` is the blocking/ordering relationship. `feeds` is a looser data or
artifact handoff that does not necessarily block execution. Do not infer these
relationships only from clock spacing; schedules are an adapter mechanism, not
the semantic dependency graph.

Treat **Actor/agent** as an execution participant of an Automation or Recipe in
v1, not a competing top-level identity. `agent-compiler` owns deterministic
Actor composition. Agent OS owns why/when that Actor runs and how the resulting
automation fits the portfolio.

Likewise, keep these out of the v1 top-level ontology unless evidence forces
promotion:

- `Policy` is a constraint/property on nodes or relationships.
- `Capability` is a requirement/provision edge used by recipes/adapters.
- `ExecutionPolicy` is a Recipe/Automation property naming optional working disciplines such as Redgate; it does not need a top-level node in v1.
- `Memory` is curated state/evidence, not a universal bucket.
- `Runtime` is adapter/run metadata.
- native `AGENTS.md`, `CLAUDE.md`, Copilot instructions, workflow YAML, hooks, and MCP servers are projections or referenced capabilities, never canonical taxonomy nodes merely because they are files.

## Recipe versus adjacent concepts

Keep the distinctions explicit so adapters do not collapse everything into
"agent":

| Concept | Agent OS meaning |
|---|---|
| **Recipe** | Reusable workflow blueprint: ordered/conditional steps, capabilities, suggested skills, evidence expectations, and optional execution policies. No independent trigger. |
| **Automation** | A deployed/bound execution contract: identity + trigger + one or more recipes + adapter + relationships + expected evidence. |
| **Workflow** | A harness-native execution graph or implementation detail that may project a Recipe/Automation, e.g. GitHub Actions YAML or a Claude/Codex workflow. |
| **Skill** | Reusable behavioral capability/procedure a Recipe may call or recommend. Agent OS does not become the global skill router. |
| **Actor/Agent** | Execution participant. Actor composition belongs to `agent-compiler`; an Automation may bind one or more Actors. |

A Recipe can say, for example, "use `diagnosing-bugs` for diagnosis and use
`redgate` as the execution policy once the build loop begins" without Agent OS
reimplementing either skill.

## Layer model

```text
Agent OS                         Redgate
DESIGN / CONTROL PLANE           WORK / HARNESS PLANE
----------------------           --------------------
automation taxonomy              execution discipline
recipe authoring                 falsifiable criteria
trigger/dependency design        ARM / TRACE / JUDGE
adapter projection               independent verification
portfolio curation               classified human gates
interactive automation design    scope / attempts / rollback discipline

           optional composition
Automation / Recipe -----------> executionPolicy: redgate
```

Agent OS remains useful when Redgate is not installed. Redgate remains useful
for ordinary project work that has nothing to do with automation design.

## Lane boundary: `Gov` versus `Meta`

Keep this distinction hard:

- **Gov** governs the user's content/workspace/project portfolio: lifecycle, taxonomy of projects, privacy boundaries, archive/delete recommendations, and related knowledge hygiene.
- **Meta** governs the automation system itself: lane taxonomy, job design, overlap, cadence, tool discovery, dependencies, reliability, and synchronization of Agent OS guidance.

This prevents a workspace curator from silently gaining authority to rewrite
the machinery curating it.

## Three truths and reconciliation

Do not create a fake single source of truth for cross-harness automation.
There are three different truths:

1. **Design truth — Agent OS desired model.** Stable identity, lane/workstream placement, recipes, dependency edges, adapter intent, privacy boundary, and expected evidence.
2. **Existence truth — live harness state.** What jobs, schedules, triggers, permissions, and native artifacts actually exist right now.
3. **Runtime truth — evidence.** What actually ran, mutated, verified, failed, or produced an output.

Adapters reconcile design truth against existence truth; evidence tests whether
the resulting automation behaves as intended. Drift is a first-class finding,
not something to silently overwrite in either direction.

Reconciliation should classify differences as:

- **expected projection difference** — native harness representation differs but semantics match;
- **design drift** — live job changed away from desired Agent OS intent;
- **observed improvement** — live state contains a useful change that should be proposed back into design truth;
- **orphan** — live automation has no Agent OS identity yet;
- **missing projection** — desired automation has no live harness representation;
- **unverified** — projected state exists but runtime evidence is insufficient.

Mutation remains human-gated unless a narrower policy explicitly authorizes a
class of low-risk reconciliation.

## Meta loop

The canonical automation-curation loop is:

```text
discover -> normalize -> reconcile -> diagnose -> propose diff -> grill -> apply approved diff -> verify -> record evidence
```

### Discover

Inspect the actual automation inventory and currently available
tools/connectors/capabilities. Prefer native read APIs over remembered task
lists. Discovery should also find newly available capabilities that could
remove recurring manual work.

### Normalize

Map harness-native jobs into Lane / Workstream / Automation / Trigger / Recipe /
Adapter / Evidence without erasing native escape hatches.

### Reconcile

Compare the desired Agent OS model with live harness state and classify drift.
Do not silently make the desired model match whatever happens to exist, and do
not silently force live state to match stale desired intent.

### Diagnose

Look for:

- duplicates and overlapping responsibilities
- repeated full rescans that should share a ledger
- bad sequencing or hidden race conditions
- missing or implicit dependency edges
- fixed schedules that should be condition watches
- noisy notification policies
- stale/completed jobs
- work that is too broad and should split, or too narrow and should merge
- naming/numbering drift
- public/private boundary leaks
- unverified jobs whose effectiveness cannot be demonstrated
- opportunities to convert rediscovery into persistent state

### Propose diff

Express changes as explicit operations: create / rename / merge / split /
retire / reschedule / change trigger / change notification policy / change
dependency / change recipe binding / change execution policy. Prefer a small
high-value diff over perpetual reorganization.

### Grill

Structural changes remain human-gated. Agent OS supplies the automation-domain
decision tree. Compose the existing `grill-me` interaction model rather than
inventing a second generic interview protocol.

### Apply

Only approved operations mutate harness-native automation surfaces. Redgate may
be used while implementing a nontrivial approved change, but it is an optional
working discipline at this phase, not Agent OS's control plane.

### Verify

Re-read the resulting inventory and confirm the proposed
relationships/schedules actually exist. Where available, inspect execution
evidence instead of accepting self-reported completion.

### Record evidence

Persist enough state that the next curator run can operate on deltas instead of
rediscovering the world.

## Progressive disclosure: the `agent-os` skill

The eventual `agent-os` plugin should be deliberately small at the front door.

### Main skill owns only

- the lane/workstream/automation taxonomy
- the naming invariant
- the minimal ontology and dependency relationships
- Recipe versus Automation distinctions
- the `Gov`/`Meta` boundary
- desired-vs-observed reconciliation
- the curation loop
- recipe routing
- the human-gated mutation rule

Deep workflows live as progressively disclosed recipes/references.

### Recipe set

Proposed first recipes:

| Recipe | Purpose |
|---|---|
| `classify-new-automation` | Decide lane/workstream/key, trigger type, dependencies, recipe bindings, and whether the work deserves its own automation at all. |
| `design-automation-recipe` | Turn a recurring workflow into a reusable Recipe before binding it to any schedule/harness. |
| `grill-my-automations` | Interactive choose-your-own-adventure audit of the current automation portfolio. |
| `dedupe-and-consolidate` | Find overlapping jobs, shared ledgers, merge/split opportunities, and better sequencing. |
| `health-audit` | Diagnose stale/noisy/unverified automations and evidence gaps. |
| `tool-scout` | Discover available tools/connectors and propose automations grounded in repeated work or a clear system gap. |
| `bootstrap-portfolio` | First-run inventory and taxonomy normalization without assuming existing structure is correct. |
| `sync-agent-os-skill` | Diff durable taxonomy/design against the public skill and propose a review-gated update only when meaningfully changed. |

Recipes are not automatically scheduled agents. A scheduled task may follow a
Recipe, but the Recipe itself stays reusable and harness-portable.

## Interactive management: `grill-my-automations`

The desired experience is a choose-your-own-adventure book crossed with an
interactive terminal.

Do **not** emit a wall of open-ended questions.

Interaction contract:

1. Infer and show the current portfolio map first.
2. Find the highest-leverage unsettled automation-design branch.
3. Prefer the harness's native structured question/choice primitive when one exists. Discover the primitive available in the current harness; do not invent a canonical tool name.
4. Present compact single-select or multi-select options with a recommended route.
5. Let the answer reveal the next branch.
6. Repeat until the user chooses to stop or the design frontier is empty.
7. End with a proposed Agent OS diff: taxonomy, recipes, dependencies, adapters, and/or automation mutations.

When no native structured-question primitive exists, fall back to the same
compact option menu in text. Portability is behavioral, not dependent on a
specific UI API.

`grill-my-automations` should **compose with `grill-me`**, not fork it:

- Agent OS supplies the automation-domain decision tree and current inventory.
- `grill-me` supplies anchor/path-consent, stakes triage, frontier iteration, recommendations, and termination discipline.
- Agent OS itself decides which automation-design branches are low/high consequence.
- Redgate is not required for the interview. It may become relevant later if an approved design change is implemented through a nontrivial work loop.

## Lousy Agents mapping

Use Lousy Agents as prior art at these seams without copying its physical
taxonomy:

| Lousy Agents idea | Agent OS automation use |
|---|---|
| Doctor | Portfolio-wide automation diagnosis and topology findings. |
| Lint | Deterministic naming/schema/trigger/adapter invariants. |
| Lessons | Candidate durable rules, promoted only after recurrence/evidence. |
| Agent shell telemetry | Independent run/action evidence where adapters can expose it. |
| Harness capability matrix | Honest adapter matrix: what each harness can discover, mutate, schedule, question, observe, and verify. |

This also sharpens the distinction between **lint** and **curation**: lint
proves local invariants; the curator reasons about portfolio shape and proposes
changes.

## Existing plugin boundaries

Do not duplicate sibling plugins:

- **`agent-compiler`** owns deterministic Actor/behavior composition. Agent OS may bind/request an Actor shape but does not recompile personas itself.
- **`grill-me`** owns generic interactive design-tree interrogation. Agent OS provides the automation-specific tree/recipes.
- **`redgate`** owns a working harness/protocol for verified iterative execution. Agent OS may recommend it as `executionPolicy` or use it while implementing a design, but does not depend on it.
- **`diagnosing-bugs`, `codebase-design`, `orchestrate`, `scope-fence`, etc.** remain specialist working capabilities a Recipe may recommend. Agent OS does not replace their routing logic.
- **`recurrence-detector`** turns repeated failure shapes into candidate invariants; Agent OS decides whether those belong in automation policy/taxonomy.
- **`docs-hygiene`** checks generated/propagated instruction surfaces against current repo reality.
- **`context-handoff`** keeps cross-session/harness continuation pointer-first.
- **`find-before-build`** remains the guard against creating a new automation/recipe/plugin when one already exists.

## Skill-sync rule

The public `agent-os` skill is a **projection of settled automation design**,
not the source of truth for a user's live automation inventory.

Sync flow:

```text
desired Agent OS model + latest Meta curator decisions + observed adapter state
  -> extract durable principles
  -> diff agent-os skill/recipes
  -> validate
  -> review-gated PR
```

No meaningful design change means no PR. Never copy private conversation
content, secrets, private project details, or transient task state into the
public skill.

## Adapter capability matrix

Before claiming cross-harness support, rate **each capability independently**;
do not give a harness one misleading overall support level.

Dimensions:

- discover existing automations
- read schedules/triggers
- read native workflow/config artifacts
- create/update/disable/delete automations
- represent dependency edges natively or by projection
- bind/import Recipes
- inspect recent run evidence
- distinguish self-report from external/runtime evidence
- emit condition watches
- ask structured interactive questions
- preserve human approval gates
- project/import the Agent OS taxonomy
- detect drift and re-read after mutation

Each cell can be `native`, `partial`, `prose-only`, or `unsupported`, with a
short adapter-specific note. Claude Code, Codex, GitHub Copilot, GitHub Actions,
and scheduled-task systems should be evaluated capability by capability.

## Implementation order

1. Land this automation-curation lens as the receiving-thread decision record.
2. Design the `agent-os` main skill around taxonomy + Recipe design/routing.
3. Implement `design-automation-recipe` and `grill-my-automations` as the first progressively disclosed workflows.
4. Add deterministic cheap checks for the naming invariant, dependency relationship vocabulary, progressive-disclosure links, and sibling-plugin boundaries.
5. Add an adapter capability matrix before promising cross-harness mutation support.
6. Only then wire actual harness mutation adapters/tool schemas.
7. Add optional execution-policy guidance (including Redgate) without making any one harness discipline mandatory.

The first release should be useful even when it can only **discover, classify,
design recipes, diagnose, reconcile, and propose**. Mutation and execution
policy support can deepen adapter by adapter without changing the canonical
taxonomy.
