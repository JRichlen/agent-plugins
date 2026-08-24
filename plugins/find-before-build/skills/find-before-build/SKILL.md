---
name: find-before-build
description: >-
  Search for the existing implementation before writing a new one: name the
  searches you ran for an existing helper, abstraction, or pattern and what
  they returned, before introducing anything new. Use before adding a
  utility, wrapper, config knob, or dependency to a codebase you did not
  write end-to-end.
license: MIT
compatibility: >-
  PORTABILITY: pure search-then-cite discipline — no hooks, no
  subagent-spawning tool, no Workflow tool, no harness-specific primitive.
  The searches are whatever the harness already offers (grep, glob, code
  search); the receipt is prose. Ports to any harness that can search a
  codebase and report what it found.
---

# find-before-build

## Invariant

A new abstraction (helper, wrapper, utility, dependency) is ALWAYS preceded
by named searches for an existing equivalent with their results shown — and
NEVER introduced when an existing equivalent was found and usable.

## Not this

- **codebase-design** (`plugins/codebase-design`) governs how to design a
  new interface *well* once one is warranted — candidates, depth, seam
  placement. find-before-build is the gate *before* that: whether a new
  interface should exist at all. Run this first; only a search that comes
  back empty (or unusable) hands off to codebase-design.

- **verify-before-claim** (`plugins/verify-before-claim`) is the general
  claims discipline. The search receipt here is one specific claim shape —
  "no existing equivalent exists" — made checkable the same way: by
  attaching the literal evidence. This skill exists because that particular
  claim is usually never *stated*, so it's never checked; find-before-build
  forces it into the open.

## When to use this

The moment you're about to introduce something new to a codebase you didn't
write end-to-end: a helper function, a formatting/parsing/retry utility, a
wrapper around an API, a config option, a test fixture, a dependency in the
manifest. Trigger phrases: "add a helper", "write a util", "we need a
wrapper", "add a package", and — most importantly — your own impulse to
start typing a function you haven't looked for.

## The gate

1. **Name what you're about to build**, in one line, in the codebase's own
   vocabulary — the thing's purpose, not your working title for it
   ("retries an HTTP call with backoff", not "myFetchHelper").

2. **Run at least two searches from different angles** before writing it:
   by likely name (grep for `retry`, `backoff`), by mechanism (call sites
   of the API being wrapped, imports of a likely module), by convention
   (the project's `utils/`, `lib/`, `helpers/` layout, the dependency
   manifest for an already-installed package that does this). One search
   that comes back empty is not looking; it's one guessed keyword failing.

3. **Show the receipt.** Before the new code, state the searches verbatim
   and what each returned: *"Searched `rg 'backoff|retry' src/` — 3 hits,
   all test mocks; checked `package.json` — no retry package installed."*
   The receipt appears wherever the work is reported (the PR description,
   the summary, the commit body).

4. **Decide by the receipt.** Found and usable → use it, extend it, or fix
   it in place; do not write the parallel version. Found but genuinely
   unusable → say why (wrong layer, deprecated, semantics differ) — that
   sentence is part of the receipt. Nothing found → build, and hand the
   design to codebase-design if it meets that skill's bar.

"Usable" means it does the job with at-most-local changes. Preference,
style, or not-invented-here is not unusability — if the existing one is
ugly but correct, use it and record the cleanup wish as a finding, not a
rewrite.

## Failure modes this exists to stop

- The codebase's fourth date-formatting helper, three directories from the
  first.
- A new dependency added while an installed one already covers the need.
- One token grep coming back empty and standing in for a real search.
- "Found it, but mine is cleaner" — a parallel implementation shipped next
  to a working existing one.
