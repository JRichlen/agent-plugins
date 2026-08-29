---
id: preference.typescript.tsconfig
kind: behavior
version: 1.0.0
domains: [typescript]
---

# TypeScript: tsconfig

Distilled from Matt Pocock's TSConfig Cheat Sheet
(totaltypescript.com/tsconfig-cheat-sheet); adapted with attribution — his
material is MIT licensed (github.com/mattpocock/skills).

<rule id="strict-plus" strength="must">
Enable strict, noUncheckedIndexedAccess, and noImplicitOverride in every
tsconfig; unchecked index access is a runtime-error class the compiler can
simply remove.
</rule>

<rule id="base-options" strength="should">
Set esModuleInterop, skipLibCheck, target es2022, moduleDetection force,
isolatedModules, and verbatimModuleSyntax (forces import type/export type).
</rule>

<rule id="module-by-role" strength="must">
Use module NodeNext when tsc transpiles; module preserve with noEmit when a
bundler transpiles and TypeScript acts as the linter. Libraries add
declaration; monorepo libraries add composite and declaration maps.
</rule>

<antipattern id="noisy-flags">
Do not add noImplicitReturns, noUnusedLocals, noUnusedParameters, or
noFallthroughCasesInSwitch by default — noise, not safety.
</antipattern>
