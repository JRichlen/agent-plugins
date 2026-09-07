# Task

Add a small `retry(fn, times)` helper that will be called from exactly two places inside `jobs/worker.py` -- nowhere else, no other module, no external API -- to retry a flaky internal call.
