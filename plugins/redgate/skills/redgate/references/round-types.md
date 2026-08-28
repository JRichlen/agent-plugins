# Round types and their shape criteria

Pick the round type with the **round-zero rule**: start at the first round
whose criteria you can write *without already knowing the answer*. Each type
below gives a criteria template you can copy into `CRITERIA.md`.

The ladder: early rounds check an artifact's **shape** (machine-checkable
even when its content is a judgment call, with the human judging substance at
the gate); later rounds check **behavior**. This is what keeps a research
round honest instead of spending the `WITNESS` budget on "is this good?".

## Scout — the approach is undecided

Judged artifact: a decision brief. Gate class: **always MAJOR** — the approach
steers every round beneath it.

```
## #1 The brief exists at the agreed path
check_cmd: test -f docs/<slug>/decision-brief.md
## #2 It presents at least 3 candidate approaches
check_cmd: test "$(grep -c '^## Option ' docs/<slug>/decision-brief.md)" -ge 3
## #3 Every option carries costs and a "fails if"
check_cmd: [ "$(grep -c '^### Costs' docs/<slug>/decision-brief.md)" = "$(grep -c '^## Option ' docs/<slug>/decision-brief.md)" ]
## #4 It ends in one recommendation naming what would falsify it
check_cmd: grep -q '^## Recommendation' docs/<slug>/decision-brief.md && grep -q 'Falsified if' docs/<slug>/decision-brief.md
```

## Plan — the approach is chosen, the slices are not

Judged artifact: an ordered slice list. Gate class: **always MAJOR** — this
approval *is* the mandate being drawn.

```
## #1 The plan exists and lists ordered slices
check_cmd: grep -qE '^### Slice 1' docs/<slug>/plan.md
## #2 Every slice names a proposed verifier
check_cmd: [ "$(grep -c '^### Slice' docs/<slug>/plan.md)" = "$(grep -c 'check_cmd:' docs/<slug>/plan.md)" ]
## #3 The first slice crosses every layer named in the brief
check_cmd: grep -A6 '^### Slice 1' docs/<slug>/plan.md | grep -qi 'end to end\|every layer'
```

## Build — the criteria are writable today

Judged artifact: working change. Gate class: **PATCH** when strictly derived
from an approved plan slice, verifier green, no escalator.

```
## #1 <the behavior, stated as an observation>
layers: <every layer the slice crosses>
red-because: absent | present-but-wrong
check_cmd: <the test / probe / audit that fails today>
```

One criterion per slice, every named layer touched for real, **no stub at the
seam the slice exists to prove**.

## Widen — the slice widened in place

Judged artifact: the same behavior at more inputs. Gate class: **PATCH**, same
conditions.

```
## #1 The behavior holds at the ambiguous inputs too
check_cmd: <the same test shape, extended cases>
## #2 The failure path is exercised, not just the happy path
check_cmd: <a test that asserts the error branch>
```

## Retro — consolidate the run's lessons (optional, cadence-triggered)

Judged artifact: the run's `gates.log` completed into a lessons ledger. Gate
class: **MINOR** (flagged, standing veto). Runs at most once per run,
normally at close; the shape is checkable, the substance is judged by the
human at the gate — the same shape-vs-behavior ladder as a scout round.

```
## #1 Every gate entry in gates.log carries a non-empty lesson field
check_cmd: ! grep -E '^[0-9]+ \|' .redgate/<slug>/gates.log | grep -vq '\| [^|]+$'
## #2 Every red verdict in the run has a lesson naming what the next contract must encode
check_cmd: <count red JUDGE verdicts; count lessons tagged red:; equal>
## #3 Recurring lesson shapes cite their sightings (recurrence-detector food)
check_cmd: <each lesson appearing twice carries both round numbers>
```

Not every run earns one: a T1 tracer's single gate line IS its retro. The
cadence rule that makes retros recur instead of evaporating lives in the
driver skill.

## The one rule every template shares

Every `check_cmd` must be **red before the work and coupled to the work**:
run it now (it must fail), and after the slice, revert the core hunk and run
it again (it must fail again). A check that survives the revert is
`WITNESS`, not proven — and assert on **exit codes, not messages**: a
grep for a warning string passes even when the gate that should act was
removed.
