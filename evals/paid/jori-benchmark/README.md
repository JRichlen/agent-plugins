# Jori benchmark — cost to complete an activity, with and without the plugin

**Question it answers.** Does loading the `jori` coordination plugin change what it
costs, in harness-reported dollars, to complete one bounded activity to a verified
outcome — on the same model, with the same tools, in the same harness?

**What it is not.** One activity, textual verification, a single harness (Claude Code
headless). A verdict here is evidence about *this activity on this model*, not a general
statement that Jori saves or wastes money.

## Design

| | baseline arm | jori arm |
|---|---|---|
| prompt | `tasks/<id>/prompt.md` verbatim | `/jori ` + the same text |
| plugin | none | `--plugin-dir plugins/jori` |
| tools | `Bash,Read,Edit,Write,MultiEdit,Glob,Grep,Agent,Skill,TodoWrite` | identical |
| permission mode, model, budget cap, working dir | identical | identical |

Exposure parity: both arms can delegate (`Agent` is allowed in both); the only difference
is Jori's coordination guidance. A correct direct baseline is allowed to win.

Each attempt is one fresh GitHub runner and one `claude -p … --output-format stream-json`
run in a `mktemp -d` workspace staged by `tasks/<id>/setup.sh`. `run-arm.sh` records, per
attempt: `total_cost_usd`, `usage`, `num_turns`, `duration_ms` (from the harness's own
`result` record — never reconstructed), the realized model(s) seen on the stream, the
installed Claude Code version, tool-use counts, adoption signals (was the jori skill
invoked, how many subagents were delegated), and the deterministic outcome from
`tasks/<id>/verify.sh`. A field the harness did not report is the string `UNKNOWN`, never
`0`.

`aggregate.py` counts **every** attempt (errors, over-budget stops and verifier failures
included), excludes UNKNOWN-cost attempts from cost means while still counting them and
saying so, refuses a verdict unless both arms ran on the same realized model with at least
two known-cost attempts each, and reports the 95% bootstrap CI of the mean-cost
difference: `jori cheaper` only when the whole interval is below zero. Cost per accepted
outcome is `unavailable` for an arm with zero successes. A cheaper arm with a lower success
rate is flagged, not celebrated.

## Running

Dispatch `.github/workflows/jori-benchmark.yml` (Actions → jori benchmark → Run workflow).
Inputs: task, repeats per arm, model, per-attempt budget cap, Claude Code version. The
verdict lands in the run's step summary and in the `jori-benchmark-report` artifact.

Locally, without spending anything:

```sh
bash evals/paid/jori-benchmark/self-test.sh        # verifier two-sided, dry-run plumbing, verdict logic
```

Locally, spending (needs `ANTHROPIC_API_KEY` or a signed-in `claude`; each call is a real
paid run and, in this repo, needs the same approval as any paid benchmark):

```sh
for i in 1 2 3; do for arm in jori baseline; do
  bash evals/paid/jori-benchmark/run-arm.sh --arm $arm --task multi-module-fix --repeat $i --out /tmp/jb --model claude-sonnet-5 --budget 2.00 --live
done; done
python3 evals/paid/jori-benchmark/aggregate.py --results /tmp/jb --out /tmp/jb/report
```

## Adding an activity

`tasks/<id>/` needs `prompt.md`, `setup.sh <ws>` (stage a fresh fixture), `verify.sh <ws>`
(exit 0 iff the user outcome holds; must fail on the untouched fixture and on a
reward-hack such as editing the tests) and `oracle.sh <ws>` (apply the known-good change
with no model, so `self-test.sh` can prove the verifier is able to pass). Prefer
activities with several independent parts — that is where coordination could plausibly
pay for itself, and where its overhead is also visible.

## Known limits

- `total_cost_usd` is whatever the installed Claude Code reports for the session; whether
  subagent spend is included is a harness property, recorded by version, not assumed.
- Subscription-authenticated local runs may report cost differently from API-key runs;
  the workflow uses the API key so the number is a real billed amount.
- One activity cannot separate "Jori's guidance" from "any structured guidance of similar
  length"; a placebo arm is a reasonable next step and is deliberately not claimed here.
