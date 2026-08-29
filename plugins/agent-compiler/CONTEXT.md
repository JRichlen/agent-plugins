# CONTEXT.md — agent-compiler ubiquitous language

Glossary only. No implementation detail; the design doc and ADRs carry those.

- **Dimension** — a coordinate of an AgentQuery that the compiler reads
  (`role`, `task`, `domains`, `views`, `stance`, `environment`, `risk`,
  `effectCeiling`, `facts`, `name`). NOT a module kind: adding registry
  content along existing coordinates is "populating a dimension"; adding a
  new coordinate is a language change and needs an ADR.
- **Module** — one Markdown file in a registry with frontmatter and a stable
  `id`. Kinds: `behavior`, `view`, `capability_interface`.
- **Identity** — a named, reusable agent persona. Represented as a `view`
  module (selectors + traits + effect ceiling), never as a prose blob.
- **View** — selector/constraint composition a query opts into by id.
  Contributes traits and a `max_effects` ceiling; contributes no behavior
  text of its own.
- **Preference** — a lean toward one library/language/tool over another.
  Represented as behavior content scoped by `domains` (e.g. `typescript`),
  so it activates only when a query asks for that domain.
- **Behavior unit** — an addressable block inside a behavior module:
  `rule`, `probe`, `example`, `antipattern`. Compiled id is
  `<module-id>#<block-id>`.
- **Effect ceiling** — the maximum effect set an agent may link:
  intersection of the query's `effectCeiling` and every selected view's
  `max_effects`. Absence anywhere fails compilation.
- **AgentQuery / AgentImage / provenance / deterministic boundary** — see
  the design doc (`docs/designs/agent-compiler-plugin.md`) and the plugin
  `README.md`; meanings unchanged from the handoff glossary.
