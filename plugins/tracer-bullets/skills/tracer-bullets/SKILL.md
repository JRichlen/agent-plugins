---
name: tracer-bullets
description: >-
  Ship the thinnest possible end-to-end slice through a system (or a question)
  first, get it working for real, then widen it in place. Applies to software
  delivery (a skeleton request that really hits every layer: UI to DB to
  response) and to open-ended investigation/research (a skeleton pass that
  really touches every source: shallow-fetch every branch before deep-diving
  any one). Use when scoping new work, de-risking an unfamiliar problem before
  committing to a full build, or planning how to structure a multi-stage
  investigation — especially before reaching for a throwaway prototype/spike,
  since the two are easy to conflate and this skill exists to keep them apart.
---

# tracer-bullets

## Invariant

A tracer bullet is a real, end-to-end, kept-and-built-upon slice through every
layer of the system (or claim) — it must ALWAYS touch every layer for real, and
it must NEVER be thrown away like a prototype/spike; a prototype/spike answers a
question and gets discarded, a tracer bullet becomes the skeleton of the final
thing.

## Where this comes from

The term is Hunt & Thomas's, from *The Pragmatic Programmer* (the tracer-round
metaphor: a tracer round is a live round, on the same trajectory as the rest of
the belt, that happens to glow so you can see where your fire is landing — it is
not a different, disposable round fired just to check your aim). Matt Pocock's
worked write-up (aihero.dev, "How I Use Tracer Bullets To Ship Fast As A Senior
Engineer") is the applied, AI-era restatement this skill leans on for the
software-delivery half: get one thin thread lit up end-to-end before fanning out
into breadth or depth.

## When to use this

- Scoping new software work where the layers (UI, API, data, whatever the stack
  is) are individually familiar but the *integration* between them is the real
  unknown.
- Planning a multi-stage investigation or research task where the source
  material is large, branching, or unfamiliar, and going deep on the first
  promising branch risks missing a better one.
- Any time a plan is about to jump straight to full-width breadth-first
  exploration *or* full-depth single-thread investigation before either has been
  cheaply validated — a tracer bullet is the cheap validation step for both.
- Any time "let's build a quick prototype to see if this works" is on the table
  — stop and ask whether the thing under discussion is disposable (prototype) or
  destined to be kept (tracer bullet); see `## Tracer bullets vs. prototypes and
  spikes` below before proceeding either way.

## How it works

1. **Pick the thinnest real slice.** Identify the smallest path that touches
   every layer (or every source/branch) for real — not a mock of the hardest
   layer, not a stub of the deepest source. "Thin" means low effort per layer,
   not fake layers.
2. **Make it work end-to-end, even if narrow.** The slice must actually run /
   actually surface a finding, not just typecheck or look plausible. A tracer
   bullet that doesn't fire tells you nothing.
3. **Treat it as the skeleton, not scrap.** The code (or findings structure) from
   this pass is not deleted once it has proven the path — it is the frame later
   work widens. This is the property most often gotten wrong; see the contrast
   section below.
4. **Widen from what you learned.** Use the now-proven path to decide where
   breadth (more layers/sources at the same shallow depth) or depth (more detail
   on one already-touched layer/source) pays off next. The tracer round showed
   you where your fire is landing — adjust aim, don't refire blind.
5. **Repeat at the new width/depth if the terrain is still unfamiliar.** A
   tracer-bullet pass can itself be layered: fire a thin round, see where it
   lands, fire the next thin round informed by that. Stop layering once the
   remaining risk is "more of the same," not "will this even connect."

## Use case: software delivery

The classic case. Instead of building the database schema fully, then the API
fully, then the UI fully (each one a leap of faith about what the others will
need), build the *thinnest possible path* through all three: one field, one
endpoint, one screen, wired for real and deployed/runnable end-to-end. That slice
is scrappy but real — and it stays in the codebase. Every subsequent feature
widens it (more fields, more endpoints, more screens) rather than replacing it,
because the integration risk (the part that was actually uncertain — do these
layers talk to each other correctly) was retired on the first pass, for keeps.

## Use case: investigation / research

The same shape applies once "layers of a system" is generalized to "branches of
an unknown space." Instead of picking the first promising source and reading it
exhaustively (deep-first — risks tunneling into a source that turns out low-value
while better ones go untouched), or trying to catalogue every possible source
before reading any of them closely (breadth-only — risks never converging, and
produces a list instead of an understanding), a tracer-bullet investigation does
a **thin, real pass across the whole space first**, then widens into the branches
that pass proved out.

**This very workflow is a worked example of that structure.** The task that
produced this skill was: recursively traverse aihero.dev via its llms.txt index
using cheap (haiku) fan-outs, surface skill-worthy concepts, prioritize them, and
— as one deliverable among several — ship this real plugin from what was found.
The shape used to do that *was* tracer bullets, layered:

- **Tracer round 1 (index-wide, shallow):** fan out cheap agents across the
  *entire* llms.txt link index first — one lightweight pass per branch (each
  post, each catalogue page) rather than deep-reading any single post
  immediately. This is the "thinnest slice that actually touches every layer"
  move: every branch got a real, if narrow, look before any branch got a deep
  one.
- **What that round was for:** it is a real pass, not a disposable one — the
  findings from round 1 (which pages exist, what each is roughly about, which
  ones cluster around a reusable idea) are the skeleton the rest of the
  investigation is built on, not scratch work thrown away once the shallow read
  was done.
- **Widen from what it found:** the shallow pass surfaced that `/tracer-bullets`
  and the `/skills` catalogue were dense with reusable, skill-shaped material
  (among other candidates already covered by sibling plugins) — that's the
  signal that justified going deep on exactly those branches next, instead of
  spending the same depth budget uniformly or guessing up front which post
  mattered most.
- **Deep pass, bounded:** only *after* the shallow round identified
  `/tracer-bullets` as high-value did a focused pass read that post in full
  depth to extract the real procedure this SKILL.md encodes — depth spent where
  the tracer round showed it would pay off, not spent first.
- **Kept, not thrown away:** the shallow-pass findings (the prioritized concept
  list, the categorization) are a real deliverable handed back at the end, not
  scaffolding deleted once the deep pass started. That is what makes the whole
  thing tracer bullets rather than a prototype: the first pass is load-bearing
  for the final answer, not a disposable check.

The generalization: **"widen a thin, real, whole-space pass" beats "go deep on
the first branch" or "catalogue everything before reading anything."** In an
orchestration with cheap (haiku) fan-out workers, this also happens to be the
cost-efficient shape — the expensive move (a deep read, a careful build) is
reserved for the branches a cheap shallow pass has already shown are worth it.

## Tracer bullets vs. prototypes and spikes

This is the property most likely to be gotten wrong, so state it explicitly and
defend it:

| | Tracer bullet | Prototype / spike |
|---|---|---|
| Purpose | Build the real thing, thin | Answer a question |
| Fidelity | Real, working, on the actual stack/sources | Fake, mocked, throwaway stack allowed |
| Fate | **Kept.** Becomes the skeleton later work widens | **Thrown away.** Deliberately deleted once it has answered the question |
| What "success" means | It runs end-to-end and stays in the system | It taught you something and can now be discarded without loss |
| Cost profile | Thin now, widened incrementally — total cost is spread out | Cheap and fast now, but its cost is sunk — none of it ships |

Concretely: if the plan says "throw this away once we know the answer," it is a
prototype or a spike, and that is a legitimate, different tool — sometimes the
right one, when the *only* need is an answer to a technical question with no
intent to keep the artifact (e.g. "can this library even do X" or "which of
these two approaches is faster," where the code that finds out is not meant to
survive). But do not call that a tracer bullet, and do not let a tracer bullet
quietly become a prototype by treating its output as disposable once the demo
works. The tell that a "tracer bullet" has drifted into prototype territory:
someone proposes rewriting the slice from scratch once it has proven the
concept, rather than widening it in place. If a rewrite-from-scratch is really
warranted, the thing that just got built was a prototype all along — rename it
as such rather than calling the rewrite a "tracer bullet cleanup."

The failure mode in the other direction — calling a prototype a tracer bullet —
matters too: it leads to shipping throwaway, mocked-out code as if it were
load-bearing skeleton, because the label implied it should be kept. Get the
label right before writing the first line.

## Keep it portable

The procedure above is prose and judgment, not a harness-specific mechanism —
it applies equally to a solo coding session, a multi-agent Workflow-tool
orchestration (as in the worked example above), or a plain research write-up.
Nothing here depends on any particular tool; the shallow-then-widen shape is the
reusable idea.
