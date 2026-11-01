# Read and maintain the example gallery

The [gallery](https://jrichlen.github.io/agent-plugins/examples/) lets readers
inspect paired outputs and their provenance. It is not a leaderboard or proof
of general effectiveness. Counts are computed from committed data in the page;
there is no separate hand-maintained phase/count table.

| Label | Evidence | Limit |
|---|---|---|
| Seed, ungraded | Earlier session output and its recorded provenance | No rubric grade or CI snapshot signature; same-family judgments are disclosed |
| CI-graded | Paired nonfaulted rows from one result file, same question and subject | A pass is the pack grader's call, not a controlled general-outcome result |
| Recovered, unattested | Retained CI rows with raw-file hash, indices/IDs, original source/run and config hash | Original capture time unknown; offline recovery created no original-run snapshot signature |
| CI-graded, attested | Snapshot bytes bound to a signing workflow run | Signature establishes production of bytes, not their truth or benefit |

Strong/stark badges describe difference, not quality. Each arm can have a different criterion: in the five recovered pairs the
calibration rubric rewards behavior opposite to the real invariant. Both passes
mean both respective criteria were met, not equal behavior or equal quality. Single examples are selected outputs,
not randomized independent trials. Human calibration and broad task-outcome
evidence remain missing; see [testing](../testing.md#not-yet-covered-by-current-evidence).

## Capture and recover

The [capture tool and procedure](../../evals/paid/README.md) own pair eligibility.
The [CI runbook](../../ci/README.md#gallery-refresh-recovery) owns event/cost and
failure handling. A missing usable pair leaves the previous snapshot intact;
zero captures fails the scheduled refresh.

To recover an already downloaded failed-run artifact without model calls, from
the repository root with Python, Git and Bash:

```sh
python3 evals/paid/recover_examples.py --inputs /path/to/downloaded-results \
  --output /tmp/recovered-gallery --source-commit FULL_ORIGINAL_SHA \
  --run-id ORIGINAL_RUN_ID --artifact-id ORIGINAL_ARTIFACT_ID \
  --recovered-at ACTUAL_RECOVERY_TIME_UTC
```

Use a new output directory. The tool reads each active plugin's grader config
from the original Git commit and reuses the capture selector. It records result
hashes and row identities, uses `captured_at: unknown`, and does not claim
attestation. Inspect outputs for private data and misleading claims, compare
them to the original artifact, then review selected snapshots before copying
them into `data/`. Do not rerun paid packs just to repair capture or rendering.

The recorded recovery used run
[41280016961](https://github.com/JRichlen/agent-plugins/actions/runs/41280016961),
artifact `13073393801`, source `2ff596caf3be9fd59ebfe42d17b05ccab1f1da1d`.
No new model calls were made. Retired plugins were excluded; eligible active
pairs retained their original grades, including passing opposite-behavior calibration controls. The stop-rule
control also omits the declared attempt bound present in the real arm; skill
injection is therefore not the sole changed input. Per-arm criteria, context
and original config links are shown in the gallery. The raw
recorded text is preserved, including any source encoding defects.

## Change the presentation

Edit `docs/build-examples.sh`, never generated `index.html`. Source snapshots
live in `data/`; navigation/styles live in `docs/_shared/sitenav.py`. From the
repository root:

```sh
bash docs/build-examples.sh
bash docs/build-index.sh
bash docs/build-examples.sh --check
bash docs/build-index.sh --check
python3 ci/check_docs.py
```

Keep the static page usable without JavaScript: anchored cards, verbatim prompt
and full outputs behind optional detail, model roles and evidence links at each
card. Filters add convenience. Narrow screens stack transcripts. Difference
labels always include text, not color alone. Inspect rendered wide/narrow output
as well as deterministic sync. Pages publishes only through the existing merge
workflow; editing a snapshot does not authorize deployment.

Recovery writes `recovery-receipt.json` incrementally in the output directory, including captured, skipped and failed packs. A partial failure returns nonzero while preserving successful labelled snapshots and the receipt; inspect it before retrying in a new directory. Schema checks validate identities and field types, not remote authenticity. On Windows the helper selects Git Bash; `TEST_BASH` can explicitly select another supported Bash.
