#!/usr/bin/env python3
"""Trivial fixture handler: reads whatever JSON is on stdin (if any), exits 0."""
import json
import sys


def main() -> int:
    try:
        json.load(sys.stdin)
    except Exception:  # noqa: BLE001 — fixture handler must never crash the harness
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
