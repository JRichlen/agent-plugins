#!/usr/bin/env python3
"""A worker that survives SIGTERM and keeps writing.

The point of T28's negative control: a cancel implemented as a SIGKILL on the
parent alone leaves this process (and anything it forked) running, while the
ledger happily records a clean cancellation. Only signalling the process GROUP
and then diffing the live pid set catches it.
"""
from __future__ import annotations

import os
import signal
import sys
import time

_CAUGHT = {"sigterm": 0}


def _swallow(signum, frame):  # noqa: ANN001, ARG001
    _CAUGHT["sigterm"] += 1
    sys.stdout.write(f"IGNORED-SIGTERM-{_CAUGHT['sigterm']}\n")
    sys.stdout.flush()


def main() -> int:
    signal.signal(signal.SIGTERM, _swallow)
    # A grandchild in the same process group: killing only the parent pid leaves
    # this one behind, which is precisely the leak the pid-set diff must see.
    if os.fork() == 0:
        try:
            signal.signal(signal.SIGTERM, _swallow)
            for _ in range(6000):
                time.sleep(0.01)
        finally:
            os._exit(0)
    sys.stdout.write("WORKER-READY\n")
    sys.stdout.flush()
    for _ in range(6000):
        time.sleep(0.01)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
