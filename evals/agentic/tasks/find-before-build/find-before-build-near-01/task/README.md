# Task

The codebase's `utils/legacy_retry.py` already retries with a blocking `time.sleep` -- this new code path runs inside an `asyncio` event loop, where a blocking sleep would stall every other coroutine.

## Paraphrase variants (holdout)

1. There's an existing retry helper but it blocks, and the new call site is async -- what now?
2. legacy_retry.py sleeps synchronously; the code we're adding to is asyncio-based.

## Baseline framing (no-skill arm)

The no-skill baseline gets the same repository and a plain search/editing capability, no receipt requirement -- it may still search and reuse an existing helper on its own initiative.
