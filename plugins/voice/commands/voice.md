---
description: Show the voice routing rule — which of human-voice, machine-voice, or second-opinion governs what you are about to write.
argument-hint: "[element you're about to write, e.g. 'a status line' or 'a recommendation']"
---

Decide which voice governs the element described in `$ARGUMENTS` (if empty,
explain the routing rule itself), then read that skill and follow it.

Routing is **per output element, not per response**:

- Agent trace, tool-call log, status line, progress update, handoff note, state
  dump, config, schema, reference card, or structured data another agent parses
  → read `skills/machine-voice/SKILL.md`.
- Any other prose a human reads → read `skills/human-voice/SKILL.md`.
- Validating a verdict, and only after the user accepted an offer to do so →
  read `skills/second-opinion/SKILL.md`.
- Code and file contents, commit messages, creative or persona writing, and
  turns that are only a clarifying question or only tool calls → none of them
  apply; ship it unstyled.

`skills/ai-writing-mistakes/SKILL.md` is not part of this choice. It is a
wording pass that runs after the voice is picked, over anything human-voice
governs and over prose you were asked to author into a file. It never claims an
element of its own.

State which voice applies and why in one line, then apply it.
