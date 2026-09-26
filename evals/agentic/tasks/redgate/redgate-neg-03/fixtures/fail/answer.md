`call_with_retry` already handles timeouts: it passes `timeout=timeout`
into `fn` on every attempt and retries on `TimeoutError` up to `attempts`
times before re-raising. No change is needed.
