import time

def retry(fn):
    time.sleep(1)
    return fn()
