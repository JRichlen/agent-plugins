# Portable context extraction

Loads only when [`SKILL.md`](../SKILL.md)'s decision tree resolves to
**HANDOFF** (branch 3). This file is the exact shape and the deterministic
checks for that one branch.

## The rule

Anything that crosses the handoff boundary and is already SETTLED — specs,
plans, ADRs, issues, commits, diffs — must ALWAYS be referenced by path
(repo-relative or absolute) or URL (a GitHub PR/issue/commit link), NEVER
copied or quoted inline into the handoff artifact. The receiving session
reads the live source, not a copy that can drift from it the moment the
source changes again.

## The handoff artifact carries exactly two things

1. **The live thread** — what's in flight, why, and what's next. This is
   synthesized state and reasoning in your own words, not a raw transcript
   dump.
2. **A suggested-skills section** — which skills/plugins the receiving
   session should load to continue correctly (e.g. "load context-handoff
   itself on arrival," "load `semver-gate` before touching CI config").

Nothing else belongs in the file. In particular, it never carries a
narrative summary of settled content (that's dev-diary's job, for a
different reader on a different timescale) and it never re-derives or
re-explains a spec/plan/ADR/issue/commit/diff that already exists somewhere
resolvable — it points at it.

## "Does the receiving session need this raw?" — the drift-check heuristic

Before writing any block of quoted content into the handoff file, ask: "If I
regenerated this handoff from scratch right now, would the referenced
content be identical to what I'm about to quote, or could it have moved on?"

- If the source could plausibly change (a spec still being edited, a plan
  still being iterated, an open PR still getting review comments) →
  reference it, don't quote it. A quote taken today is a lie tomorrow.
- If drift is even *possible*, treat it as certain for the purpose of this
  check — the cost of a stale quote (the receiver silently acts on outdated
  information) is much higher than the cost of one extra path lookup.

## The resolvability check

For every artifact referenced in the handoff file, ask: can the receiving
session open it from the reference alone?

- A path reference only resolves if the receiver is in the same
  directory/repo/worktree as the writer. If the receiver is in a different
  harness, a different clone, or a different machine, a bare local path is
  useless to them.
- If the reference is to a local, uncommitted file and the receiver will be
  elsewhere, **commit or push it first** — the handoff file may not be
  written until every reference in it resolves for the receiver, not just
  for the writer. An unresolvable reference is worse than no reference: it
  looks like a pointer but silently dead-ends.
- Prefer URLs (GitHub PR/issue/commit links) over local paths whenever the
  receiving session's location is not guaranteed to match the writer's —
  a URL resolves from anywhere; a local path only resolves from the same
  tree.

## The size check — the deterministic, eval-able rule

A handoff file must not contain a block of more than ~3–4 lines of prose
lifted from any single external artifact under a heading like `Spec:`,
`Plan:`, `ADR:`, `Issue:`, `Commit:`, or `Diff:` — replace any such block
with a path or URL plus a one-line pointer to the relevant section or line
range.

This is the exact shape a cheap/deterministic eval can check for: flag any
handoff-shaped file that has one of those six headings followed by more than
~4 lines of prose with no path-like token or URL anywhere in that block. This
plugin ships that checker at
[`../../../scripts/check-handoff-portability.py`](../../../scripts/check-handoff-portability.py)
— run it against a candidate handoff file before sending it:

```
python3 plugins/context-handoff/scripts/check-handoff-portability.py path/to/handoff.md
```

Exit 0 means every `Spec:`/`Plan:`/`ADR:`/`Issue:`/`Commit:`/`Diff:` block in
the file is either short (≤4 lines) or carries an adjacent path/URL. Exit 1
prints the offending heading and line number.

## Recursive rule: research.md is referenced too, never re-embedded

If `research.md` exists for this work (see
[`research-documenter.md`](research-documenter.md)), the handoff file
references it by path — it never re-embeds its contents. This is the exact
same pointer-only rule applied recursively to context-handoff's own other
reference artifact: `research.md` is itself a settled artifact the moment
it's written, so it gets the same treatment as a spec or an ADR.
