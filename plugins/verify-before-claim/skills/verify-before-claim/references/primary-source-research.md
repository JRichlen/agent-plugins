# Primary source research

Loads when: the claim cites an external source, or the task is "research X" /
"find out whether Y" and produce findings.

## Cite the source that owns the claim, not an account of it

A blog post's summary of a paper is not the paper. A changelog entry someone
quoted in a forum thread is not the changelog. The distance between a claim
and its primary source is exactly the distance error can hide in.

- **For every cited claim, follow the link back to the primary source** — the
  actual paper, changelog, spec, commit, or primary doc. Stop only once you
  are reading the thing that owns the claim, not a description of it.
- If a source cannot be reached (paywalled, dead link, no access), that is
  itself a fact to report: "claim attributed to X, primary source not
  reachable" — not silently upgraded to a confirmed citation because a
  secondary account of it exists.

## Delegated research must not launder a summary as a source

PORTABILITY: "subagent" below names Claude-Code's fan-out primitive as one
concrete example; on a harness without it, "delegated" means any background
process, worker, or second call — the requirement to fetch and quote the
primary source directly is harness-agnostic.

- **If research is delegated to a background or subagent, that agent must
  fetch and quote the primary source directly.** A second-hand summary from
  another agent's output does not satisfy this — it just moves the
  secondary-source problem one hop further from view, and it looks identical
  to a real citation to whoever reads the final report.
- When merging findings from multiple research threads, check that each
  citation still traces to a primary source after the merge — a merge step
  that drops the URL and keeps only the paraphrase has quietly converted a
  primary citation into a secondary one.

## Leave a locatable trail

- **Leave behind a cited Markdown file**: each claim paired with the URL or
  path it came from. Prose citations with no locatable reference ("studies
  show...", "the docs say...") are not verifiable by the reader and do not
  satisfy this — a claim without a locatable source is functionally
  unverified even if it happens to be true.
