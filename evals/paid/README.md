# Behavioral runs and gallery capture

Use existing results before buying another run. These packs exercise bounded
prompts; passing grades and visible differences do not establish general skill
effectiveness. The [testing reference](../../docs/testing.md#behavioral-tier-promptfoo)
owns coverage and the [CI runbook](../../ci/README.md) owns event/cost selection.

## Check capture before spending

From the repository root, with Python, Bash and Git installed:

```sh
python3 evals/paid/preflight_refresh.py --selected 'scope-fence'
bash evals/paid/capture-example.sh --help
```

Preflight validates active paid-pack names, rejects duplicates and paths, checks
the tracked executable mode, and runs the real launcher's help path. It makes
zero model calls. Fix any failure before dispatching the scheduled refresh.

## Capture an existing result

```sh
bash evals/paid/capture-example.sh path/to/results.json scope-fence \
  --pack plugins/scope-fence/evals/promptfoo --out /tmp/capture-review \
  --commit ACTUAL_SOURCE_SHA --captured-at ACTUAL_CAPTURE_TIME \
  --run-url https://github.com/OWNER/REPO/actions/runs/RUN_ID
```

Use the config from that source revision, not a newer pack. The tool selects a
passing real-skill row and a nonempty, nonfaulted calibration row for the same
question and subject provider. It refuses undisclosed or same-family grading.
No usable pair leaves the previous snapshot unchanged. Inspect the copied
outputs and grades before publication; a pair where both pass is useful
negative evidence about discrimination, not proof of improvement.

The capture time is when capture happened, never an invented evaluation time.
Do not pass `--attestation github` locally: only the workflow that actually
signs those bytes may promise its attestation. If recovering a failed run whose
capture time or signature is absent, disclose that absence and preserve the
original artifact/source identity instead of manufacturing provenance.

The refresh workflow preserves raw results even when later steps fail and
attests only snapshots written by that run. A zero-capture run fails. A reviewed
gallery change merges separately from evaluation execution; no script here
authorizes a paid run or a merge.
