# Devil's-advocate technique (DEEP tier)

Load this only for a DEEP-tier branch's first answer, or when a STANDARD
answer contradicts an earlier one or the plan's own stated goal — grill-me's
default is assistive, not adversarial, so this is the deliberate exception,
not the norm.

## Steelman the opposite

State the strongest version of the alternative the user did *not* pick, using
their own stated goals as ammunition — not generic caution ("have you
considered edge cases?"). Then ask them to defend their choice against it in
one line. A steelman that a reasonable engineer could actually be persuaded by
is doing its job; a strawman that's easy to wave off is not.

## Pre-mortem (Klein)

One line, asked directly: "Assume this shipped and broke in three months —
what's the most likely reason?" This forces a concrete failure mode, not a
vague risk category ("something could go wrong"). If the user can't name one,
that absence is itself a signal — either the design is more solid than it
looked, or nobody has actually thought past shipping it, and the recommendation
should say which.

## Writing a tradeoff comparison that earns its recommendation

- 2-3 options, never more — comparison quality collapses past three, and a
  longer list reads as indecision rather than analysis.
- One line each: `option — chief upside — chief risk`. No hedging paragraphs;
  if a nuance doesn't fit in one line, it isn't the deciding nuance.
- The recommendation should follow from the plan's *own* stated priorities
  from earlier rounds, not a generic best practice: "recommend B — you said
  latency mattered more than cost in Q1, and B is the only option that keeps
  p99 flat." Naming the earlier answer it derives from is what makes the
  recommendation auditable rather than asserted.
- If two options are genuinely close, say so and name the tie-break variable
  instead of forcing false confidence in one over the other.

## Requiring explicit confirm (DEEP only)

Unlike LIGHT and STANDARD, silence is never acceptance at DEEP tier. If the
user doesn't respond to the devil's-advocate pass and tradeoff comparison with
something that reads as a decision, ask once more, directly, rather than
assuming the recommendation and moving the round forward.
