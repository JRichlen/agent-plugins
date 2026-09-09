# AGENTS.md — eval-ladder

Design and audit the eval ladder for an agent system: build tiers bottom-up from
observed failures, pick the cheapest rung that can catch a given regression,
name what each rung structurally cannot prove, validate every LLM judge against
human labels (TPR and TNR separately, never raw agreement), and score
irreversible-action scenarios pass^k rather than by majority.

## How to use it

Read `skills/eval-ladder/SKILL.md` and follow it — it is the authoritative
description of this plugin's workflow and the invariant it defends. The command
`commands/eval-ladder.md` is the entry point a user invokes.

The skill is deliberately thin; the weight is in `skills/eval-ladder/references/`,
loaded on demand:

| Reference | Load it when |
|---|---|
| `eval-surfaces.md` | Deciding *what* to grade — output, trace, memory, environment |
| `judge-alignment.md` | Building or trusting an LLM judge, or starting error analysis |
| `metric-choice.md` | Choosing pass@k / pass^k / a floor, or a suite has saturated |
| `integrity-hazards.md` | Auditing a suite that is green and you suspect it is wrong |
| `source-map.md` | A claim is load-bearing and needs checking at the primary source |

## The invariant this plugin defends

Never present an eval result as evidence beyond what its tier structurally proves: every green is reported with its blind spot, every LLM-judge verdict is bounded by that judge's measured TPR/TNR against human labels, and a scenario guarding an irreversible action passes only when EVERY trial passes (pass^k) — never on a k-of-N majority.

The deterministic checks that defend it live in `evals/cheap/checks.sh` and run
as part of the marketplace cheap tier. They are paranoid about three clauses:
that every rung declares what it cannot prove, that judge validation refuses raw
agreement in favour of TPR/TNR, and that the irreversible-action floor stays at
1.0. Wording drift elsewhere is not what that tier catches.

## Relationship to the rest of the marketplace

- **verify-before-claim** governs asserting a fact you have not checked.
  eval-ladder governs the *instrument* that produces such facts: it is what you
  reach for when the thing being over-claimed is a green check.
- **prove-the-undo** rehearses the rollback for one irreversible action.
  eval-ladder is where the rule that such actions are scored pass^k, never by
  majority, is written down.
- **docs-hygiene** catches an instruction file that has gone stale.
  eval-ladder catches a *test tier* that has gone stale — still running, still
  green, no longer capable of failing.
- This repository's own eval architecture is documented in `docs/testing.md`;
  it is the nearest worked example of the ladder, blind spots included.

## Honest limits

This plugin ships no eval runner and no judge. It is an analytical discipline:
it tells you which rung a check belongs on, what a green from it does and does
not license, and which hazards live between rungs. It cannot tell you whether a
specific rubric is well written — only whether you have measured it.
