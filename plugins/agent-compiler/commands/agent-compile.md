---
description: "Compile a deterministic, content-hashed agent from registry behavior modules: normalize intent into a typed AgentQuery, run the kernel, and render the result."
argument-hint: "describe the agent you want, or point at a query JSON"
---

Invoke the `agent-compiler` skill and follow `skills/agent-compiler/SKILL.md`.

Normalize the user's intent ($ARGUMENTS if given) into a typed AgentQuery —
interviewing until role, task, domains, views, and an effect ceiling are
explicit — show the query JSON, then compile it with
`scripts/compile.py compile` and render the image with
`scripts/render_claude_agent.py`. On diagnostics, fix the registry source and
recompile; never suppress a failure or paste prose into the rendered output.
