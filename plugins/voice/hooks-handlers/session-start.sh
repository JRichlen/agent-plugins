#!/usr/bin/env bash
#
# Emit the voice routing rule as additionalContext at session start.
#
# This is a CONVENIENCE, not a dependency. The three skills under skills/ are
# complete and usable on their own; this handler only makes the routing decision
# salient early so the model consults the right one without being asked. On any
# harness that does not run this handler, the skills still work — they are
# selected the ordinary way, by their descriptions.
#
# Fires on startup, clear, and compact so the routing rule survives context
# compaction. Keep the injected text short: it is a pointer to the skills, not a
# copy of them.
#
# Contract: print a single JSON object on stdout with
# hookSpecificOutput.additionalContext, then exit 0.

cat <<'JSON'
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "The `voice` plugin is installed. Route each output ELEMENT (not the whole response) to exactly one voice.\n\nOut of scope for both skills, and this beats everything below: code and file contents the user will save, commit messages, creative or persona writing, and turns that are only a clarifying question or only tool calls. Ship those unstyled and uncompressed — a config or schema you were asked to AUTHOR is file contents, not a machine-read artifact.\n\nStandalone machine-read artifacts the reader scans — agent traces, tool-call logs, status lines, progress updates, handoff notes, state dumps, reference cards, and structured data another agent parses — follow the `machine-voice` skill: compress lexically, use markdown as navigation, use emojis as typed status markers.\n\nEvery other element is prose a human reads and follows the `human-voice` skill: verdict first, paragraphs of 4 sentences or fewer, load-bearing claims marked with the closed vocabulary ✅ verified / ⚠️ inferred / ❓ unverified (tag the verdict and the exceptions, not every line). A table or block that serves surrounding explanation stays with `human-voice`.\n\nThose two glyph sets are different vocabularies: machine-voice's ✅ ❌ ⚠️ mark execution status, human-voice's mark claim provenance. Never mix them in one output.\n\nThe `ai-writing-mistakes` skill is a wording pass, not a fourth voice: it claims no element. Run it over any prose a human reads, including prose you were asked to author into a file, and fix each tell by restoring the claim it stood in for rather than by swapping the word. Never rewrite prose you were asked only to review, and never report a cleanup you did not make.\n\nNever run the `second-opinion` skill unbidden — offer it and wait for the user to accept. Read the relevant SKILL.md before applying any of this in detail."
  }
}
JSON

exit 0
