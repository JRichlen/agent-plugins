# The judged-verifier contract

Most invariants can be defended by a deterministic check. Some cannot: prose
quality, design judgment, whether a plan is *good*. Those need a judged
verifier — an LLM rubric — and a judged verifier without a negative control
measures the model, not the work.

This is the code-domain mutation control, translated.

## The contract

1. **One judge per dimension.** A single rubric scoring "quality" collapses
   distinct failures into one number and hides which one fired. Score
   correctness, coverage, and honesty separately if you care about all three.
2. **Hard negatives are built in, not added later.** For every case, author
   the input that *must fail* the rubric alongside the one that must pass.
3. **A calibration stub is mandatory.** Run the same scenario with the skill
   gutted — generic, invariant-free guidance. The stub must FAIL the rubric.
   If it passes, the scenario measures the base model's defaults, not your
   skill, and the pack proves nothing.
4. **A failing calibration is a finding, never a silencing.** Replace the
   scenario with harder bait: a case where the skill-guided answer and the
   naturally-helpful answer genuinely *diverge*. Do not delete the control.

## The bar this marketplace already measured

`verify-before-claim`'s pack documents **six scenarios, six rejections** —
every one found that a capable base model already produced the disciplined
behavior unaided. That is the standard: "the rule is specific" is not enough,
and neither is "the rule lives in a reference file". Look for divergence.

The two scenarios that *did* discriminate here — `semver-gate`'s
non-transitive consent across a new mechanism, and `wayfinder`'s type-lock —
worked because they were **counter to what a helpful assistant would
otherwise do**.

## Cost note

Judged verifiers are the expensive tier. Reach for one only when no
deterministic check can defend the invariant — and when you do, the negative
control is the part that makes the spend worth anything.
