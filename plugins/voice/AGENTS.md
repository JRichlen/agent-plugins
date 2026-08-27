# AGENTS.md — voice

Four skills that decide how output is written. `human-voice` governs prose a
human reads: verdict first, scannable, claims tagged with a closed confidence
vocabulary. `machine-voice` governs machine-read artifacts — agent traces, logs,
status lines, state dumps, schemas — and compresses them. `second-opinion` is an
offer-only validation pipeline that stress-tests a verdict and re-emits it
grouped into verified, flagged, and conflict. `ai-writing-mistakes` is a
wording pass over prose the first skill has already laid out. It removes the
filler that marks text as machine-written, and it is not a fourth voice.

The four ship together because they are one system: the first two partition a
single decision by reference to each other, the third is the escalation target
the first one names, and the fourth explicitly declines to claim an element so
that partition stays exclusive. Installed apart, each describes a counterpart
that is not there.

## How to use it

Read the skill that matches the element you are about to write:

- `skills/human-voice/SKILL.md` — prose a human reads
- `skills/machine-voice/SKILL.md` — traces, logs, status lines, schemas,
  structured data. Pattern detail lives in
  `skills/machine-voice/references/lexical-patterns.md`
- `skills/second-opinion/SKILL.md` — validating a verdict, only after the user
  accepts the offer
- `skills/ai-writing-mistakes/SKILL.md` — the wording pass. Runs over anything
  `human-voice` governs, and over prose you were asked to author into a file
  (README, docs, PR body, release notes). Full tell catalogue in
  `skills/ai-writing-mistakes/references/tells.md`

The routing rule is **per output element, not per response**. One reply commonly
contains both: prose sections follow `human-voice`, an embedded trace follows
`machine-voice`. Code and file contents, commit messages, creative writing, and
turns that are only a clarifying question or only tool calls fall outside both —
and that exemption takes precedence over machine-voice's list, so a config or
schema the user asked you to author ships verbatim rather than compressed.

`ai-writing-mistakes` sits outside that routing decision entirely. It takes no
element from either voice; it revises wording inside prose one of them has
already placed, plus prose destined for a file the user asked you to write.

`commands/voice.md` is the entry point a user invokes to read the routing rule
on demand.

## PORTABILITY: harness-agnostic, with one optional convenience

The skills are plain prose discipline and port to any coding agent. This plugin
also ships an optional Claude Code session-start hook — `hooks/hooks.json` and
`hooks-handlers/session-start.sh` — which injects the routing rule as additional
context so the right skill is consulted without being asked.

That hook is a **convenience, never a dependency**. On a harness that does not
read `hooks/hooks.json`, nothing breaks: the skills are selected the ordinary
way, by their descriptions. No skill's instructions depend on the hook having
run, and none of them claim to be invoked by it.

`second-opinion` has one genuine capability requirement — a subagent-spawning
tool. Where none exists it is required to decline and fall back to search-based
verification rather than simulate a result.

## The invariant this plugin defends

> ALWAYS route each output element to exactly one voice — prose to
> `human-voice`, machine-read artifacts to `machine-voice`. NEVER run
> `second-opinion` unbidden, and never emit its validation format without having
> actually dispatched the subagents it reports. NEVER report work you did not
> do: that covers a fabricated validation and, in `ai-writing-mistakes`, a
> cleanup pass claimed over a draft left unchanged.

The third clause is the one with teeth, and it binds two skills. A model that
emits a grouped Verified/Flagged/Conflict block and a delta line without having
dispatched anything has produced a counterfeit of exactly the thing the user
asked for when they said "are you sure": indistinguishable from the real
output, and worse than no answer. `ai-writing-mistakes` has the same shape of
failure at lower stakes: "cleaned that up for you" over prose that was never
touched, which the user has no way to check without re-reading the draft
themselves. Its other teeth clause is consent — a review request gets a
diagnosis, never an unrequested rewrite of someone else's words.

The deterministic checks that defend it live in `evals/cheap/checks.sh` and run
as part of the marketplace cheap tier. The prose-level behaviour — that the
partition routes correctly and that the ungated case refuses to fabricate — is
defended by the behavioral tier in `evals/promptfoo/promptfooconfig.yaml`.
