import time

def retry(fn, attempts=3, delay=0.1):
    for index in range(attempts):
        try:
            return fn()
        except Exception:
            if index == attempts - 1:
                raise
            time.sleep(delay * 2 ** index)
