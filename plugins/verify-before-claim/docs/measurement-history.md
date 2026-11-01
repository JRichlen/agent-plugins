# Historical claim-check measurement

This record predates the acceptance-mechanism integration. It is not evidence
that the new integration or every host works.

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
