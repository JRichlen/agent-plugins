# Task

Add a small `retry(fn, times)` helper that will be called from exactly two places inside `jobs/worker.py` -- nowhere else, no other module, no external API -- to retry a flaky internal call.

## Paraphrase variants (holdout)

1. jobs/worker.py needs a retry(fn, times) helper used from two spots in that same file.
2. Add a tiny internal retry wrapper, called twice, both call sites inside jobs/worker.py.

## Baseline framing (no-skill arm)

The no-skill baseline gets the same starting files and task text with a plain editing capability and no access to the design-it-twice reference material -- it may still write and compare several designs on its own initiative if it chooses.
