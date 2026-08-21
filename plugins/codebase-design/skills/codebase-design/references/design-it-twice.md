# design-it-twice: the comparison procedure

Loaded from SKILL.md Step 1 (once you're about to generate candidates) and
Step 2 (once 3+ candidates exist and need scoring). This file carries the
exact definitions, the comparison-table template, and worked examples so the
pattern is concrete, not abstract.

PORTABILITY: the comparison itself is plain reasoning and prose — no
subagent-spawning tool required. The one optional escalation this file
describes (parallel candidate generation) is a convenience where a
subagent-spawning tool exists, never a dependency; see "Optional: parallel
generation" at the end of this file.

## The three axes, precisely

### DEPTH

> Ratio of caller-visible footprint to hidden decision count.

- **Footprint** = parameter count + required call-order constraints + config
  surface the caller must understand to use the interface correctly.
- **Hidden decision count** = branches, states, and error cases the
  implementation handles internally, that the caller never has to think
  about.

Scoring question: *if I had to explain how to call this correctly in one
sentence, and separately list everything it handles so the caller doesn't
have to — which list is longer?* A deep design has a short "how to call it"
and a long "what it handles." A shallow design has the two lists roughly the
same length — the interface is barely doing more than exposing its own
internals.

### LOCALITY

> How many places a plausible future change touches, and whether the caller
> has to hold a cross-call invariant in their head.

Scoring questions:
1. Pick one plausible bug fix and one plausible future requirement change for
   this concern. For each, count the files/call sites that would need to
   change.
2. Does correct usage require calling things in a specific order, or
   remembering a cleanup/pairing call (open before close, subscribe before
   publish, lock before unlock)? Every such invariant is a place a caller can
   silently get it wrong — count them as a locality cost even though no
   change has happened yet.

A design with fewer touched files per plausible change, and zero
caller-held invariants, has better locality. This is the axis most sensitive
to guessing — pick a *specific*, plausible change before scoring, not a vague
"if requirements change" hand-wave.

### SEAM PLACEMENT

> The deletion test, applied to pick a winner (full definition, including the
> pass-through tell, lives in `deep-modules.md`; this is the compressed
> version for scoring three candidates against each other).

Scoring question: mentally delete this module and inline its logic at every
call site. Does real complexity — branching, error handling, I/O, retries —
disappear from the codebase entirely (a real seam: the module earned its
boundary), or does the code read almost identically minus one layer of
indirection (a pass-through: the interface exists but isn't hiding anything)?

## Comparison-table template

Use this shape (a table if the answers are short, three short paragraphs per
candidate if they need room to breathe):

| Candidate | Depth | Locality | Seam placement | Verdict |
|---|---|---|---|---|
| A — <one-line shape> | <short answer> | <short answer> | <short answer> | keep / reject: <why> |
| B — <one-line shape> | <short answer> | <short answer> | <short answer> | keep / reject: <why> |
| C — <one-line shape> | <short answer> | <short answer> | <short answer> | keep / reject: <why> |

Close with the winner and the one-paragraph rationale SKILL.md Step 2 asks
for — it must cite the specific depth/locality/seam answers that decided it,
not a vibe.

## Worked example 1 — a rate limiter, varying state location and call shape

Three candidates for "limit an operation to N calls per window," generated
using generator prompts 1 (state location) and 2 (call shape) from SKILL.md
Step 1:

- **A — synchronous check-and-increment call.** `allow(key) -> bool`. State
  lives inside the module (an in-process counter map). Caller calls `allow()`
  before doing the work and branches on the result itself.
- **B — async event-stream consumer.** The module subscribes to an event
  stream of attempted calls and emits a `throttled` event when a key exceeds
  its window; callers never call anything synchronously, they react to the
  event.
- **C — declarative policy object evaluated by a shared engine.** Callers
  register a `RateLimitPolicy { key, limit, window }` with a shared
  evaluation engine; the engine — not the caller, not the policy object —
  owns state and enforcement, and callers query "would this be allowed?"
  through the engine.

| Candidate | Depth | Locality | Seam placement | Verdict |
|---|---|---|---|---|
| A | Shallow-ish: caller must call `allow()` *and* separately handle the branch — the interface exposes the check but the enforcement decision leaks to every call site. | Poor: every call site must remember to call `allow()` before the guarded work, and re-implement the same branch. A new guarded operation means re-deriving that pattern again. | Real seam if the counter storage (in-memory vs. distributed cache) is genuinely swappable; a pass-through if it's hardcoded to one backend nobody will ever change. | Reject — locality is the deciding weakness: the caller-held invariant ("call allow() first") is exactly the kind of cost this axis exists to catch. |
| B | Deep: callers do nothing but react; all throttling logic — windowing, counting, eviction — is fully hidden. | Good for new consumers (nothing to remember), but changing *which operations* are rate-limited means touching the event-emission call sites, which is a real but bounded cost. | Real seam: the event bus is a genuine external boundary already used elsewhere in most codebases, and a second implementation (a different broker) is easy to name. | Strong candidate, but only if an event bus already exists in this codebase — introducing one solely for this is a locality cost the table doesn't show. |
| C | Deep: caller-visible surface is one `RateLimitPolicy` value object; the engine hides evaluation, storage, and eviction entirely. | Best: a new guarded operation is a new policy registration, not new call-site logic; policy changes (raise the limit) touch one declaration, not every call site. | Real seam: "a shared engine evaluated by declarative policy" is exactly the kind of boundary a second implementation (a different engine, a test fake that always allows) is trivial to name for. | **Winner** — deep, best locality, and the seam passes the two-adapter check cleanly. |

Rationale (Step 2 shape): *C wins on locality (new guarded operations require
no new call-site logic, unlike A) and depth (callers hold no invariant, unlike
A's "call allow() first"), and its seam passes the two-adapter check (a
different engine or a test fake are both easy to name) where A's seam is
contingent on backend swappability that may not be real. B is a strong
second — reject it only if this codebase has no existing event bus, since
introducing one solely for rate limiting would cost more locality than the
table shows.*

## Worked example 2 — a config loader, varying surface size

Three candidates for "read application configuration," generated using
generator prompt 3 (surface size) from SKILL.md Step 1:

- **A — one fat interface exposing every step.** `ConfigLoader` with
  `loadFile()`, `mergeEnv()`, `applyDefaults()`, `validate()`, `freeze()` all
  public; callers call them in the right order themselves.
- **B — one thin single-entry facade.** `loadConfig() -> Config`. Internally
  does file-load, env-merge, defaults, validation, freeze — none of it is
  callable independently.
- **C — a composable pipeline of small pieces.** Small, independently usable
  functions (`readFile`, `mergeEnv`, `withDefaults`, `validate`) that a
  caller composes explicitly, plus one pre-built `loadConfig()` pipeline for
  the common case.

| Candidate | Depth | Locality | Seam placement | Verdict |
|---|---|---|---|---|
| A | Shallow: five public steps, and the caller must call them in the right order — footprint is nearly 1:1 with what it does. | Poor: every caller re-derives "file, then env, then defaults, then validate, then freeze" — a caller-held invariant, and a change to that order touches every call site that got it right by convention. | Ambiguous — depends whether any caller genuinely needs the steps separately; if not, this is five seams where one would do. | Reject — depth and locality both fail for the same reason: the surface is too fat for what's actually needed. |
| B | Deep: one call, zero caller-visible steps, all five internal decisions hidden. | Best for the common case: one call site, no invariant to hold. But if a caller genuinely needs to skip file-load (e.g. tests that inject config directly), there's no seam to attach to — locality cost shows up as a workaround elsewhere. | Real seam at the one entry point if there's a genuine second implementation (e.g. a test fake that returns fixed config); no internal seams to evaluate since nothing internal is exposed. | Good default, but only if no real caller needs partial composition. |
| C | Deep for the common path (`loadConfig()` is a one-liner), but the composable pieces reintroduce A's footprint for callers who need them — depth is per-caller, not uniform. | Best overall: the common case gets B's locality, and the rare caller that needs partial composition (tests, tooling) gets a real seam to attach to instead of a workaround. | Each piece is a real seam only if a second implementation is nameable for it (e.g. `mergeEnv` swapped for a test double that returns fixed vars) — apply the two-adapter check per piece, not to the pipeline as a whole. | **Winner** — matches B's locality for the common case without discarding a real need for partial use; the one thing to watch is not exposing a piece that fails its own two-adapter check. |

Rationale (Step 2 shape): *C wins because it gets B's depth and locality for
the common case (`loadConfig()`) while giving the one caller that genuinely
needs partial composition (config-injecting tests) a real seam instead of a
workaround — A's full step-by-step surface loses on both depth and locality
for no corresponding benefit once C's common-case entry point exists.*

## Optional: parallel generation

If a subagent-spawning tool is available, Step 1's three candidates MAY be
dispatched to three separate agents in parallel, each given the same problem
statement and told not to see the others' output, for genuine independence —
this mirrors orchestrate's fan-out habit but stops there: there is no
harvest step, no verifier, no reconciliation, because these are competing
designs the same agent will score in Step 2, not claims to fact-check. On any
harness without a subagent-spawning tool, generate all three yourself,
sequentially — this is the default, portable path, not a fallback.
