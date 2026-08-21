# Skill behavior verification

Loads when: uncertain what a skill, plugin, tool, or command actually does,
before describing or relying on its behavior.

## Read the source, not the description

A name and a one-line description are written to help a discovery mechanism
decide WHEN to trigger something — they are not a specification of WHAT it
does once triggered. Treating the description as the spec is exactly the
error this file exists to prevent.

- **Before describing or relying on what a skill, plugin, tool, or command
  does, open its actual definition** — the `SKILL.md` body, the source file,
  or the `--help` output — and read it.
- Never infer behavior from a name or a one-line description alone when the
  claim depends on getting the behavior right. "It's probably like the other
  one" is not a check.
- This applies to your own claims about your own tools just as much as to
  someone else's: if you are about to say "the `second-opinion` skill
  requires a subagent tool," that claim needs to have come from actually
  reading `second-opinion`'s `SKILL.md`, not from the one-line description in
  a plugin listing. (PORTABILITY: "subagent tool" here names a Claude-Code
  primitive only because it's the real example being cited — the
  read-the-source-not-the-description rule itself is harness-agnostic.)

## Where this bites in practice

- Assuming a command's flag exists because a similarly-named tool has it.
- Describing a skill's gating logic from its trigger phrases instead of its
  body — trigger phrases describe when to reach for it, not what it does once
  reached for.
- Relying on a plugin's README summary of its own behavior instead of the
  SKILL.md it is summarizing, when the two have drifted.
