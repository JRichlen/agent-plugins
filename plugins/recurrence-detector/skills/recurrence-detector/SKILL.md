---
name: recurrence-detector
description: >-
  Close the growth loop's DETECT step: read the exhaust every run already
  sheds — stop-reports, scope-fence findings, unmet criteria, diary entries —
  cluster it by failure shape, and surface any shape seen at least N times as
  a named candidate invariant with its sightings cited. Proposes; never
  scaffolds. Use when asking what keeps going wrong, or before adding a skill
  on a hunch.
license: MIT
compatibility: >-
  PORTABILITY: pure reading-and-clustering discipline over files the repo
  already holds — no hooks, no subagent-spawning tool, no harness-specific
  primitive. Runs anywhere a shell can grep a directory of notes.
---

# recurrence-detector

## Invariant

A failure shape is surfaced as a candidate invariant ONLY when it was seen at
least N times across consolidated exhaust and every sighting is cited by
source and date — and a candidate is NEVER auto-scaffolded into a skill: the
output is a proposal a human and `plugin-factory` dispose of.

## Why this exists

A system that learns needs a step between *remembering* and *building*.
`dev-diary` and `fleet-playbook-curator` remember; `plugin-factory` builds.
Nothing reads a month of exhaust and says **"this failure shape has appeared
four times — here is the invariant that would prevent it."** Until that
exists, the human is the detector: a fine bootstrap and a real bottleneck.

## The threshold, and why it is not 1

Default **N = 3**. One occurrence is an incident; two is a coincidence; three
is a shape. Below the threshold a candidate is *listed as watched*, never
promoted — a skill built from a single bad day is the system memorizing noise,
and the behavioral tier will reject it anyway for failing to beat its
calibration stub. The threshold is the cheap filter that saves the expensive
one.

## The loop

1. **Gather** the exhaust: `stop-rule` reports, `scope-fence` findings and
   `BACKLOG.md`, unmet criteria and `gates.log` from `.redgate/*/`, diary
   entries, and any typed deltas (see the `consolidate-delta` references in
   `dev-diary` and `fleet-playbook-curator` — deltas are what make this
   greppable rather than a re-read of prose).
2. **Cluster by failure shape, not by surface.** "The test was flaky" and
   "the check passed for the wrong reason" are the same shape — an
   uncoupled verifier — wearing different words. Name the shape as a
   mechanism, not as a symptom.
3. **Count and cite.** Each cluster carries every sighting: source file,
   date, and one quoted line. A cluster whose sightings cannot be cited is
   not a cluster; it is a memory.
4. **Draft the invariant.** State it as ALWAYS/NEVER, testable by a
   deterministic check — the same bar `plugin-factory` will hold it to.
5. **Propose. Stop there.** Output is a ranked list of candidates, each with
   its shape, count, citations, drafted invariant, and the cheapest check
   that would defend it. **Never scaffold, never edit a skill, never open a
   PR.** The human picks; `plugin-factory` scaffolds red-by-default; the eval
   tiers decide whether it earned its slot.

## What disqualifies a candidate

- **Fewer than N sightings**, or sightings that cannot be cited.
- **Already covered** by a shipped skill — check before proposing; a rename
  of an existing invariant is noise (`find-before-build`'s discipline,
  applied to skills rather than code).
- **Not stateable as ALWAYS/NEVER** — a preference is not an invariant.
- **No cheap deterministic check** could defend it. If only a judge can tell,
  it needs the negative-control contract in `plugin-factory`'s
  `references/judge-calibration.md` before it is worth proposing.

## Not this

- **`dev-diary`** records what happened on a day; this reads across many days
  and asks what *keeps* happening.
- **`docs-hygiene`** audits whether documented claims are still true; this
  asks whether an undocumented rule should exist at all.
- **`plugin-factory`** builds the skill; this only nominates it. The
  separation is the point: DETECT proposes, the human and the factory dispose.
