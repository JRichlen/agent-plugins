#!/usr/bin/env python3
"""T24 fixture worker: exit with a nonzero code, simulating a crash.

Usage: worker_fault.py [exit_code=1]

Must classify as `fault`, never `incomplete` — this is the plain non-signalled
crash case; see worker_sleep.py (killed via SIGTERM by the test) for the
signalled fault case.
"""
import sys


def main() -> int:
    code = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    print("worker_fault: simulating a crash", file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
