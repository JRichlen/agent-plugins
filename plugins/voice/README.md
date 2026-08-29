# voice 🗣️

Four skills that decide how output is written, with an explicit routing rule
for picking between them.

- **human-voice** — prose a human reads. Verdict first, scannable layers,
  claims tagged `✅` verified / `⚠️` inferred / `❓` unverified.
- **machine-voice** — machine-read artifacts: agent traces, tool-call logs,
  status lines, state dumps, schemas. Compressed lexically, structured for
  scanning, emojis as typed status markers.
- **ai-writing-mistakes** — the wording pass. Removes the tells that mark prose
  as machine-written (negation flips, rule-of-three padding, hedge stacks,
  unearned intensifiers, empty closers) by restoring the claim each one was
  standing in for. Not a fourth voice: it never claims an element.
- **second-opinion** — an offer-only validation pipeline. Batches fact-checks,
  adds scoped advisor personas, re-emits the verdict grouped into verified /
  flagged / conflict with a mandatory delta.

## Install

```sh
/plugin marketplace add JRichlen/agent-plugins
/plugin install voice@jrichlen
```

## What's in the box

| Path | What it is |
|---|---|
| `skills/human-voice/` | Prose discipline: intent triage, layered layout, confidence tags |
| `skills/machine-voice/` | Compression layers, plus `references/lexical-patterns.md` loaded on demand |
| `skills/ai-writing-mistakes/` | The wording pass, plus `references/tells.md` loaded on demand |
| `skills/second-opinion/` | Validation pipeline with a hard subagent budget |
| `hooks/` | Optional session-start context injection (Claude Code only) |
| `commands/voice.md` | Ask which voice governs a given element |
| `evals/cheap/checks.sh` | Deterministic checks that the invariant is intact |
| `evals/promptfoo/` | Behavioral tier — an LLM judge on routing and refusal |

## How routing works

**Per output element, not per response.** One reply commonly contains both: the
explanation is `human-voice`, an embedded trace is `machine-voice`.

`ai-writing-mistakes` is outside this decision. It claims no element; it revises
wording inside prose one of the voices already placed, and inside prose you were
asked to author into a file.

Code and file contents, commit messages, creative writing, and turns that are
only a clarifying question or only tool calls fall outside both — they ship
unstyled. That exemption beats the machine-voice list: a config or schema you
were asked to *author* is file contents, not a machine-read artifact.

## The always-on part

On Claude Code, a session-start hook injects the routing rule once per session
(and again after a context compaction) so the right skill is consulted without
being asked. It costs one short injection per session, not a per-turn tax.

The hook is a convenience, not a dependency. On any other harness the skills
still work — they are selected the ordinary way, by their descriptions, and no
skill's instructions assume the hook ran. To turn the always-on behaviour off
while keeping the skills, uninstall the plugin and copy the four `skills/`
directories into your own skills path.

## The one thing this plugin will not do

Neither skill with teeth will report work it did not do. `ai-writing-mistakes`
will not label a draft "cleaned up" without having changed it, and will not
rewrite prose you asked it only to review — a review request gets the line
quoted, the tell named, and the rewrite offered.

`second-opinion` refuses to produce validation output it did not earn. Where no
subagent-spawning tool exists, it is required to say so and offer search-based
verification instead — emitting a grouped Verified/Flagged/Conflict block and a
delta without having dispatched anything would counterfeit exactly what the user
asked for when they said "are you sure".

## License

MIT
