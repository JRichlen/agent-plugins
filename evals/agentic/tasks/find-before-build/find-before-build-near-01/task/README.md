# Task

The codebase's `utils/legacy_retry.py` already retries with a blocking `time.sleep` -- this new code path runs inside an `asyncio` event loop, where a blocking sleep would stall every other coroutine.
