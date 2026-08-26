# AGENTS.md — recurrence-detector

Close the growth loop's DETECT step: read the exhaust every run already sheds — stop-reports, scope-fence findings, unmet criteria, diary entries — cluster it by failure shape, and surface any shape seen at least N times as a named candidate invariant with its sightings cited. Proposes; never scaffolds. Use when asking what keeps going wrong, or before adding a skill on a hunch.

## How to use it

Read `skills/recurrence-detector/SKILL.md` and follow it — it is the authoritative
description of this plugin's workflow and the invariant it defends.

The command `commands/recurrence-detector.md` is the entry point a user invokes.

## The invariant this plugin defends

A failure shape is surfaced as a candidate invariant ONLY when it was seen at least N times across consolidated exhaust and every sighting is cited by source and date — and a candidate is NEVER auto-scaffolded into a skill: the output is a proposal a human and plugin-factory dispose of.

The deterministic checks that defend it live in `evals/cheap/checks.sh` and run
as part of the marketplace cheap tier.
