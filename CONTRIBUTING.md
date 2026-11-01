# Contributing

Choose the smallest change that solves the problem. Keep its instructions beside
its owning code, and link outward when another component owns the rule.

| Change | Edit the source | Start with |
|---|---|---|
| Plugin behavior | `plugins/<name>/skills/` and its actual command/host adapters | Plugin README, [Core](core/OPERATING.md), relevant eval pack |
| Plugin usage | `plugins/<name>/README.md` | A runnable task and its limits |
| Generated catalog or gallery | The owning `docs/build-*.sh` and source data | [Gallery source](docs/build-examples.sh) |
| Tests or CI | `evals/` or `ci/`, workflow only for orchestration | [Eval selection](evals/README.md), [CI runbook](ci/README.md) |
| Installation metadata | Plugin manifest and marketplace entries | [Plugin factory](plugins/plugin-factory/README.md) |

## Before opening a PR

1. Read `AGENTS.md` and the instructions nearest the changed source. Preserve
   unrelated work. Check marketplace conflicts entry by entry; never blindly
   keep both copies of a registration.
2. Run `bash evals/cheap/run.sh` from the repository root on a qualified host.
   Use [evals/README.md](evals/README.md) to select additional checks. Report the
   host and actual failures; a skipped or unavailable check is not a pass.
3. If you change a tier, job or pack, update the authoritative
   [testing inventory](docs/testing.md) in the same PR. Regenerate derived files
   from their source rather than hand-editing them.
4. For a skill change, demonstrate the actual skill on pre-existing input:
   source, output, responsible rule and misses. Attribute who ran it. A source
   test or a demonstration does not establish causal effectiveness.
5. Open a focused draft with the problem, resulting behavior, relevant rationale,
   verification and remaining limits. Put working history in commits and PR
   discussion, not permanent duplicate plans.

PR checks run free coverage plus bounded reachability probes when secrets are
available. Paid subject legs need the existing same-repo `paid-evals` label;
main can run selected legs automatically. Forks cannot access these secrets.
Green aggregates may represent skips. A maintainer must decide whether additional
behavioral evidence is needed and authorize its cost; do not manually run paid
suites or move untrusted code into a secrets-bearing context to obtain a badge.

## Reconcile marketplace changes

Resolve `.claude-plugin/marketplace.json` by registration identity, not by
keeping both sides of a conflict. Follow the
[entry-by-entry recovery procedure](plugins/plugin-factory/README.md#reconcile-marketplace-changes)
and run its checks. Coordinate published stack changes before any rebase or
history rewrite.

## Working in a PR stack

Create a linear dependency chain and keep each PR's base on the previous layer.
Link drafts into a native GitHub stack, then verify remote membership, bases,
heads and focused diffs. Review and merge from the bottom when approved.
The [CI runbook](ci/README.md#working-in-a-pr-stack) covers safe operations and
links the official commands. Do not treat `gh stack sync` as read-only or rewrite
shared branches without permission.

## Review standard

A reader should know what to do next without reading the architecture first.
Keep commands reproducible, links purposeful, costs and permission boundaries
visible, and claims bounded by current evidence. Use a diagram or table when it
clarifies a real choice. Do not claim all hosts behave alike because their files
parse, or that a visible model-output difference proves improvement.
