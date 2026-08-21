# Pre-claim reproduction

Loads when: the claim concerns a bug report's reality, or a PR/merge's
readiness to build on.

## Reproduce before building on top of a claim

A bug report is a claim someone else made. Do not build a fix on top of it
until you have reproduced it yourself.

- Take the reporter's own steps-to-reproduce **verbatim**, not a paraphrased
  summary of them. A paraphrase drops the exact input, the exact version, the
  exact ordering — any of which can be the reason it does or doesn't
  reproduce.
- Execute those steps exactly, in the stated environment or branch where
  available. "Ran something similar" is not reproduction.
- **If it does not reproduce: say so explicitly and ask what's missing** —
  exact version, exact input, exact environment — rather than assuming the bug
  is real and building a fix on an unconfirmed report. A fix for a bug that
  doesn't reproduce is a fix for nothing, shipped with confidence.

## "Ready to build on" for a merge or PR

A claim that a merge or PR is "ready", "passing", or "clean" is a completion
claim, and it gets the same treatment as any other: name the check, run it,
show the output.

- Run the **full suite on the actual merge result** — the commit that will
  land — not just the source branch in isolation.
- A green source branch plus a green target branch does **not**, by itself,
  prove the merged combination is green. The merge itself can break things
  neither branch broke alone (conflicting assumptions, overlapping edits that
  textually merge but semantically diverge). Treat "both sides pass" as zero
  evidence about the merge until the merge itself has been run.
- If the full suite cannot be run against the actual merge result — no CI
  access, no time — say so explicitly next to the readiness claim: "not
  verified against the merged commit" — not silently assumed clean.
