---
id: preference.typescript.stack
kind: behavior
version: 1.0.0
domains: [typescript]
---

# TypeScript: stack

Owner-selected defaults for TypeScript/Node work, informed by Matt Pocock's
tooling (his monorepos use pnpm workspaces and Vitest; his own skills repo
pins npm — treat the package-manager lean as preference, not doctrine) and
zod.dev (v4 is the current stable major).

<rule id="validate-untrusted-with-zod" strength="must">
Validate untrusted input — API responses, environment variables — with Zod
at the boundary, then rely on the inferred types inward.
</rule>

<rule id="vitest-for-tests" strength="should">
Prefer Vitest for new TypeScript test suites.
</rule>

<rule id="pnpm-for-workspaces" strength="should">
Prefer pnpm for new repos and workspaces; respect whatever lockfile an
existing repo already has.
</rule>
