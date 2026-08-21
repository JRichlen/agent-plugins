# AGENTS.md — codebase-design

Before writing a new interface (module boundary, class API, function signature, or service contract) that at least two call sites will depend on, that crosses a module/service/team/persistence boundary, or that will be expensive to change later — produce 3+ radically different candidate designs and compare them on depth, locality, and seam placement before picking one. Use on "before committing to an interface", "design this API/module/class boundary", "how should this be structured", "compare interface designs", "is this the right abstraction", "design it twice", reviewing a proposed interface shape in a PR — or self-trigger whenever about to write a new interface meeting that bar.

## How to use it

Read `skills/codebase-design/SKILL.md` and follow it — it is the authoritative
description of this plugin's workflow and the invariant it defends.

The command `commands/codebase-design.md` is the entry point a user invokes.

## The invariant this plugin defends

Before committing to an interface (a module boundary, class API, or function signature that ≥2 call sites will depend on, or that crosses a service/team/persistence boundary, or that is expensive to change later): ALWAYS produce 3+ radically different candidate designs and compare them on depth, locality, and seam placement before picking one — NEVER let the first workable interface ship unexamined. The chosen interface must ALWAYS hide its implementation complexity behind a boundary that tests hold honest at a confirmed seam — NEVER a shallow pass-through whose interface exists only to make internals swappable, and NEVER a test written against an unconfirmed seam.

The deterministic checks that defend it live in `evals/cheap/checks.sh` and run
as part of the marketplace cheap tier.
