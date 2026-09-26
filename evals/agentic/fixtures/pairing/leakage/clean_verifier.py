#!/usr/bin/env python3
"""T18 negative-control fixture: the paired (unrelated) adoption verifier.

Deliberately shares no text with leaky_verifier.py or surface.md -- it exists
only so the synthetic Card in test_registry.py has two distinct verifier
paths, matching the same card-shape every real corpus card uses.
"""
from __future__ import annotations

import pathlib
import sys


def check(workspace: str) -> bool:
    ws = pathlib.Path(workspace)
    marker = ws / "ritual-marker.txt"
    return marker.is_file()


if __name__ == "__main__":
    sys.exit(0 if check(sys.argv[1]) else 1)
