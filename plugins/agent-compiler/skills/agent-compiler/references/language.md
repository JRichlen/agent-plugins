# Behavior module language

One authoring format for everything in a registry: Markdown with restricted
YAML-style frontmatter and XML-like semantic blocks. The kernel parses this
subset deterministically with no dependencies — anything outside it is a
compile error (`BAD_MODULE`), never a guess.

## Frontmatter subset

Supported syntax — nothing else:

```markdown
---
id: security.iam.review          # required; [a-z0-9._-], stable, semantic
kind: behavior                   # required; behavior | view | capability_interface
version: 1.0.0                   # required
tasks: [pull-request-review]     # inline list…
domains:                         # …or one-level dash list
  - aws
  - iam
requires: [behavior.evidence]
conflicts_with: []
supersedes: []
capabilities: [scm.pull_request.read]   # behavior modules: required interfaces
effects: [network, scm:read]            # capability_interface modules only
max_effects: [network, scm:read]        # view modules: the ceiling they impose
traits: [adversarial]                   # view modules: stance traits
---
```

No nesting, no multi-line scalars, no anchors. Quoted or bare scalars only.

## Semantic blocks (behavior modules)

Exactly four block kinds, non-nested, each with a required `id`:

```markdown
<rule id="least-privilege" strength="must">
Evaluate permissions against the minimum privileges required.
</rule>

<probe id="cross-boundary-access">
Could this change allow a principal to cross a trust boundary?
</probe>

<example id="good-finding">
"s3:* on arn:aws:s3:::prod-* grants delete on every prod bucket (diff L42)."
</example>

<antipattern id="unsupported-vulnerability">
Do not describe a theoretical vulnerability without concrete evidence.
</antipattern>
```

A block's compiled unit ID is `<module-id>#<block-id>` — addressable, citable,
independently selectable, and carried with provenance (module, version, source
file, line range) into every AgentImage.

## Selection semantics (exact, documented, deterministic)

- **Views** are selected only when the query names them in `views`.
- A **behavior module** is selected when its `tasks` contain the query's
  `task`, its `roles` contain the query's `role`, or its `domains` intersect
  the query's `domains`.
- `requires` closes transitively (cycles fail; missing IDs fail).
- `conflicts_with` between two selected modules fails compilation unless one
  `supersedes` the other, in which case the superseded module is dropped.
- **Capability interfaces** are pulled in only via a selected module's
  `capabilities`; the union of their `effects` must fit inside the effective
  ceiling — the intersection of the query's `effectCeiling` and every
  selected view's `max_effects`. No ceiling from either source fails closed.
- **Applicability conditions**: a module declaring `environments:` or
  `risks:` selector-matches only when the query's `environment`/`risk` is in
  the list. Explicit `requires` edges and views named in `query.views` are
  exact asks and ignore applicability.
- **Stance validation**: every entry in the query's `stance` must be a trait
  some selected view declares (`traits:`), or compilation fails with
  `UNDECLARED_STANCE` — stance is never decorative.

## AgentQuery

```json
{
  "name": "security-pr-reviewer",
  "role": "reviewer",
  "task": "pull-request-review",
  "domains": ["aws", "iam"],
  "views": ["view.security-reviewer"],
  "stance": ["adversarial", "evidence-driven"],
  "environment": "production",
  "risk": "high",
  "effectCeiling": ["network", "scm:read"],
  "facts": {}
}
```

`name`, `role`, `task` steer selection and rendering; `facts` is opaque
context carried into the image; list fields are canonicalized (sorted) so
their order never changes the hash.
