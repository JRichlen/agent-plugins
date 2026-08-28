---
name: ai-writing-mistakes
description: >-
  Catch and repair the tells that mark prose as machine-written — the
  negation-flip ("it's not X, it's Y"), rule-of-three padding, hedge stacking,
  unearned intensifiers, filler verbs like delve and leverage, participle
  trailers ("...ensuring seamless integration"), sycophantic openers, empty
  closing summaries, and uniform em-dash/sentence rhythm. Use when drafting or
  revising any prose a human will read, including documents you were asked to
  author — READMEs, docs, PR bodies, release notes, emails — and when the user
  asks whether something "sounds like AI" or wants writing tightened. This is a
  wording pass, not a voice: human-voice still decides layout and confidence
  tags, machine-voice still owns traces and logs, and neither this skill nor
  those two touch code, commit messages, or quoted text.
license: MIT
compatibility: >-
  PORTABILITY: fully harness-agnostic. Every rule here is prose discipline and
  ports to any coding agent. Nothing in it requires a tool, a hook, or a
  subagent; the plugin's optional session-start injection is a convenience this
  skill does not depend on.
---

# AI Writing Mistakes

The tells that make prose read as machine-written, and what each one is
covering for.

## Invariant

**ALWAYS** fix a tell by restoring what it displaced — the specific claim, the
real subject, the actual cause. **NEVER** swap a flagged word for a synonym and
call it fixed, and **NEVER** rewrite prose you were asked only to review.

## Not a fourth voice

This is a **pass, not a voice**. It never claims an output element and never
competes with the routing rule: `human-voice` decides layout, ordering, and
confidence tags; `machine-voice` owns traces, logs, status lines, and schemas.
This skill only changes **wording inside prose those rules already placed**.

Where it runs:

- Every element `human-voice` governs.
- Prose you were asked to **author into a file** — README, docs, PR body,
  release notes, email, changelog entry. Those ship unstyled by the routing
  rule, which exempts them from *layout*, not from being written well.

Where it does not run: code and identifiers, `machine-voice` artifacts
(compression is the point there), creative or persona writing where the user
asked for a voice, and any text you are quoting.

**Never alter quoted text, cited titles, error strings, or the user's own
words.** A tell inside a quotation is evidence, not a defect.

## Substitution is not a fix

Every tell is a symptom. The disease is a **missing commitment** — a claim the
sentence would have to support, a subject it would have to name, a cause it
would have to establish. Filler is what the sentence does instead.

So the repair is not a thesaurus:

| Draft | Substitution (still broken) | Fix |
|---|---|---|
| "This leverages caching to significantly improve performance." | "This uses caching to significantly improve performance." | "Caching cuts the p95 from 400 ms to 90 ms." |
| "It's not just a linter — it's a safety net." | "It's more than a linter; it's a safety net." | "The linter fails the build on unhandled promise rejections." |
| "This may potentially help reduce flakiness." | "This could help reduce flakiness." | "This removes the sleep-based wait, which caused 6 of last week's 9 flakes. ⚠️ the other 3 are unexplained." |

If you cannot supply the commitment, **cut the sentence**. A shorter paragraph
that says less is not a regression; a padded one that says the same amount is.

## Frequency is the tell, not the token

No word and no punctuation mark is banned. The em dash, "delve", and the rule of
three are all legitimate — what marks machine prose is **using them at uniform
rate, everywhere, regardless of what the sentence is doing**.

Two numeric rules, so this is checkable rather than a matter of taste:

- **At most one em dash per paragraph.** A second one in the same paragraph
  becomes a comma, a colon, or a full stop. Three things this counts, because
  measuring it exposed all three: the unit is one prose paragraph or one list
  item, so a list of six dashed bullets is six units and not a violation; a
  matched **pair** setting off a single parenthetical — like this one — is one
  use, not two; and YAML frontmatter, tables, and code are not prose and are
  not counted.
- **At most one hedge per claim.** "may potentially", "could possibly",
  "generally tends to" carry one hedge's meaning at three hedges' cost. Where
  the uncertainty is real, `human-voice`'s `⚠️` or `❓` tag says it once.

Two judgement rules, applied per instance:

- **An intensifier needs a number behind it.** "significantly", "vastly",
  "dramatically", "remarkably" without a figure are decoration — supply the
  figure or drop the word.
- **A specialist writing to a peer** would use domain terms plainly. "Leverage"
  in a finance document and "delve" in a paper title are not tells.

## The catalogue

The twelve that account for most of it. Full list with worked before/after
examples: `references/tells.md` — read it when doing a dedicated cleanup pass
rather than an inline check.

| Tell | What it covers for | Fix |
|---|---|---|
| **Negation flip** — "It's not X, it's Y" / "This isn't just X — it's Y" | No comparison was actually made; X is a straw man | Assert Y directly, with what makes it true |
| **Rule-of-three padding** — "fast, reliable, and scalable" | Two of the three are unsupported | Keep only the ones you can back |
| **Participle trailer** — "..., ensuring seamless integration" | A consequence nobody verified | Cut it, or make it its own sentence with evidence |
| **Hedge stack** — "may potentially help" | Unquantified uncertainty | One hedge, or a `⚠️`/`❓` tag |
| **Unearned intensifier** — "significantly faster" | A missing measurement | The number, or nothing |
| **Filler verb** — delve, leverage, harness, unlock, foster, embark, showcase | A plain verb felt too plain | The plain verb |
| **Abstraction nouns** — landscape, realm, ecosystem, tapestry, testament, beacon | No concrete subject | Name the thing |
| **Unearned quality adjectives** — robust, seamless, comprehensive, cutting-edge, game-changing | Praise instead of a property | The property, or nothing |
| **Sycophantic opener** — "Great question!" / "You're right to be concerned" | Warmth in place of an answer | Delete; start at the answer |
| **Question restatement** — "You're asking about X" | Filling the verdict slot | Delete; `human-voice` wants the verdict there |
| **Empty closer** — "In summary, X is a powerful tool for Y" | Nothing left to say | Delete, or replace with a scoped depth offer |
| **Audience spanner** — "Whether you're a beginner or an expert..." | No specific reader | Address the reader you actually have |

Two structural ones no word list catches:

- **Uniform rhythm.** Every sentence 15–25 words, every paragraph three
  sentences, every section the same length. Vary it: a four-word sentence
  after a long one is the strongest emphasis available, and it costs nothing.
- **Bulletization.** Prose chopped into bullets that are each a full paragraph.
  A list is for parallel items; if the bullets have to be read in order to make
  sense, it was a paragraph.

## Reviewing someone else's prose

**Review means name and stop.** When the user asks whether something reads as
AI-written, or asks for a critique, the deliverable is the diagnosis: quote the
line, name the tell, offer the rewrite. Do not hand back a rewritten document
they did not ask for.

Rewrite only when the user asked for a rewrite, an edit, or a cleanup. When they
did, **never claim a pass you did not make**: say what you changed, or say
plainly that you found nothing worth changing. A "cleaned up" label over an
unchanged draft is the failure this rule exists to prevent — the user cannot
tell it from real work, which is exactly what makes it worse than saying no.

## Self-check before emitting

- Does every intensifier and quality adjective have a number or a property
  behind it?
- More than one em dash in any paragraph? More than one hedge on any claim?
- Any sentence whose deletion would cost the reader nothing? Delete it.
- Did any fix replace a word without adding a commitment? That one is not fixed.
- Was this a review request? Then is the output a diagnosis rather than a
  rewrite?
