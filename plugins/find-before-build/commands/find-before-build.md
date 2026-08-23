---
description: >-
  Search for the existing implementation before writing a new one: name the searches you ran for an existing helper, abstraction, or pattern and what they returned, before introducing anything new. Use before adding a utility, wrapper, config knob, or dependency to a codebase you did not write end-to-end.
---

Invoke the `find-before-build` skill and follow
`skills/find-before-build/SKILL.md`.

For the abstraction about to be introduced (or the one the user named): state
its purpose in the codebase's vocabulary, run at least two searches from
different angles (name, mechanism, convention, dependency manifest), and show
the receipt — searches verbatim, results summarized — before any new code.
Then decide by the receipt: use/extend a found equivalent, justify in one
sentence why a found one is unusable, or build only when the search came back
genuinely empty.
