# Card authoring guide (registry lane)

This directory holds the reference corpus: one subdirectory per plugin
(`tasks/<plugin>/`), each containing one subdirectory per card
(`tasks/<plugin>/<card_id>/`). `framework.validate.load_cards()` walks this
tree looking for `card.json` files; there is no separate registration step.

Read `agent-plugins-implementation-contract.md` §2.3 (`Card`), §3.10
(`validate.py`), §7 (suite catalog) before adding a card. This file is the
concrete "how", not a restatement of the contract.

## Directory layout (exact)

```
tasks/<plugin>/<card_id>/
  card.json           # validates against schemas/card.schema.json
  task/                # what the agent starts from -- files in a workspace
    ...
  fixtures/
    pass/              # a workspace state that MUST be decisive=True (see below)
    fail/              # a workspace state that MUST be decisive=False
    near-fail/         # near-miss cards ONLY -- see "Near-miss cards" below
```

`card_id` MUST follow `<plugin>-{pos,neg,near}-<NN>` (e.g. `graveyard-pos-01`).
This is not decoration: `framework.reporting._plugin_of_card` derives the
plugin name from this exact convention when a `Card` object isn't in hand.

## The two verifiers

`card.json`'s `outcome_verifier` and `adoption_verifier` are both
**repo-relative paths to an executable Python script**, never
`module:function` (that form is `controls.py`'s own, for its two built-in
toy scenarios only -- see `controls._resolve_verifier`'s docstring). Each
script:

- takes exactly one positional argument: a workspace directory path;
- reads the required `AGENTIC_CARD_ID` environment variable naming the
  card being graded (see "Card binding" below);
- prints exactly one line of JSON to stdout: `{"passed": <bool>, "reason": <str>}`;
- exits `0` when `passed` is `true`, `1` when `passed` is `false`.

`outcome_verifier` answers "did the user's actual task get done?".
`adoption_verifier` answers "was the plugin's ritual performed?" -- these are
independent booleans, checked independently, feeding the reporting lane's
2x2 outcome/adoption matrix. **Never make one verifier call the other, and
never make them byte-identical** -- `validate.validate_card` raises
`VacuousVerifier` for both (contract §3.10): with one verifier serving both
columns, `ritual_without_outcome` and `outcome_without_ritual` are both zero
by construction, which is "the central vacuity risk in the corpus"
(benchmark-spec §5) rendered permanently undetectable.

### Card binding (CV-01/CV-02/CV-03/CV-04 repair)

Earlier revisions of the shared verifiers below trusted whatever bytes they
found at `<workspace>/guard.sh` / `<workspace>/events.jsonl` -- since those
files live inside the very tree being graded, the grading criterion
travelled with the artifact: any workspace could forge a trivially-true
`guard.sh` (or copy a DIFFERENT card's entire pass fixture) and pass, and a
correct direct solution that (correctly) never heard of `guard.sh` failed
for a reason unrelated to its actual task. Both scripts now require the
caller to set `AGENTIC_CARD_ID=<card_id>` and resolve the real check/digest
from **this repo's own committed `fixtures/pass/guard.sh` for that specific
card_id** -- never from the workspace being graded. `test_corpus.py`'s
`run_verifier()` sets this for every corpus self-test call.

Concretely, `verify_outcome.py` copies the subject workspace into a
throwaway temp dir (the real workspace and the repo's fixtures are never
written to), seeds it with whatever files are byte-identical across this
card's own `fixtures/{pass,fail[,near-fail]}` (the harness-owned grading
scaffolding -- e.g. `guard.sh` itself, or a helper like `check.sh` --
proven empirically to be identical across every fixture variant for all 75
corpus cards today, since a genuine task deliverable necessarily *differs*
between a passing and a failing fixture or the two would be
indistinguishable), and only then executes the one card's canonical
`# GUARD_CHECK` line there. A card author does not create or maintain any
per-card "which files are scaffolding" list -- it is derived structurally
from the fixtures already required by the schema.

### The shared generic verifier pair

Every reference card in this delivery points `outcome_verifier`/
`adoption_verifier` at the SAME two shared scripts:

```
evals/agentic/tasks/_verifiers/verify_outcome.py
evals/agentic/tasks/_verifiers/verify_adoption.py
```

These are generic, not decorative -- the verdict is never decidable from the
card's own metadata, only from executing real, per-fixture content:

- **`verify_outcome.py <workspace>`** resolves `AGENTIC_CARD_ID`'s
  `fixtures/pass/guard.sh` and requires it to carry exactly one line ending
  in the trailing comment `# GUARD_CHECK`. That line IS the real,
  task-specific correctness check (it differs completely between plugins
  and between cards). The script fails closed if the marker line is
  missing (`controls.MUTATIONS["delete-guard-line"]`) or commented out
  (`controls.MUTATIONS["comment-out-check"]`); otherwise it executes the
  marker line as a bash command with `cwd=<a seeded copy of the workspace>`
  and `AGENTIC_REPO_ROOT` set to the repo root, and reports its exit code.
- **`verify_adoption.py <workspace>`** reads `<workspace>/events.jsonl` for
  a `{"op":"backup","digest":<sha256>}` event whose digest matches the REAL
  sha256 of `AGENTIC_CARD_ID`'s canonical `fixtures/pass/guard.sh` bytes,
  strictly preceding a `{"op":"delete"}` event. Falsified by
  `controls.MUTATIONS["corrupt-pinned-hash"]` (wrong digest) and
  `controls.MUTATIONS["reorder-backup-after-delete"]` (order reversed). A
  workspace with no `events.jsonl` at all fails closed (`passed: false`),
  not vacuously -- this is exactly what a correct oracle-direct solution to
  a NEGATIVE card's task looks like (the ritual never started).

A new card does **not** have to reuse these two scripts -- point
`outcome_verifier`/`adoption_verifier` at your own real, executable scripts
if the generic `guard.sh`/`events.jsonl` convention doesn't fit your
plugin's invariant. If you do reuse them, your fixtures need a `guard.sh`
(with the trailing `# GUARD_CHECK` marker on its one real check line,
byte-identical across `pass`/`fail`[/`near-fail`] since it is grading
apparatus, not the deliverable) and, where the ritual is meant to have
fired, an `events.jsonl` whose `backup` event's digest is
`sha256(fixtures/pass/guard.sh's bytes)`.

### Known residual gap (CV-03)

`events.jsonl`'s `backup`/`delete` convention is not derived from any
observable trace of a real plugin invocation -- it is a fixture-authored
stand-in, identical in shape for all 25 plugins regardless of whether that
plugin's own ritual is destructive at all. This repair closed the specific
forgeability of the digest it checks (CV-03's reproduction: a workspace
hashing its own forged `guard.sh` no longer self-validates), but did not
replace the convention with a genuine per-plugin trace signal -- that
requires plugin-specific engineering (e.g. wrapping each plugin's own
hook/script output) outside this pass's bounded scope. Concretely: a
positive card whose task explicitly forbids actually performing the risky
step in-session (e.g. graveyard-pos-01's "do not delete anything
yourself") can never legitimately satisfy `adoption` under the current
convention, even with a byte-perfect `outcome`. Treat `adoption` as
measuring "did the workspace carry a correctly-pinned backup/delete
ledger", not yet "did the plugin's real ritual fire".

### `mutations`

List every `controls.MUTATIONS` name (contract §3.4: `delete-guard-line`,
`reorder-backup-after-delete`, `blank-criteria`, `corrupt-pinned-hash`,
`comment-out-check`, `truncate-manifest`) that meaningfully applies to your
fixture layout. `validate.validate_card` rejects any name not in
`controls.MUTATIONS`; `mutations` must be non-empty for every card kind.

## Card-kind "decisiveness" (registry's reading, in `test_corpus.py`)

`Card` exposes only `outcome_verifier`/`adoption_verifier` -- there is no
separate "decisive" field. `test_corpus.py`'s `decisive(card, outcome,
adoption)` is registry's own, documented interpretation:

| Kind | decisive = |
|---|---|
| `positive` | `outcome AND adoption` (task done, ritual used) |
| `negative` | `outcome AND (NOT adoption)` (task done, ritual absent) |
| `near-miss` | `outcome` (the outcome_verifier directly encodes the boundary check) |

`fixtures/pass/` must be `decisive=True`; `fixtures/fail/` must be
`decisive=False`. Both verifiers are always run against both fixtures (T15);
which one is "the" decisive check for a given kind is this table, not a
frozen contract field.

## Near-miss cards

A near-miss card additionally ships a **third** fixture,
`fixtures/near-fail/`, alongside the schema-required `pass`/`fail` pair.
`fixtures/fail/` and `fixtures/near-fail/` are the two ADJACENT wrong
behaviors T14 requires (one "over-triggers", one "under-triggers" relative
to the boundary) -- both must be `decisive=False`, and only `fixtures/pass/`
(the boundary-CORRECT behavior) is `decisive=True`. `near-fail/` is not a
`Card` schema field (the schema only has `pass_fixture`/`fail_fixture`); it
is a directory-naming convention `test_corpus.py`'s `NearMissDiscrimination`
test looks for directly (`card.pass_fixture`'s parent `/ "near-fail"`).

`expected_boundary_verdict` must be a short, non-empty string naming what the
boundary-correct behavior actually is (not empty, not "positive" or
"negative" — see the four reference near-miss cards for examples such as
`archive-fork-with-unique-commits` or `decline-not-simulate`).

## Holdout, leakage, strata (T18)

- Set `"holdout": true` on a card to exclude it from the dev-loop's visible
  set; `validate.holdout_ids()` / `validate.assert_holdout_unread()` enforce
  that a run manifest's `planned_n` never names a holdout card id. All four
  reference near-miss cards (`*-near-01`) are holdout in this delivery.
- Never let your task fixture's prose or your verifier's literal expected
  strings appear verbatim (>=8 tokens) in the plugin's own `SKILL.md` or
  command markdown -- `validate.scan_leakage()` / `assert_no_leakage()`
  catch this; `test_registry.py::SamplingIntegrity` runs it against the real
  corpus and real plugin surfaces on every test run.
- Strata (`provider|model|revision|effort|harness`) are an execution-time
  concern (`contract.Stratum`, `pairing.assign_stratum` once part 2 lands),
  not something a card author sets.

## Running the validator

```sh
python3 -m evals.agentic.framework.validate --corpus          # human-readable
python3 -m evals.agentic.framework.validate --corpus --json   # coverage.schema.json document
```

Prints `roster_size` (always 25, live-derived), `total_cards`, `complete`,
`measured_plugins` (plugins with `>= 8` cards -- the measurement floor,
distinct from the `>= 1 per kind` coverage floor -- benchmark-spec §6.0),
and the list of plugins still missing at least one card kind. Exits non-zero
on any schema/resolution failure (a card whose `task_path`, `pass_fixture`,
`fail_fixture`, or verifier path does not resolve; a vacuous verifier pair;
an unknown mutation name).

Run the actual tests before committing a new card:

```sh
python3 -m unittest discover -s evals/agentic/tests -t . -p 'test_registry.py' -v
python3 -m unittest discover -s evals/agentic/tests -t . -p 'test_corpus.py' -v
```

`test_corpus.py` discovers cards dynamically (`validate.load_cards()`), so a
new, correctly-shaped card is exercised automatically -- there is no
per-card test to add by hand, only the fixtures and verifiers above.

## Current corpus (CV-15: updated for the complete delivery)

The corpus is complete: all 25 roster plugins carry all three card kinds
(positive/negative/near-miss), 75 cards total. `python3 -m
evals.agentic.framework.validate --corpus` reports `total_cards=75
complete=True` and `TripletCompleteness`'s roster-wide completeness
assertion (`assert_triplet_completeness`) does NOT raise -- there is no
missing plugin/kind cell left. `graveyard`, `redgate`, `voice`, `jori` remain
the four *reference* plugins other tests anchor to by name (their cards were
authored first and are used as named examples elsewhere in this repo), not
the only plugins with cards.

`evals/agentic/run.sh` exists and drives this corpus end to end (offline,
`--gate` included); nothing here is "inert pending integration" any more.

Every corpus fixture's `outcome_verifier`/`adoption_verifier` binds to the
specific `card_id` being graded (CV-01/CV-04), so a donor fixture copied
verbatim into a different card's directory fails that card's verifiers. A
smaller number of fixtures (currently just `stop-rule`'s three cards, this
delivery's one worked plugin for CV-04's second half) additionally carry a
committed `evidence/manifest.json`, generated by
`tasks/_verifiers/generate_evidence_manifest.py` and checked by
`validate_card` via `framework.controls.assert_fixture_evidence_current` --
see that generator's docstring and `known-gaps.md` for which cards still
lack one and what closes the remainder.
