# Grader calibration — a human in the grading loop

Issue #102. Every behavioral verdict in this repo is one language model's
opinion of another's output. These two scripts measure how much that opinion
is worth, and they need no API key to run.

## Procedure (measurement 2: human vs grader)

1. Take a real `results.json` from a behavioral run (a CI artifact, or a
   local `npx promptfoo eval --output results.json`).
2. `sample-for-labelling.py results.json --n 20` writes `sheet.json` (blind:
   scenario, request, output, empty label) and `verdicts.json` (the grader's
   pass/fail per sample, keyed by a hash of scenario plus output so the same
   answer under two rubrics is two samples). Do not open `verdicts.json` until step 4.
3. Label every row in `sheet.json` as `"pass"` or `"fail"` against the pack's
   rubric text, the same text the grader sees.
4. `agreement.py sheet.json verdicts.json --name-a human --name-b grader`
   prints percent agreement, Cohen's kappa, the confusion matrix, and every
   disagreement with its scenario.

Commit the filled sheet and the report next to the pack they came from as
`calibration/<date>.sheet.json` and `calibration/<date>.report.json`, and
record the kappa on #102 with the run number. The threshold for promoting any
grader-dependent tier is chosen after the first measurement, not before.

## The same procedure from CI

The `calibration sheet` workflow (manual dispatch: `run_id`, `packs`, `n`)
downloads a finished run's results artifact on the runner, draws the sheet
with the script above, seals the verdicts as base64 (`<run>.verdicts.b64`) so
they are not read by accident, and pushes both to a `calibration/<run-id>`
branch under `plugins/<pack>/evals/promptfoo/calibration/`. Open a pull
request from that branch, fill the `label` fields in the sheet, and run
`agreement.py <run>.sheet.json <run>.verdicts.b64 --name-a human --name-b grader`.
No model is called; the workflow never becomes a required check.

## Grader vs grader, grader vs itself (measurement 3)

Grade the same cached outputs with a second grader (a different model family)
or with the same grader again, and feed the two `verdicts.json` files to
`agreement.py`. Self-agreement is the label-noise floor: if it sits below the
pass-rate floor, two of three cannot separate a skill effect from grader
noise, and the repeat count has to rise before the floor means anything.

## What these scripts cannot do

They do not make a human's labels correct, and twenty rows is a small sample;
kappa's confidence interval at n=20 is wide. They turn "AI grades AI" from an
unanswered objection into a number with a stated sample size.
