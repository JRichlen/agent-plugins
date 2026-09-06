#!/usr/bin/env python3
"""Generic outcome verifier for the registry lane's reference corpus.

Usage: verify_outcome.py <workspace>

<workspace>/guard.sh must carry exactly one line ending in the trailing
comment "# GUARD_CHECK" -- that line IS the real, per-card, task-specific
correctness check (it differs completely between plugins and between cards;
nothing here is decidable by reading the card's metadata). This script:

  1. fails closed if the marker line is missing entirely (this is what
     controls.MUTATIONS' "delete-guard-line" produces) or is itself commented
     out ("comment-out-check"),
  2. otherwise executes the marker line as a bash command with
     cwd=<workspace> and AGENTIC_REPO_ROOT set to this repo's root, and
     reports ITS exit code as the verdict.

Prints a JSON verdict {"passed": bool, "reason": str} on stdout; exits 0 if
passed, 1 otherwise.
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

_MARKER = "# GUARD_CHECK"


def _repo_root() -> pathlib.Path:
    here = pathlib.Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / ".claude-plugin" / "marketplace.json").is_file():
            return candidate
    raise SystemExit("verify_outcome: cannot locate repo root from " + str(here))


def _verdict(ws: pathlib.Path) -> tuple[bool, str]:
    guard = ws / "guard.sh"
    if not guard.is_file():
        return False, "guard.sh is missing"
    marker_lines = [ln for ln in guard.read_text().splitlines() if _MARKER in ln]
    if not marker_lines:
        return False, "no line carries the '# GUARD_CHECK' marker"
    active = [ln for ln in marker_lines if not ln.lstrip().startswith("#")]
    if not active:
        return False, "the guard check line is commented out"
    check_cmd = active[0]
    env = dict(os.environ)
    env["AGENTIC_REPO_ROOT"] = str(_repo_root())
    proc = subprocess.run(
        ["bash", "-c", check_cmd],
        cwd=ws,
        env=env,
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0:
        return True, f"guard check passed: {check_cmd.strip()}"
    detail = (proc.stderr or proc.stdout or "").strip()[:400]
    return False, f"guard check failed (exit {proc.returncode}): {check_cmd.strip()} :: {detail}"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(json.dumps({"passed": False, "reason": "usage: verify_outcome.py <workspace>"}))
        return 1
    ws = pathlib.Path(argv[1]).resolve()
    passed, reason = _verdict(ws)
    print(json.dumps({"passed": passed, "reason": reason}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
