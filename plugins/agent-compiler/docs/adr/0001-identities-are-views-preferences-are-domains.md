# ADR 0001: Identities are views; preferences are domain-scoped behavior

- Status: Accepted (grill session, 2026-08-29)

## Decision

New registry dimensions are populated as **content along existing
coordinates**, not as new module kinds or query coordinates:

- An **identity** is a `view` module (selectors + traits + effect ceiling +
  `requires` edges to its behavior), never a prose persona blob.
- A **library/language preference** is a `behavior` module scoped by
  `domains` (e.g. `typescript`), so imported taste activates only when a
  query asks for that domain.
- Externally sourced material (Karpathy, Pocock, Anthropic, Willison) is
  paraphrased with attribution in module prose; provenance carries the file.

Two kernel additions were accepted alongside, because they make existing
dead coordinates load-bearing rather than adding new ones: applicability
conditions (module `environments`/`risks` gate selector matching) and stance
validation (`stance` must be a trait some selected view declares).

## Context

The alternatives were a first-class `identity` kind and/or a `preference`
unit block. Both grow the module language, and every language addition is
effectively permanent once modules are published against it (the handoff's
"premature ontology explosion" warning, open question 4).

## Consequences

- Positive: zero schema change; the four block kinds and three module kinds
  survive contact with three new dimensions; identity ceilings compose with
  the existing effect system for free.
- Negative: "prefer X over Y" is expressed as a `rule` with should-strength
  rather than a dedicated construct; if that reads forced as the preference
  corpus grows, revisit a `preference` block kind (the grill session's
  explicit reopening condition).
