#!/usr/bin/env python3
"""A cooperative worker that emits one line after its SIGTERM arrives.

Models the late-result case: output that is real, that the host genuinely
observed, and that must be recorded as LATE_OUTPUT with
`arrived_after_terminal=True` rather than credited as delivered.
"""
from __future__ import annotations

import signal
import sys
import time

_STOP = {"now": False}


def _on_term(signum, frame):  # noqa: ANN001, ARG001
    sys.stdout.write("LATE-AFTER-CANCEL\n")
    sys.stdout.flush()
    _STOP["now"] = True


def main() -> int:
    signal.signal(signal.SIGTERM, _on_term)
    sys.stdout.write("WORKER-READY\n")
    sys.stdout.flush()
    for _ in range(6000):
        if _STOP["now"]:
            return 0
        time.sleep(0.01)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
