# Uncertainty flagging

Loads when: the claim is headed into a handoff doc, questionnaire response, or
any deliverable someone else will act on without re-checking it.

## Write a flag that survives to the reader

A deliverable that someone else acts on unchecked is where an unflagged
assumption does the most damage — the reader has no way to tell a checked
claim from a hopeful one unless the document tells them.

- **Classify every claim in the deliverable inline**: `VERIFIED` (the check
  ran, its output is shown or linked) or `UNVERIFIED` / `ASSUMED` (state
  exactly what was assumed and why it wasn't checked — out of scope, no
  access, time-boxed).
- **The flag stays adjacent to the claim everywhere the claim recurs** — in a
  summary line, in a table row, in a "next steps" section — not just at first
  mention. A claim that starts flagged and ends unflagged three paragraphs
  later has been silently smoothed into fact, which is the exact failure this
  file exists to prevent.
- A flagged uncertainty is a valid, useful deliverable output **on its own**.
  It is not a defect to be minimized, hedged into disappearing, or apologized
  for — "I could not verify X because Y" is a complete and correct line, not
  an admission that the deliverable is unfinished.

## Where this bites in practice

- A summary table that drops the VERIFIED/ASSUMED column from its final row.
- A "Findings" section that states a claim plainly, with the caveat living
  only in an appendix the reader may never open.
- A status report where "assumed passing" in the detail section becomes
  "passing" in the executive summary at the top of the same document.

Each of these is the same failure in a different shape: the flag existed once,
and did not travel with the claim.
