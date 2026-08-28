# Design: `agent-compiler` plugin

**Status:** Proposed — design only, no implementation in this PR.
**Source material:** the `agent-compiler-handoff` design package (README, docs 00–08,
ADRs 0001–0004, JSON schemas, examples, TypeScript scaffold). This document is the
refinement of that handoff into a plugin that fits this marketplace's conventions.

## 1. What the handoff proposes, in one paragraph

Agents are compiled, not stored. Humans author small, addressable **behavior
modules** (Markdown + YAML frontmatter + XML-like `<rule>`/`<probe>`/`<antipattern>`
blocks, each with a stable ID). A model may turn fuzzy intent into a typed
**AgentQuery**, but everything after that boundary is deterministic: a resolver
selects modules, expands dependencies, detects conflicts, validates requested
capabilities against an **effect ceiling**, and emits an immutable, content-hashed
**AgentImage** with per-unit provenance. Execution (an ExecutionPlan DAG behind an
MCP `execute` tool) is explicitly deferred; the handoff's own v0.1 is only the
compiler kernel plus read-only `inspect`/`compile`.

## 2. The core fit: the deterministic boundary is this marketplace's house style

The handoff's central invariant —

> Natural language may **select** behavior; it may not silently **define** behavior.

— is structurally the same move the graveyard plugin already makes: the model
orchestrates and explains, but the consequential artifact is produced by a
deterministic script the model cannot improvise around. That mapping drives the
whole design:

| Handoff concept | Plugin realization |
|---|---|
| intent → AgentQuery (LLM allowed) | the skill: an interview/normalization step the model performs |
| AgentQuery → AgentImage (deterministic) | a single-file, stdlib-only script the command invokes |
| MCP `inspect` / `compile` facade | plugin commands first (`/agent-inspect`, `/agent-compile`); MCP later |
| MCP `execute` + runtime DAG | **cut** — the harness *is* the runtime (see §6) |
| effect ceiling enforcement | compile-time link check + emitted permission manifest (see §5.4) |
| golden / metamorphic tests | the cheap eval tier, verbatim (see §7) |

## 3. Scope refinement: what a plugin can honestly be

The handoff describes a platform. A marketplace plugin cannot ship a graph
registry service, a policy engine, and a workflow scheduler — and per this repo's
discipline it should not try. Three deliberate narrowings:

1. **Compile to artifacts the ecosystem already executes.** The handoff leaves
   "what consumes an AgentImage?" abstract. Here the answer is concrete: the
   AgentImage is canonical JSON, and thin **renderers** emit harness-native
   agent definitions from it — a Claude Code subagent file
   (`.claude/agents/<name>.md` with frontmatter `tools`/`model`), a `SKILL.md`,
   or the equivalent for other harnesses. The cross-harness guarantee this
   marketplace already keeps via `AGENTS.md` symlinks becomes: one image, many
   renderings, all traceable to the same hash.
2. **No capability linker in v0.1.** Behavior modules may *declare* required
   capability interfaces (`scm.pull_request.read`); the compiler records them and
   validates them against the effect ceiling. Binding interfaces to concrete
   MCP servers/tools is deferred until a real second provider exists to link
   against (the handoff itself ranks this Phase 3).
3. **No execution, ever, inside this plugin.** The handoff defers `execute`;
   this design removes it. Claude Code, codex, gemini etc. already are
   schedulers with permission systems. Rebuilding retries/locks/approvals inside
   a plugin would duplicate the harness badly. What survives from the effect
   system is compile-time: refuse to compile an image whose declared effects
   exceed its ceiling, and emit the ceiling in a form the harness can enforce.

## 4. The invariant this plugin defends

Marketplace rule: every plugin leads with the clause its evals defend.

> Given the same registry revision, query, and compiler version, compilation
> produces a **byte-identical canonical AgentImage and identical hash**. The
> compiler **never invents behavior text** — every emitted unit carries
> provenance to a source module — and it **fails closed**: unresolved conflicts,
> missing dependencies, dependency cycles, and effects above the query's ceiling
> are compile errors, not warnings.

Weakening any clause (a nondeterministic sort, a silently dropped conflict, a
"best effort" effect check, prose emitted without provenance) is the regression
class the evals exist to catch.

## 5. Plugin architecture

### 5.1 Layout

```
plugins/agent-compiler/
  .claude-plugin/plugin.json
  AGENTS.md  (+ CLAUDE.md/GEMINI.md symlinks)
  README.md
  commands/
    agent-compile.md      # /agent-compile — intent → query → image → rendering
    agent-inspect.md      # /agent-inspect — browse/search the registry, explain provenance
  skills/
    agent-compiler/
      SKILL.md            # the boundary discipline + authoring guide
      references/
        language.md       # module format: frontmatter keys, semantic blocks, ID rules
        schemas/          # behavior-module / agent-query / agent-image JSON Schemas (from the handoff)
      scripts/
        compile.py        # the deterministic kernel (stdlib-only python3)
        render_claude_agent.py   # AgentImage → .claude/agents/<name>.md
  registry/               # starter behavior modules (evidence, security/iam, views)
  evals/
    cheap/checks.sh       # golden-hash + metamorphic + fail-closed checks
    promptfoo/            # behavioral pack (skill-prose changes)
```

### 5.2 The kernel (`compile.py`)

Python 3 stdlib only — the same toolchain the cheap tier already requires
(bash + python3), fully offline, no package manager. One file, pure-function
stages mirroring the handoff pipeline: parse → validate → lower to ABIR →
index → resolve selectors → expand dependencies → detect cycles/conflicts →
validate effects → canonicalize (explicit partial order, lexicographic ID
tiebreak — never filesystem traversal order) → attach provenance → stable JSON
render → SHA-256 → AgentImage. Diagnostics are structured JSON, not prose
exceptions. The handoff's TypeScript scaffold is treated as pseudocode; its
stage names and types carry over directly.

Interface (all deterministic, all scriptable from evals):

```sh
compile.py compile  --registry <dir> --query <query.json> [--out <image.json>]
compile.py inspect  --registry <dir> [--id <id> | --kind <kind> | --tag <tag>]
compile.py explain  --image <image.json> --unit <unit-id>   # provenance chain
```

### 5.3 The skill: owning the nondeterministic side

`SKILL.md` governs exactly the part the script cannot: turning fuzzy intent into
a typed AgentQuery, and *refusing* to smuggle behavior past the boundary. Its
load-bearing rules:

- Interview or infer until the query's coordinates (role, task, domains, views,
  stance, environment, effect ceiling) are explicit; show the query JSON before
  compiling.
- If the user's intent needs behavior that no registry module provides, the move
  is **author a module, then recompile** — never paste prose into the rendered
  agent. New behavior enters through the registry or not at all.
- Fuzzy discovery may *suggest* module IDs (`inspect`); the compile call consumes
  exact IDs only.
- On compile errors, relay the structured diagnostics and help resolve them in
  source (add a `supersedes` edge, split a module) — never by suppressing the check.

### 5.4 Effects → harness permissions

The AgentImage records declared effects and the query's ceiling. The Claude Code
renderer translates that into the subagent's frontmatter `tools:` list and, where
useful, a suggested `settings.json` permission block — so "read-only reviewer"
is enforced by the harness's own permission layer, not by prose. This is the
handoff's ADR 0004 ("permissions are checked structurally") relocated to where
structure already exists.

### 5.5 Marketplace wiring

Scaffolded with `plugin-factory` (its red-by-default eval skeleton is exactly
right here), registered in `marketplace.json`, name matching directory, version
`0.1.0`. Keywords: `agent-compiler`, `behavior-modules`, `deterministic`,
`provenance`, `subagents`, `persona`.

## 6. What is cut from the handoff, and why

- **`execute` / ExecutionPlan runtime** — the harness is the executor; the
  plugin's job ends at a validated, rendered artifact. (ExecutionPlan schema is
  kept in `references/` as future work, not implemented.)
- **Graph database, semantic search, marketplace of modules** — the handoff
  itself defers these; flat files + generated indices.
- **MCP facade** — deferred to a later phase, not cut. Claude Code plugins can
  bundle MCP servers, so `inspect`/`compile` (read-only, pure — matching the
  handoff's trust-boundary argument) can be exposed once the CLI kernel is
  stable. Commands come first because they're testable offline and cost no
  model-visible tool surface until proven useful.
- **Capability linker** — declarations validated, bindings deferred (§3.2).
- **Model-specific prompt rendering inside the hash** — open question 11/12 in
  the handoff, resolved here: the hash covers the canonical AgentImage only;
  renderers are versioned separately and record `(imageHash, rendererVersion)`
  in the emitted artifact's header comment. Rendering can evolve without
  invalidating image identity.

## 7. Eval mapping (the reason this design fits this repo)

The handoff's own evaluation chapter is nearly a specification of this repo's
cheap tier, which is the strongest signal the plugin belongs here.

**cheap — deterministic, offline, <1s.** Runs the real kernel against the
bundled `registry/` and fixture queries:

- *Golden:* the fixture query compiles to a pinned hash; repeated compilation is
  byte-identical.
- *Metamorphic* (handoff §06, directly): re-running with shuffled file discovery
  order changes nothing; adding an unrelated module changes nothing; a read-only
  ceiling never links a write effect.
- *Fail-closed:* fixtures with a conflicting rule pair, a missing dependency, a
  dependency cycle, and an over-ceiling effect must each fail with the expected
  diagnostic code.
- Plus the marketplace's standing checks (manifest validity, wiring, `bash -n`,
  `python3 -m py_compile`).

A counterfeit fixture (weakened-guard style) mutates the effect check into a
warning and asserts the tier rejects it — proving the gate discriminates.

**behavioral — promptfoo, on skill-prose changes.** A model given the skill and
a fuzzy request ("make me a paranoid security reviewer for our terraform repo")
must produce a valid AgentQuery and invoke compile — and, given intent the
registry can't satisfy, must propose authoring a module rather than inlining
prose into the output. The second case is the one worth paying for: it tests the
boundary, not the happy path.

**deep — not required at v0.1.** The plugin performs no irreversible or
effectful action; there is nothing a sandbox proves that the cheap tier doesn't.
One wiring caveat: the CI deep-tier gate fires on
`plugins/*/skills/**/scripts/**`, so commits touching `compile.py` will trigger
the pier run as written. Either accept that cost or narrow the gate's glob to
the graveyard's scripts when this plugin lands — to be decided in the
implementation PR, not silently here.

**demonstration — required, and easy.** The PR that lands the skill compiles an
agent from this repository's own material (e.g. a "marketplace reviewer" built
from modules encoding the eval discipline), shows the query, the image hash, the
rendered subagent, and at least one compile *failure* with its diagnostic — the
misses requirement, satisfied honestly.

## 8. Phasing

1. **Phase 0 (this doc):** design, invariant, schemas adopted from the handoff.
2. **Phase 1:** kernel + starter registry + cheap evals + `/agent-compile`,
   `/agent-inspect` + Claude Code renderer. Exit: pinned golden hash in CI.
3. **Phase 2:** renderers for a second harness; `explain` provenance UX;
   behavioral pack.
4. **Phase 3:** bundled MCP server exposing `inspect`/`compile` (read-only).
5. **Deferred indefinitely:** capability linker beyond presence-checking,
   `execute`, graph storage.

## 9. Open questions carried forward

From the handoff's 32, the ones that actually gate Phase 1 (resolve by
prototype, per the handoff's own advice):

- How much XML-like block syntax before authoring gets cumbersome? (Start with
  exactly four blocks: `rule`, `probe`, `example`, `antipattern`. No nesting.)
- Which query dimensions are first-class vs. tags? (Start with the handoff's
  `AgentQuery` schema as-is; promote nothing until a selector needs it.)
- Where does a *user's* registry live — inside the plugin, in the target repo,
  or both with enterprise-baseline layering? (Phase 1: plugin ships a starter
  `registry/`; `--registry` accepts any directory, so a repo can carry its own.
  Layering/override semantics are Phase 2+, and the handoff's governance
  questions 26–28 stay open.)
