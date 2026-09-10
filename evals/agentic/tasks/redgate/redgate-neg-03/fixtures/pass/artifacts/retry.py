import time


def call_with_retry(fn, attempts=3, timeout=5):
    for _ in range(attempts):
        try:
            return fn(timeout=timeout)
        except TimeoutError:
            time.sleep(1)
    raise TimeoutError("retry exhausted")
