#!/usr/bin/env python3
"""A worker that finishes cleanly, so the pool's happy path is exercised too."""
from __future__ import annotations

import sys


def main() -> int:
    sys.stdout.write("WORKER-DONE\n")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
