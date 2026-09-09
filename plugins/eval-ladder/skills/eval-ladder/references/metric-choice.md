# Choosing the metric

## pass@k and pass^k answer opposite questions

- **pass@k** — probability that *at least one* of k attempts succeeds. A
  **capability** question: can the system do this at all, given retries?
- **pass^k** — probability that *all* k attempts succeed (`p^k`). A
  **reliability** question: can I let this run unattended?

They move in opposite directions as k grows. At p = 0.75, pass@10 ≈ 1.00 and
pass^10 ≈ 0.056 — the same system, two opposite stories. Always say which one
you mean; comparing your pass@10 to someone else's pass^10 is meaningless.

Decide the metric **before** running, and record the choice in the eval config
so it cannot drift after you see the numbers.

### Estimating pass@k

Never report the naive `1 - (1-p)^k`; it is biased high for small n. With n
samples of which c passed, use the unbiased estimator
`pass@k = 1 - C(n-c, k) / C(n, k)`, computed as a running product rather than
by forming the binomials. Draw n ≫ k. Report n and k beside the number. Average
per-problem values across problems; do not pool every sample into one ratio.

Sanity check: as k rises, pass@k must be non-decreasing and pass^k
non-increasing. If not, the estimator is wrong.

Both assume the k trials are **independent**. Temperature 0, a shared seed, or a
cached prefix breaks that assumption and both numbers stop meaning what they say.

## The floor is a policy, not a default

A per-scenario pass-rate floor over N repeats (e.g. 2-of-3) is the pragmatic
middle ground: it stops a single lucky draw reading as green without paying for
large n. But a **uniform** floor applied to every scenario is a policy decision
made by accident.

Segment the floor by what the scenario guards:

| Scenario guards | Floor | Why |
|---|---|---|
| A preference, a style, a nicety | majority (e.g. 0.6) | One bad draw is noise |
| A correctness property | high (0.8+) | Regression should be visible |
| An **irreversible action** — delete, drop, force-push, spend, send | **1.0 (pass^k)** | A guard that holds two times in three is not a guard |

A safety invariant scored at a majority floor is stating, in the config, that
failing it one time in three is acceptable. Almost no one means that.

## FAULT is not FAIL

A red row has two causes that must never be pooled:

- **FAIL** — the grader judged the answer wrong. Evidence about the system.
- **FAULT** — the call never completed: a 5xx, an abort, an empty or truncated
  body. Evidence about the weather.

Score the floor over valid samples only, excluding FAULTs. But **fail closed on
starvation**: a scenario whose samples were nearly all FAULTs is "never tested",
not "green". Require a minimum count of valid samples and of total runs, and go
red when either is unmet. Retry transient 5xx with backoff before classifying.

## Saturation and difficulty calibration

A suite everyone passes has no measurement left in it. If every scenario sits at
3-of-3, the suite can register a catastrophic regression and nothing else — it
cannot distinguish a good change from a neutral one, and it cannot rank two
candidate versions.

Target a difficulty band where the system succeeds sometimes and fails
sometimes; that is where the gradient lives. When a suite saturates, treat it as
a signal to dig — audit the tasks for shortcuts and broken graders before
concluding the capability is solved — and add harder cases rather than retiring
the suite.

## Controls: the must-not-fire twin

Every must-fire scenario needs a twin that must **not** fire, and every suite
needs a **calibration control**: the same scenario run *without* the
intervention under test. If the bare system already behaves correctly, the
with-intervention green measures nothing on that scenario.

A suite with no controls cannot separate "the skill works" from "the model would
have done that anyway." This is the cheapest missing tier in most suites.

## Cost is a metric

Report cost per run beside the score. A configuration that wins on accuracy and
costs 20× is not obviously better, and unreported cost is how suites quietly
become unrunnable.
