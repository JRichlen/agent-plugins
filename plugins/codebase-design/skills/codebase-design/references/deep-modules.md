# deep-modules: how do you judge a single interface once chosen

Loaded from SKILL.md Step 3 (seam confirmation) and Step 4 (final depth check
before handoff). This is the "how do you tell a deep module from a shallow
one" lens — four subsections that are one coherent judgment, not four
separable procedures: Module Depth Analysis (the dependency classification),
the deletion test (spot a pass-through), seam validation via the two-adapter
check (spot a premature abstraction), and Seam-Based Design & Test Agreement
(what earns a test double). They stay in one file because splitting them
would force a boundary that isn't earned — the same discipline this skill
asks of the interfaces it judges.

PORTABILITY: everything below is plain reasoning applied to a design you
already chose — no subagent-spawning tool, no harness-specific primitive
required.

## Module Depth Analysis

A deep module hides a lot of implementation complexity behind a small
interface. A shallow module's interface is roughly as complex as what it
does — the abstraction costs about as much to learn as the thing it's
abstracting, so it isn't paying for itself.

To judge whether the chosen design is deep, classify every dependency it
touches into exactly one of four categories. This classification also decides
what gets a test double later (SKILL.md Step 4 uses it directly):

1. **Pure/internal logic** — no I/O, deterministic given inputs. No mocking;
   test it directly with real inputs and real assertions on real outputs.
2. **Owned deep dependency** — another module in this same codebase that
   already has its own confirmed seam (it passed this same analysis) and its
   own tests. Call it for real. Re-mocking an owned deep dependency here
   duplicates an assumption you've already tested once, and hides
   integration bugs that only show up when the real thing is called.
3. **Unowned external boundary** — a third-party API, the network, the
   filesystem, the system clock, another team's service: anything outside
   your control that can fail or change independently of this codebase.
   This is where a test double belongs, and the *only* place one belongs.
4. **Config/environment surface** — values that vary by deploy, not by
   logic (a feature flag, a region, a timeout tuned per environment). Inject
   these as parameters; test by passing fixed values through the real code
   path, never by mocking a getter that reads them.

### The over-fragmented-shallow-module diagnostic

If a design's *only* reason for a given boundary is that a test needs to
swap out a category-1 (pure/internal) or category-2 (owned deep dependency)
piece — i.e., nothing in category 3 (a real unowned external boundary)
justifies the split — that boundary is a **testability-only interface**.
It exists to make internals swappable, not because two real
implementations will ever coexist. This is the invariant's "shallow
pass-through" failure mode in category-classification form: collapse the
boundary back into its caller, and push the test double out to the real
category-3 boundary that actually deserves one. A module whose sole adapter
is a mock built purely to satisfy this test has already failed the
two-adapter check below — the two diagnostics are meant to agree, and if
they don't, re-run both.

## The deletion test

A fast, standalone check for whether a single interface is a real seam or a
pass-through — the same test SKILL.md Step 2 applies across three
candidates, described here in full:

> Mentally delete the module. Inline everything it did, directly at each of
> its call sites.

Then look at what happened to the call sites:

- **Real seam** — the call sites got *messier*: branching, error handling,
  retries, or I/O logic that used to be hidden now sits exposed at every
  caller. The module was earning its boundary by keeping that mess in one
  place instead of N places. Restore the boundary.
- **Pass-through (the tell)** — the call sites read almost identically,
  minus one function call / one layer of indirection. Nothing got messier
  because the module wasn't hiding anything — it was relaying arguments to
  something else, or wrapping a single call in a same-shaped call. The
  interface exists, but it isn't a seam; it's ceremony.

The deletion test is deliberately mental, not literal — you are not
actually asked to delete the module. It is a five-second gut check you can
run on any interface, chosen or candidate, any time the question "is this
hiding anything?" comes up.

## Seam validation: one adapter vs two

A seam is a boundary in the code where one concrete implementation can be
swapped for another without the caller knowing. The question that separates
a real seam from a premature one:

> **The two-adapter check**: can you name a second concrete implementation
> this boundary would actually have to support? A fake for tests counts. A
> different backend counts. A v2 of the same protocol counts. Anything with
> a name and a plausible reason to exist counts.

- **Yes, a second implementation is nameable** → the seam is real. Keep the
  boundary; it is worth the interface it costs.
- **No — you can only imagine the one implementation that exists today** →
  the seam is hypothetical. Two moves are available, in order of
  preference:
  1. Find the *real* external boundary further out (often one or two layers
     away — the actual network call, the actual filesystem read, the actual
     third-party client) and move the seam there instead.
  2. If no real external boundary exists nearby, drop the abstraction
     entirely and let the code call the concrete thing directly. An
     interface that will only ever have one implementation is not a seam,
     it's a rename.

This is the check SKILL.md Step 3 applies to every named seam in the chosen
design, and the check the over-fragmentation diagnostic above cross-checks
against. When both checks agree a boundary is fake, that's strong signal —
collapse it.

## Seam-Based Design & Test Agreement

Seams should be named *before* code is written, not discovered by writing
tests against whatever happens to be mockable. Two rules fall out of this:

1. **Name seams in the spec, before the implementation.** SKILL.md Step 3
   asks for a short bullet list of confirmed seams as part of the design
   output — "this call boundary is a confirmed seam" — written down before
   any test or implementation exists to make the boundary look plausible in
   hindsight. A seam discovered by "well, this happens to be the thing I
   mocked" is exactly backwards.
2. **A test only earns its place if it exercises a confirmed seam.** The
   test/seam agreement this file is named for: tests double *at* seams that
   passed the two-adapter check (category-3 boundaries from Module Depth
   Analysis) and nowhere else. A test written against a boundary that never
   passed the two-adapter check — an unconfirmed seam — does not earn its
   place. It should be flagged as a smell (a mock introduced to make a
   shallow module *look* testable) rather than written, per SKILL.md Step 3.

The practical test for whether this agreement is holding: every mock or test
double in the chosen design's test suite should trace back to a seam that is
named in the design output *and* passes the two-adapter check. If a mock
exists that doesn't trace back to a named, confirmed seam, either the seam
was never named (fix the spec) or the mock shouldn't exist (fix the test).
