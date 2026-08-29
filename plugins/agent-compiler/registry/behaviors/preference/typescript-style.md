---
id: preference.typescript.style
kind: behavior
version: 1.0.0
domains: [typescript]
---

# TypeScript: style

Distilled from Matt Pocock's Total TypeScript articles (type-vs-interface,
any-considered-harmful, why-i-dont-like-typescript-enums); MIT-licensed
skill material adapted with attribution.

<rule id="type-over-interface" strength="should">
Default to type aliases; reach for interface only when you need extends —
interfaces cannot express unions or mapped/conditional types, and declaration
merging surprises.
</rule>

<rule id="no-enums" strength="should">
Avoid TypeScript enum; use as-const objects or literal unions — erasable,
what-you-see-is-what-you-get syntax.
</rule>

<rule id="unknown-not-any" strength="must">
Never use any in application code — it disables checking, autocomplete, and
safety; unknown is the safe wide type. The exception is advanced generic
positions (constraints like T extends (...args: any[]) => any) where the wide
type is deliberate.
</rule>

<rule id="type-errors-as-unknown" strength="should">
Type caught errors as unknown and narrow; for expected failures return a
discriminated-union result instead of relying on untyped throws.
</rule>
