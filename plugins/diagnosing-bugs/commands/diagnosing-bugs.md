---
description: >-
  Diagnose a bug by writing ranked, falsifiable hypotheses before any code
  change, tagging temporary debug instrumentation for a zero-tolerance sweep,
  and gating the regression test to a red-then-green proof at the confirmed
  seam. Use when fixing a bug, debugging a failure, triaging an error, or the
  user asks to diagnose/root-cause/troubleshoot an issue.
---

Invoke the `diagnosing-bugs` skill and follow `skills/diagnosing-bugs/SKILL.md`.

Use this when a bug is confirmed and the next step is finding out why, before
writing a fix. Walk the seven steps in order: confirm (or build) a tight,
deterministic feedback loop; write a ranked, falsifiable hypothesis list
before touching any code; test the top-ranked hypothesis; falsify or confirm
and move on, re-ranking as new evidence appears; minimize the confirmed repro
to its load-bearing seam; implement the fix and gate a regression test to
that seam with a red-on-pre-fix / green-on-post-fix check; then run the
`DBGRM:` instrumentation sweep and confirm it returns zero lines before
calling the fix done. Surface the ranked hypothesis list (with what was
falsified/confirmed and why) in the PR description, commit message, or chat
output so the reasoning is auditable afterward.
