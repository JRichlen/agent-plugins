#!/usr/bin/env python3
"""T24 fixture worker: ignore SIGTERM, keep running, then finish normally.

Usage: worker_ignore_sigterm.py <hold_seconds>

Reproduces the "late result" case: the pool cancels this worker (sends
SIGTERM to its process group), the worker traps and ignores the signal
instead of dying, keeps working for `hold_seconds`, then prints its result
and exits 0. The real exit therefore arrives strictly AFTER the pool already
recorded the cancellation — WorkerPool.collect() must mark
`arrived_after_terminal=True` on this result and the caller must never score
it as an ordinary clean delivery, even though the process itself exited 0.
"""
import json
import os
import signal
import sys
import time

_state = {"sigterms_ignored": 0}


def _on_sigterm(signum, frame):  # noqa: ARG001 — signal handler signature
    _state["sigterms_ignored"] += 1


def main() -> int:
    hold = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
    signal.signal(signal.SIGTERM, _on_sigterm)
    time.sleep(hold)
    print(json.dumps({
        "label": "late-finished-after-cancel",
        "pid": os.getpid(),
        "sigterms_ignored": _state["sigterms_ignored"],
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
