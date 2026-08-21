---
name: codebase-design
description: >-
  Before writing a new interface (module boundary, class API, function
  signature, or service contract) that at least two call sites will depend
  on, that crosses a module/service/team/persistence boundary, or that will
  be expensive to change later — produce 3+ radically different candidate
  designs and compare them on depth, locality, and seam placement before
  picking one. Use on "before committing to an interface", "design this
  API/module/class boundary", "how should this be structured", "compare
  interface designs", "is this the right abstraction", "design it twice",
  reviewing a proposed interface shape in a PR — or self-trigger whenever
  about to write a new interface meeting that bar.
license: MIT
compatibility: >-
  PORTABILITY: harness-agnostic. The core design-it-twice procedure is plain
  reasoning and prose comparison — no subagent-spawning tool, no Workflow
  tool, no hooks, no harness-specific primitive required. An optional
  parallel-subagent escalation exists only where a subagent-spawning tool is
  present (see the Portability section below) — a convenience, not a
  dependency, mirroring voice's "hook is a convenience, not a dependency"
  pattern rather than second-opinion's hard gate on subagents.
---

# codebase-design

## Invariant

Before committing to an interface (a module boundary, class API, or function signature that ≥2 call sites will depend on, or that crosses a service/team/persistence boundary, or that is expensive to change later): ALWAYS produce 3+ radically different candidate designs and compare them on depth, locality, and seam placement before picking one — NEVER let the first workable interface ship unexamined. The chosen interface must ALWAYS hide its implementation complexity behind a boundary that tests hold honest at a confirmed seam — NEVER a shallow pass-through whose interface exists only to make internals swappable, and NEVER a test written against an unconfirmed seam.

## Not this

Three plugins in this marketplace share enough vocabulary to be reached for
by mistake. None of them is this skill.

- **orchestrate** (`plugins/orchestrate/skills/orchestrate`) ships two
  Workflow-tool templates for fanning subagents out over RESEARCH dimensions
  and adversarially verifying the CLAIMS that research surfaces — frozen
  ground-truth context, per-stage JSON schemas, a verifier that defaults to
  disbelief. It is fact-checking machinery for information gathering.
  codebase-design borrows only the *shape* of "produce several, then
  compare" — applied to DESIGN ALTERNATIVES the agent itself generates, not
  to claims a research fan-out surfaced — and it needs no Workflow tool, no
  per-stage schema, no adversarial verifier. Default execution is one agent
  working through 3+ designs sequentially in a single session; a
  subagent-spawning tool, if available, may optionally dispatch the 3
  designs in parallel for extra independence (Step 1), but that is a
  borrowed optimization, never a dependency, and it never pulls in
  orchestrate's verify/harvest/reconcile machinery — these are competing
  designs, not assertions to fact-check.
- **second-opinion** (`plugins/voice/skills/second-opinion`) is *post-hoc and
  offer-only*: it validates a verdict that already exists, batches
  fact-checks plus scoped advisor personas, and is forbidden from emitting
  its grouped Verified/Flagged/Conflict output unless subagents actually
  dispatched and reported back. codebase-design is *pre-hoc and
  self-triggering* on the interface-shaped heuristic in Step 0 — it runs
  BEFORE an interface is written, produces designs rather than validating
  one that already exists, and never needs a subagent-spawning tool to do
  its core job.
- **grill-me** (`plugins/grill-me/skills/grill-me`) is the closest surface
  match — it too runs "before starting a nontrivial multi-step change whose
  design isn't yet settled" and walks a "design tree." But grill-me is a
  live, single-session CONVERSATIONAL INTERVIEW of the USER aimed at
  reaching shared understanding of a PLAN. codebase-design never interviews
  the user as its core mechanism — it is the agent GENERATING and
  self-comparing 3+ concrete interface designs against objective axes
  (depth/locality/seam placement), with no requirement that the user
  participate turn-by-turn. The two are complementary: grill-me's frontier
  loop can reach a branch that IS an interface decision (Step 0's heuristic)
  and at that branch hand off to design-it-twice instead of asking the user
  to freehand an API in conversation — but the two must never merge into one
  "design conversation" skill that does neither job well.

## Step 0 — Is this interface-shaped?

Apply this heuristic before doing anything else — it's the gate that stops
overhead on trivial code. The decision is interface-shaped, and the rest of
this procedure applies, if ANY of these hold:

- **≥2 call sites** will depend on this shape (not counting the one you're
  writing right now).
- It **crosses a boundary** — a module, service, team, or persistence
  boundary: a public API, a network contract, a DB schema, a package export.
- It would be **expensive or breaking to change later** (this is
  semver-gate's MAJOR-class test in miniature: does changing this later
  break a contract someone else depends on?).
- You are about to write a **genuinely new abstraction** — roughly 30+ lines
  of new module/class scaffolding — not extending an existing,
  already-judged one.

If NONE hold — a private helper, a single call site, an internal
implementation detail nobody else touches — say so in one line ("trivial,
not interface-shaped, skipping design-it-twice") and go straight to
implementation. Do not manufacture a 3-design comparison for a getter. This
mirrors grill-me's "if the whole plan triages LIGHT end to end, say so
briefly and move on" discipline — the same anti-overhead norm, aimed at
interface decisions instead of whole plans.

## Step 1 — Produce 3+ radically different designs

Load `references/design-it-twice.md` now. Generate at least 3 candidate
interfaces for the SAME piece of functionality. "Radically different" is a
checkable bar, not a vibe: each candidate must differ from every other
candidate on at least one of the three axes in Step 2 by more than a rename
or parameter reorder. Four generator prompts force real divergence — use at
least 2 of them across the 3 candidates so they don't converge on one shape:

1. Vary **where state lives** — fully inside the module, passed in by the
   caller each call, or externalized to a shared store.
2. Vary the **call shape** — a single synchronous call, event/message-driven,
   or declarative/config-driven (the caller states the desired end-state,
   the module figures out how).
3. Vary the **surface size** — one fat interface exposing every step, one
   thin single-entry facade, or a composable pipeline of small pieces.
4. Vary **who owns error/retry/edge-case handling** — the caller, the
   callee, or a shared policy object both consult.

The default path needs no subagent-spawning tool: generate all 3 designs
yourself, sequentially, in this session, explicitly trying to make each one
defensible on its own terms before moving to the next (don't let candidate 2
be a strawman built to lose to candidate 1). If a subagent-spawning tool
happens to be available, you MAY optionally dispatch each candidate to a
separate agent in parallel for genuine independence — that's an optimization
borrowed from orchestrate's fan-out habit (see "Not this"), never a
dependency; see Portability below.

## Step 2 — Compare on depth, locality, seam placement

Still from `references/design-it-twice.md`. For EACH candidate, answer these
three named questions — the "exact check" that replaces "be careful":

1. **DEPTH** — what's the ratio of caller-visible footprint (parameter
   count + required call-order + config surface) to hidden decision count
   (branches/states/error cases handled internally)? A small footprint
   hiding a lot is deep (good); a footprint roughly 1:1 with what it does is
   shallow.
2. **LOCALITY** — if a bug fix or a plausible future requirement change hits
   this concern, how many call sites/files need to change? Does correct
   usage require the caller to hold a cross-call invariant in their head
   (call A before B, remember to call C)? Fewer forced call sites and no
   caller-held invariants is better locality.
3. **SEAM PLACEMENT** — apply the deletion test now (full definition in
   `references/deep-modules.md`, applied here to pick a winner): mentally
   delete the module and inline its logic at each call site. Does real
   complexity (branching, error handling, I/O) disappear from the codebase
   (a real seam — the module earned its boundary), or does the code read
   almost identically minus one layer of indirection (a pass-through, not a
   seam)?

Build a 3-candidates x 3-axes comparison — a short table or three short
paragraphs, whichever the answer's complexity warrants — then pick a winner
and write ONE paragraph of rationale that cites the specific depth/locality/
seam answers that decided it. Never "this one felt cleaner." If two
candidates tie, **locality wins the tiebreak**: a design that concentrates
change in fewer places compounds in your favor over the module's lifetime
more than a marginal depth or seam difference does.

## Step 3 — Confirm seams before writing any implementation

Load `references/deep-modules.md` now (Seam-Based Design & Test Agreement
subsection). For the CHOSEN design only, name each seam explicitly as a
short bullet list — "this call boundary is a confirmed seam; tests double
here and nowhere else." Apply the two-adapter check from the same reference
to each named seam: can you name a second concrete implementation this
boundary would have to support (a fake for tests, a different backend, a v2
protocol)? If yes, the seam is real — keep it. If you can only imagine one
implementation ever existing, it's a hypothetical seam: either find the real
external boundary further out and move the seam there, or drop the boundary
and let the code be direct. A test written against a boundary that fails
this check does not earn its place — per the Seam-Based Design & Test
Agreement, no test at an unconfirmed seam — flag it as a smell rather than
writing it.

## Step 4 — Final depth check before handoff

Still in `references/deep-modules.md` (Module Depth Analysis subsection).
Classify the chosen design's dependencies into four categories to decide
what gets a test double and what doesn't:

1. **Pure/internal logic** — no I/O, deterministic given inputs. Test
   directly, no mocking.
2. **Owned deep dependency** — another module in this codebase that already
   has its own confirmed seam and its own tests. Call it for real;
   re-mocking it here duplicates an assumption and hides integration bugs.
3. **Unowned external boundary** — a third-party API, the network, the
   filesystem, the clock, another team's service: something outside your
   control that can fail or change independently. This is where a test
   double belongs, and the only place one belongs.
4. **Config/environment surface** — values that vary by deploy, not by
   logic. Inject as parameters; test by passing fixed values through, never
   by mocking a getter.

Diagnostic — the over-fragmentation check: if the chosen interface exists
ONLY so a test can swap out a category-1 or category-2 dependency (the sole
reason for the boundary is testability, not a real external system), that's
exactly the thin, testability-only interface failure mode. Collapse it back
into its caller and push the test out to the real category-3 boundary
instead. A module whose only adapter will ever be itself just failed the
two-adapter check from Step 3 as well — the two diagnostics should agree.

## Step 5 — Ship the decision, not the debate

Output is: the chosen design (interface signature/shape), the one-paragraph
rationale from Step 2, the named-seams list from Step 3, and nothing about
the 2+ rejected designs beyond a one-line "considered and rejected: X
(shallow — Y), Z (poor locality — W)" — enough for someone reading the
decision later to know it wasn't the first idea, without carrying the full
comparison forward. Implementation itself is out of scope for this skill —
it hands off to whatever writes the code/tests next. Design-then-implement
is a front-loaded, distinct step, not interleaved with coding.

## Portability

Default mode needs NO subagent-spawning tool: Step 1's 3+ designs are
produced sequentially by the same agent in one session — the
always-available path, matching grill-me's "no subagents required"
portability class, not second-opinion's hard gate. Where a
subagent-spawning tool (e.g. Claude Code's Task/Workflow tool) IS available,
Step 1 MAY optionally dispatch the 3 candidate generations in parallel for
genuine independence (each agent proposes without seeing the others first)
— the one place this skill's shape echoes orchestrate's fan-out habit (see
"Not this"). The escalation is always optional and never changes Steps 2-5.
