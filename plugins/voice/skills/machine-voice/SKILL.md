---
name: machine-voice
description: >-
  Compression rules for standalone machine-read artifacts the reader scans —
  agent traces, tool-call logs, status lines, progress updates, handoff notes,
  state dumps, config, schemas, reference cards, and structured data another
  agent parses. Applies three layers: lexical compression, markdown structure as
  navigation, and emojis as typed status markers. Reach for it when emitting one
  of those artifacts on its own. Companion to human-voice, which governs prose a
  human reads and also owns any table or block that serves surrounding
  explanation. Neither skill applies to code or file contents the user will
  save, commit messages, creative writing, or turns that are only a clarifying
  question — those ship unstyled and uncompressed.
license: MIT
compatibility: >-
  PORTABILITY: fully harness-agnostic. The compression layers are prose
  discipline and port to any coding agent. The only Claude-Code-only part of
  this plugin is the optional session-start context injection, which is a
  convenience — this skill is complete and usable without it.
---

# Machine Voice

Compression for output whose next reader is scanning for information.

## Invariant

**ALWAYS** confirm the element matches the list below before compressing.
**NEVER** apply these layers to prose a human reads — that is `human-voice`'s.

## The list

This skill governs an output element when it is one of:

- Agent trace or tool-call log
- Status line, progress update, handoff note
- State dump, config, schema, reference card
- Structured data block another agent will parse

**These four bullets are the whole list.** Do not generalize it.
Not on the list → this skill does not apply; follow `human-voice` for that element.

The split is **per element, not per response**. A reply that explains something
in prose and embeds a trace uses `human-voice` for the explanation and this
skill for the trace.

`ai-writing-mistakes` does not run here. Its subject is filler in prose a human
reads; compression has already removed that surface, and its rewrites would
expand what this skill exists to shrink.

## Precedence — read before applying the list

The list above is not the last word. Two rules beat it, in this order.

**1. Out of scope beats the list.** These never get compressed, even when they
look exactly like a config or a schema:

> Code and file contents, commit messages, creative or persona writing, and
> turns that are only a clarifying question or only tool calls.

The contents of a real `.eslintrc`, a `SKILL.md` being written, or a JSON Schema
the user asked you to author are **file contents**. Ship them verbatim and
unstyled. Compressing a file the user will save corrupts it — Layer 1 rewrites
content, and content is the artifact here.

**2. Serving prose beats the list.** An element that exists to support
surrounding explanation belongs to `human-voice`, even if it matches a bullet. A
four-database comparison table inside a recommendation is the explanation's
evidence, not a standalone reference card, so it takes `human-voice`'s
confidence tags and never this skill's status glyphs.

**3. Otherwise**, a standalone artifact matching one of the four bullets is
this skill's.

Tiebreak within rule 3 only: would this element still be correct pasted into a
log file with no surrounding sentences, *and* is it something the reader scans
rather than saves? Both yes → this skill.

## The three layers

Applied together, only to a matching element.

1. **Lexical** — drop connective tissue, keep content words.
2. **Vertical** — markdown structure as navigation.
3. **Iconic** — emojis as typed markers, not decoration.

### Layer 1 — Lexical

Drop *discourse* overhead: transitions, hedges, preambles. Keep *grammatical*
disambiguators. Articles are cheap; misread commands are expensive.

- "Delete user file" — ambiguous (verb? modifier? object?)
- "Delete the user's file" — clear

> `Fetched 12 rows. Schema mismatch col 3. Retrying with cast.`

Four named patterns — block language, headlinese, asyndeton, nominal style —
with worked examples and their failure modes are in
`references/lexical-patterns.md`. Read it when you need the specific pattern;
the rule above is what governs.

**Avoid:** full telegraphic speech (parse-ambiguous), terseness past clarity,
and obscure abbreviations (`cfg` is fine, `cfgr` is not).

### Layer 2 — Vertical

Markdown does wayfinding. Vertical space is navigation, not decoration.

- **Headers** — only for independently meaningful sections. Under ~3 lines, use
  a bold lead-in instead.
- **Lists** — only for parallel items: same shape, same granularity. A one-line
  bullet beside a three-paragraph bullet means the list is wrong.
- **Tables** — token-expensive, attention-cheap. Use at ≥3 items × ≥2
  attributes where the point is comparison. Two-item comparisons are prose.
- **Code blocks** — structured data, copy-verbatim commands, anything where
  whitespace matters. Always tag the fence language.
- **Whitespace** — group related items, blank line between groups.
- **Emphasis** — bold the one phrase per paragraph that carries load. Universal
  bold is no bold.

### Layer 3 — Iconic

Emojis work as typed markers the eye matches faster than words, and fail as
decoration.

```
✅ Tests passed (42/42)
❌ Build failed: missing dep 'foo'
⚠️  Rate limit at 80%
🔄 Retrying in 3s
⏭️  Skipped (cached)
```

Rules: one per line maximum, at line start when it marks status or category,
never inside a prose paragraph, never a skin-tone variant. Prefer glyphs with
unambiguous semantics — `✅ ❌ ⚠️ 🔄 ⏭️ 📋 🔑 💡 🎯 🚧`. Region-dependent gestures
like `👍` read differently across cultures; use `✅` for done. Always pair the
glyph with text — screen readers announce them awkwardly.

**Vocabulary collision — read this.** `✅ ❌ ⚠️` here are *execution status*
markers: passed, failed, needs attention. They are **not** `human-voice`'s
confidence tags, which mark claim provenance (verified / inferred / unverified).
Never mix the two vocabularies in one output. If a response carries both a trace
and a tagged verdict, keep them in separate blocks so the reader can tell which
vocabulary is in play.

## Worked example

Before (287 tokens):

> I started by looking at the user's request, which was to find flights from SFO
> to JFK for next Tuesday. I then called the flight search API with these
> parameters. The API returned 42 results, but I noticed that 8 of them had a
> layover longer than 6 hours, which the user probably doesn't want. I filtered
> those out, leaving 34 options. I sorted them by price and took the top 5.

After (98 tokens):

```
🎯 Task: SFO→JFK, Tue
🔄 flight_search → 42 results
⚠️  Filtered 8 (layover >6h)
✅ 34 remain → sorted price → top 5
```

Same information, ~65% fewer tokens. Lexical dropped the scaffolding, vertical
replaced paragraph flow, iconic turned narrative beats into typed markers.

## Before emitting

Confirm the element matches one of the four listed types. If it does not,
discard what you drafted with these layers and rewrite it under `human-voice`.
