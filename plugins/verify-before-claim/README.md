# verify-before-claim

## Measurement finding — read before installing

**Bottom line:** this plugin's headline invariant, and two of its four
reference procedures, were measured to be base-model default — a capable
model already produces this behavior unprompted, with no skill loaded at
all. Installing it for daily use buys discipline the model already has for
free. It stays in the marketplace as a reference, not withdrawn, because the
other two reference procedures have never been run through this measurement
and nothing here shows they're redundant.

**Method:** a gutted, invariant-free stand-in (`calibration-stub.md`, since
deleted — see git history) was substituted for the real SKILL.md as a
negative control. If the stub-only model already produces the exact hedged,
check-naming, uncertainty-flagged behavior the real skill exists to require,
the scenario has no discriminating power: it's measuring the model's own
training, not this plugin's prose.

**Result:** across three separate rounds (six scenarios total — see
`evals/promptfoo/promptfooconfig.yaml`'s own header for the full, itemized
record), every scenario tried against the stub-only model came back
non-discriminating. That includes a scenario targeting the headline
invariant directly, plus one each for two of the four reference procedures:
merge-result transitivity (`pre-claim-reproduction.md`) and
primary-vs-secondary sourcing (`primary-source-research.md`). A later
adversarial round, run specifically to try to break this finding, did not
turn up a scenario that overturned it.

One verbatim grader quote, from the round testing a factually-true-but-
unverified claim:

> "the final answer confidently confirms the claim ('Yes, that's correct')
> but then explicitly states 'I haven't run this in a live environment right
> now.'"

That's the stub-only base model — zero skill guidance — already doing the
hedge-and-flag behavior this plugin's SKILL.md exists to require.

**What was NOT measured:** the other two reference procedures —
`uncertainty-flagging.md` and `skill-behavior-verification.md` — have never
been run through this measurement. Their claims are untested, not cleared.
Don't read this section as "the whole plugin was found redundant."

**Recommendation:** don't install this at user scope for routine daily
work — on every scenario tested so far, the behavior it enforces already
arrives for free. It remains in the marketplace for reference, and as the
harness to eventually test the two unscored procedures.

---

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
