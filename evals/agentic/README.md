# `evals/agentic/` — the marketplace-wide agentic test framework

Full narrative documentation lives in
[`docs/testing.md`](../../docs/testing.md#agentic-suite); this file is a
quick orientation for anyone opening this directory directly.

## What this is

The backlog `T01`–`T52` (see `agent-plugins-test-backlog.md` in the design
reports) is a fail-closed suite catalog mapping every item to a real,
executing, falsifiable assertion — not a metadata table. Seven lanes:

| Lane | IDs | Owns |
|---|---|---:|
| core | T01–T10 | `framework/{contract,io,classify,controls}.py` |
| registry | T11–T18 | `framework/{registry,validate,pairing}.py`, `manifests/arms/**`, `tasks/**` |
| protocol | T19–T24 | `framework/protocols.py`, real hook/MCP/subprocess fixtures |
| adapter | T25–T31 | `framework/adapters.py`, native CLI driver + host ledger |
| measurement | T32–T41 | `framework/{accounting,analysis,reporting}.py` |
| redteam | T42–T48 | `evals/redteam/**` (a separate top-level eval dir) |
| integration | T49–T52 | this README, `run.py`, `run.sh`, the catalog `index.json`, and every SHARED file the ownership map (contract §6) lists |

## Running it

```sh
evals/agentic/run.sh                 # full offline suite + catalog + run manifest
evals/agentic/run.sh --offline       # same, explicit
evals/agentic/run.sh --gate          # root-portable subset (contract §9.3), terse, no manifest
evals/agentic/run.py --catalog       # the 52-ID fail-closed catalog walk
evals/agentic/run.py --id T07        # one catalog entry
evals/agentic/run.py --lane core     # one lane's catalog entries
evals/agentic/run.py coverage --json # registry.coverage_document
evals/agentic/run.py driver --dry-run --name claude   # plan a real invocation, spawn nothing
evals/agentic/run.py plan            # the dispatch plan: cells x arms x repeats
evals/agentic/run.py plan --json     # ... with every planned attempt and its paraphrase
evals/agentic/run.py report --manifest <m.json> --attempts-dir <dir> \
    [--event-ledger <events.jsonl>]  # build + render a Report from real records
python3 -m unittest discover -s evals/agentic/tests -t .   # everything, every lane
```

No flag anywhere spawns a model. `driver --spawn --approval-token <tok>`
exists and always raises `ApprovalRequired` today (contract §10.6) — no
approved native-harness capture has landed, so there is no wired path from
`--spawn` to an actual process.

`driver --dry-run` validates the driver's flags against the **installed**
binary's own `--help` before it renders anything, and refuses (non-zero, with
`agentic FAIL adapter:`) rather than printing an unvalidated argv. It is the
one place the runner spawns a child on the offline path, and the only child it
spawns is `<binary> <help_argv>`.

### `plan` — what the run intends to dispatch

`plan` enumerates **cells × arms × repeats** — one cell per corpus card, the
two arms from that plugin's committed `manifests/arms/<plugin>.json`, and
`REPEATS_PER_CELL_ARM` (tied to `MIN_VALID`) repeats each. Two things depend
on it:

* `Manifest.planned_n` is populated from it, so
  `accounting.assert_planned_reconciles` has something declared *outside* the
  attempt ledger to compare against. `conserve()` and
  `Denominators.assert_reconciles()` re-derive their comparison from the very
  list they check, so neither can see a row dropped before the ledger held it.
* every planned attempt on a **holdout** card is assigned one of that card's
  `paraphrases` (a `card.json` field, not the agent-visible task file),
  selected deterministically from the run seed and recorded on the attempt as
  `paraphrase=<i>/<n> digest=<16 hex>`. Same seed, same assignment, any host.

An `--offline` run writes the plan alongside its manifest and declares in
`Manifest.skipped` that it dispatched none of it.

`report --event-ledger` reconciles the event ledger's `SPAWN` entries against
the attempt records and refuses a report in which an attempt was spawned and
never recorded.

## Six items are approval-gated, not "failed"

`T26`–`T29` (native-required: a real `claude`/`codex` multi-turn session) and
`T45`–`T46` (paid-required: a real subject-model pass over the red-team
controls) print `BLOCKED — approval required` from `run.py --catalog` and are
never counted toward "executed". Their offline forms exist, execute, and are
named `*__offline_form` so no reader mistakes an offline pass for native
proof. Obtaining an approval token is a human action outside this codebase.

## Directory layout

See contract §1 for the exact frozen tree. In short: `framework/` is the
importable package (`from evals.agentic.framework import <module>` — the
package `__init__.py` re-exports only `contract.py`'s vocabulary, so no lane
needs every other lane's module to exist before its own tests can run);
`schemas/` holds the JSON Schemas; `manifests/catalog/<lane>.json` plus
`index.json` are the suite catalog fragments (contract §7); `manifests/arms/`
are the precomputed per-plugin arm manifests; `tasks/<plugin>/<card>/` are the
task fixtures and verifiers; `fixtures/` holds each lane's own test fixtures;
`tests/` holds every `test_*.py` module the catalog resolves into.

`evals/agentic/manifests/runs/` is generated (gitignored) — one JSON manifest
per `run.py --offline` invocation, validated against
`schemas/run-manifest.schema.json` before it is written, plus the matching
`<run_id>-plan.json` dispatch plan.

## Every catalog entry's negative control is *bound* to its sibling

`--catalog` used to check two independent facts: that
`entry.negative_control` resolves to a path on disk, and that a
`<test>__negative` method exists. Both can be true while naming unrelated
things, so an entry's `negative_control` could be re-pointed at an unrelated
artifact — even a *positive* fixture — with every gate still green.

It now also has to be the **same** control. An entry is bound when its sibling
(or the module hosting it) declares, constructs, or names that exact path;
otherwise `--catalog` prints `agentic FAIL catalog: <ID> negative control not
bound`. The strongest form is a `negative_control = "<path>"` attribute on the
test class, which is checked exactly and in both directions — the adapter and
integration lanes' entries carry one. See `known-gaps.md` for what these
source-reference bindings still cannot prove.
