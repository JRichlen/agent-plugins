# verify-before-claim

Never assert a fact, completion, or reproduction claim without naming and running the specific check that would prove it false, first.

An always-on, inline discipline — no subagent required, no offer/gate step, no
Workflow tool. It fires every time the agent is about to write a sentence
that asserts a fact, completion, or reproduction: name the single observation
that would prove the claim false, run that exact check directly in the same
turn, and attach its literal output next to the claim. If the check couldn't
run, the claim is flagged "not verified" or "assumed, unchecked" adjacent to
it — never asserted as settled, and never smoothed into confident prose later
in the response.

See `skills/verify-before-claim/SKILL.md` for the full invariant and core
procedure, and `skills/verify-before-claim/references/` for the four
situational sub-procedures (pre-claim reproduction, uncertainty flagging in
handoff docs, primary-source research, and skill-behavior verification).

PORTABILITY: "subagent" and "Workflow tool" below name Claude-Code-only
primitives used only to describe *other* plugins for contrast — this plugin
itself needs neither. The discipline is harness-agnostic; on any harness it
is just "run the check yourself, in this turn, before writing the claim."

## Install

```
/plugin marketplace add JRichlen/agent-plugins
/plugin install verify-before-claim@jrichlen
```

## Not this

This sits near two other plugins in the marketplace without being either of
them:

- **second-opinion** is post-hoc, offer-only, and requires a subagent tool —
  it re-validates a verdict that already exists, on request.
- **orchestrate** is a Workflow-tool template for fanning research out across
  multiple subagents and adversarially verifying their claims.

`verify-before-claim` runs inline, in the main thread, unprompted, by the same
agent making the claim, using direct checks rather than dispatched subagents.
See the "Not this" section of the SKILL.md for the full differentiation.

## License

MIT
