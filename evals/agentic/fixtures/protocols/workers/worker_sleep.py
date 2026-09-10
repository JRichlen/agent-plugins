#!/usr/bin/env python3
"""T24 fixture worker: sleep for N seconds, then print a JSON result and exit 0.

Usage: worker_sleep.py <seconds> <label>

Used to prove WorkerPool.collect() returns results in spawn order regardless
of which worker actually finishes first (spawn a slow one, then a fast one;
the fast one's process exits first, but collect() must still yield
[slow, fast]).
"""
import json
import os
import sys
import time


def main() -> int:
    seconds = float(sys.argv[1])
    label = sys.argv[2]
    time.sleep(seconds)
    print(json.dumps({"label": label, "pid": os.getpid()}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
