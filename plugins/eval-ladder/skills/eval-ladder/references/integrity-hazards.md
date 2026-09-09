# Hazards that live between tiers

These are not defects in any one tier. They are ways a whole suite can be green
and wrong, and none of them is caught by adding another check of the same kind.

## Tuning on the gate

A regression set you keep editing until it passes has stopped being a regression
set. The mechanism is mundane: a scenario fails, the failure looks defensible,
the assertion is loosened to accept it, the suite goes green. Each step is
reasonable; the sum is a suite fitted to the system's current behavior.

Symptoms to look for in your own history: assertions described as "regraded
from a live run", slots relaxed from exact to "tolerant", negatives that
acquired an exception for one observed output.

Defenses: keep a **held-out set that is never regraded** — if a case is
loosened, it moves out of the holdout permanently. Record *why* each loosening
happened, in the config, next to the assertion. Separate the set you develop
against from the set you gate on.

## Criteria drift

The inverse hazard, and the reason tuning is tempting: you genuinely cannot
write the right criteria before grading real outputs. Expect the rubric to
evolve — but distinguish "I learned the criterion was wrong" (legitimate, record
it) from "the model failed and I moved the line" (fitting). The test is whether
you would have made the same edit before seeing the failure.

## Saturation

A suite where everything passes measures only catastrophe. It cannot rank two
candidate versions or detect gradual erosion. When a suite saturates, audit it
before celebrating: saturated suites frequently turn out to contain broken
graders, exploitable shortcuts, and wrong ground truth. Then add harder cases.

## Missing controls

Without a must-not-fire twin and a no-intervention control, a green says only
"the system did the right thing", never "the intervention caused it." Roughly
half of most suites' scenarios need a control they do not have.

## The harness confound

The same model under different harnesses can produce *opposite* rankings. What
teams call "the model's behavior" is mostly harness plus product plus prompt:
context handling, tool design, retries, system reminders. Adding a deterministic
tool layer has been measured to erase both the spread between models and the
run-to-run variance within one.

Consequences for an eval suite:

- A result from one harness does not transfer to another. If the artifact under
  test ships cross-harness, at least one rung must run cross-harness, or the
  portability claim is untested.
- Infrastructure is a variable: resource limits alone can move agentic coding
  scores by several points — larger than the gaps between adjacent models.
- Pin and report the harness, the sampling settings, and the grader alongside
  every number.

## Contamination

A public eval corpus can end up in a model's training data, and an agent that
can search the web can find the answers — including its own benchmark's source.
Three shapes: metadata leakage, question-context leakage, explicit answer
leakage.

Defenses, in order of strength: date-window tasks past the model's cutoff; a
refresh pipeline so the post-cutoff pool never empties; a human-authored matched
holdout scored against the public set, where the accuracy gap *is* your
contamination estimate; and for agents, denying network and history access
during graded runs. Objective ground truth (tests, exact match) keeps freshness
the only moving variable.

## Grading the wrong thing well

Two specific ways a technically-correct harness measures the wrong object:

- **Reasoning leaking into the graded output.** If the harness prepends a
  model's reasoning trace to what the grader sees, you are grading the thinking,
  not the answer. Turn it off explicitly.
- **Success by retrieval.** Audits of "solved" coding tasks have found a
  majority of successes came from looking up the known fix rather than deriving
  it. If the task exists publicly, isolation is part of the measurement.

## Reward hacking and metric pressure

Any gap a metric ignores gets exploited once there is pressure on the metric —
whether that pressure is gradient descent or an agent iterating to make CI go
green. Before you let anything optimize against a scorer, ask what the cheapest
way to satisfy it without doing the work would be, and close that path first.
Skipping, disabling, or quarantining a failing test is the canonical instance.

## Offline is not online

An offline suite answers "did this change break a known case." It cannot answer
"what is actually happening in real use." Those need different instruments:
a curated regression set as the CI gate, and sampled real traffic scored
continuously for monitoring and drift. A suite that has never seen a real
session is a hypothesis about usage, and the honest report says so.

Watch for a related circularity: an "examples of real behavior" artifact
generated *from the eval itself* is not independent evidence of real usage. It
is the eval, rendered.
