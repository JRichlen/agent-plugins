# The five gradable surfaces

An agent run exposes five surfaces you can grade. Most suites grade only the
first, which is the weakest one.

| Surface | What it is | Typical grader | Weakness |
|---|---|---|---|
| **Output** | The final text the agent emitted | string match, LLM judge | The agent can *say* it did the thing |
| **Trace** | The tool calls: which, in what order, with what args | reference match, judge, contract validator | Credits one path; misses whether it worked |
| **Memory** | What carried across turns/sessions — notes, state files, context | artifact audit, schema check | Rarely instrumented at all |
| **Environment** | The world after the run: rows, files, repos, API state | before/after diff | Needs isolation and a golden state |
| **Mechanistic** | Internals — activations, attention, confidence | probes | Rarely available or actionable in product work |

## Grade the surface closest to the harm

The canonical failure: an agent replies "your flight has been booked" and no
reservation row exists. Grading the output passes; grading the environment
fails. If your system's harm is a wrong side-effect, grading the transcript is
grading the press release.

Order of preference when the harm is a state change: **environment > trace >
output**. Order of preference when the harm is what the user is *told*: output,
but assert on the specific claim, not on general quality.

## Environment-state grading, done properly

1. **Snapshot before and after.** Never infer the state from the transcript.
2. **Build the golden end-state by replaying the reference solution** on a fresh
   copy of the seed data — not by hand-writing it. Then any different-but-valid
   path that lands on the same state still scores.
3. **Assert both directions.** All expected changes happened, AND no unexpected
   changes happened. The second half is the one everyone omits, and it is the
   half that catches collateral damage: a verifier that checks "alpha and beta
   were deleted, gamma was not" passes an agent that also deleted four unrelated
   things. Bound the whole scope, not the named items.
4. **Isolate trials.** Every run starts from a clean world, or leftover state
   from case 3 silently decides case 4.
5. **Normalize volatile fields** (timestamps, autoincrement ids) before hashing,
   or assert on specific rows instead of hashing the whole store.
6. **Partial credit for analysis, all-or-nothing for the gate.** Report the
   fraction of checks passed to debug with; gate on the strict bar.

## Trajectory grading has two biases, in opposite directions

- **Rule-based reference match under-reports.** It penalizes valid alternative
  paths and non-exact outputs; measured false-negative rates around 44%. Loosen
  ordering deliberately (`strict` → `unordered`/`subset` for independent calls)
  and grade only the load-bearing arguments.
- **LLM-judge-of-trajectory over-credits.** No judge measured above ~70%
  precision; roughly 30% of real failures pass.

Neither is safe alone for open-ended tasks. Where a state check is possible,
prefer it — it is path-agnostic by construction. Where it is not, treat a failing
rule-based match as a *candidate* failure routed to a judge or a human, and
track your grader's own precision and recall against a small labeled set.

## The trap of the frozen decision point

Freezing a fabricated mid-run prefix and grading the single next move is cheap,
deterministic, and genuinely useful — it is the only way to test a decision that
a full run reaches rarely. But it grades a decision in a context you wrote. It
cannot tell you the agent would ever *reach* that context, and a suite made
entirely of frozen prefixes has never observed the system it grades. Pair it
with at least one end-to-end rung.
