---
id: typo.module
kind: behavior
version: 1.0.0
task: [pull-request-review]
---

# Fixture: typo'd frontmatter key

<rule id="r" strength="must">
'task' (singular) is not a known key; this must fail with BAD_MODULE_KEY
instead of silently never being selected.
</rule>
