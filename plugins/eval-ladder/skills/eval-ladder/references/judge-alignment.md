# Building a judge that is evidence

## Start with error analysis, not with a rubric

You cannot write the rubric before you grade. Grading real outputs is what
*teaches* you the criteria — this is "criteria drift", and it means a rubric
authored from imagination encodes the failures you guessed rather than the ones
you have.

The loop:

1. **Sample** 20–50 real traces (50–100 for a mature system). Stratify by
   feature or user type, or pull outliers by length/latency.
2. **Open coding.** ONE domain expert — a benevolent dictator, not a committee —
   writes a free-text note on the **first / most upstream** failure in each
   trace. Downstream errors are usually symptoms; logging them muddies clusters.
3. **Axial coding.** An LLM groups the notes into 4–8 specific, actionable
   categories. A human reviews and tightens them.
4. **Prioritize** by frequency × severity (× business value). Take the top 4–7.
5. **Build one narrow binary check per mode** — and ask first whether a
   *deterministic* predicate can decide it. Most can. Only the residual
   subjective modes justify a judge.

The open-code notes are not throwaway: they become the few-shot examples for the
judges you build in step 5. That is the flywheel.

## Judge construction

- **Binary, always.** PASS/FAIL, not 1–5. The gap between a 3 and a 4 is noise;
  a binary verdict forces a crisp decision and unlocks classification metrics.
  Kill every Likert scale.
- **Reason then verdict.** Chain-of-thought before the single-letter answer, then
  map to {1.0, 0.0}.
- **The signal is in few-shot critiques, not rubric verbiage.** Pair each
  labeled example with the expert's one-line *why* ("critique shadowing"). A
  bloated rubric in the system prompt does not fix misalignment; concrete
  labeled critiques do. If a judge is misaligned, swap the judge model before
  adding more prose.
- **Few-shot examples are sensitive** to label, order, and count. Re-measure
  after editing them. More shots is not automatically better.

## Validation: TPR and TNR, separately, on held-out labels

This is the step that turns a judge from an opinion into evidence.

Have a domain expert label 100+ examples. Hold some out. Report:

- **TPR** (recall on failures): of the real failures, what fraction did the judge
  catch?
- **TNR**: of the real passes, what fraction did the judge let through?
- FP and FN **counts**, not just rates.

**Never report raw agreement.** Under class imbalance it lies outright: if 90%
of traces genuinely pass, a judge that rubber-stamps PASS scores ~90% agreement
while catching zero failures — TPR ≈ 0. A suite whose scenarios are all written
as "the system should do the right thing" is exactly this imbalanced case, and
raw agreement on it is uninformative by construction.

Cohen's kappa is better than raw agreement but still not a substitute: it is a
single number that does not tell you which direction the judge errs, and on a
nearly all-green run it has little information to carry. Draw calibration
samples from runs that contain real failures.

Ship only when both TPR and TNR clear the bar you set in advance. Re-validate
whenever the agent, the prompt, the judge model, or the data distribution
changes.

## Self-agreement is the noise floor

Grade the same outputs twice with the same judge. That self-agreement is the
label-noise floor of the whole tier. If it sits below your pass-rate floor, the
tier cannot separate a real effect from grader noise, and no number above it
should be reported as a measurement.

Cross-family agreement (a judge from a different model family, same rubric)
tells you whether a verdict is a property of the rubric or of the judge. It does
not tell you which judge is right.

## Known judge biases

Position bias, verbosity bias, and self-enhancement (a model preferring its own
outputs). Prefer direct binary grading over pairwise where you can; where you
use pairwise, swap the order and average. Do not use the model under test as its
own grader.

## The cost hierarchy

Assertions and reference-based checks are cheap to build and cheap to maintain.
A judge needs 100+ labels, ongoing re-validation, and coordination across roles.
So: only build a judge for a failure mode you will iterate on repeatedly. For
everything else, write the assertion.
