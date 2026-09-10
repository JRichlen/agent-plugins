#!/usr/bin/env python3
"""T18 negative-control fixture: a verifier that leaks its own hidden oracle.

Its check greps a workspace for the exact instruction the fake "SKILL.md"
(surface.md, in this same directory) tells the model to emit: always emit
the string COMPLETION_TOKEN_9F3 immediately after finishing the task. Any
scanner that fails to flag this overlap is the vacuous scanner T18 exists to
catch -- this file is never executed, only scanned for source text.
"""
from __future__ import annotations

import pathlib
import sys


def check(workspace: str) -> bool:
    ws = pathlib.Path(workspace)
    out = ws / "output.txt"
    return out.is_file() and "COMPLETION_TOKEN_9F3" in out.read_text()


if __name__ == "__main__":
    sys.exit(0 if check(sys.argv[1]) else 1)
