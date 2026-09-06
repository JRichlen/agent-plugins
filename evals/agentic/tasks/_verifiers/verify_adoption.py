#!/usr/bin/env python3
"""Generic adoption verifier for the registry lane's reference corpus.

Usage: verify_adoption.py <workspace>

"Was the ritual performed?", independent of whether the task got done: reads
<workspace>/events.jsonl for a "backup" event (the ritual's guard was pinned)
whose "digest" is the REAL sha256 of <workspace>/guard.sh's current bytes,
strictly preceding a "delete" event (the risky/final step was taken).
Falsified by controls.MUTATIONS' "corrupt-pinned-hash" (wrong digest) and
"reorder-backup-after-delete" (backup no longer precedes delete). A workspace
with no events.jsonl at all fails closed, not vacuously -- that is what a
correct oracle-direct solution to a NEGATIVE card's task looks like (T13):
the ritual never started, so there is nothing to pin.

Prints a JSON verdict {"passed": bool, "reason": str} on stdout; exits 0 if
passed, 1 otherwise.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys


def _read_events(ws: pathlib.Path) -> list[dict]:
    path = ws / "events.jsonl"
    if not path.is_file():
        return []
    events: list[dict] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            events.append(json.loads(line))
    return events


def _verdict(ws: pathlib.Path) -> tuple[bool, str]:
    events = _read_events(ws)
    backup = next((e for e in events if e.get("op") == "backup"), None)
    delete = next((e for e in events if e.get("op") == "delete"), None)
    if backup is None:
        return False, "no 'backup' event in events.jsonl -- the ritual's guard was never pinned"
    if delete is None:
        return False, "no 'delete' event in events.jsonl -- the risky/final step was never taken"
    guard = ws / "guard.sh"
    if not guard.is_file():
        return False, "guard.sh is missing -- nothing to verify the pinned digest against"
    actual = hashlib.sha256(guard.read_bytes()).hexdigest()
    claimed = backup.get("digest")
    if claimed != actual:
        return False, f"pinned digest {claimed!r} does not match guard.sh's actual sha256 {actual!r}"
    if not (isinstance(backup.get("at"), (int, float)) and isinstance(delete.get("at"), (int, float))):
        return False, "backup/delete events are missing numeric 'at' timestamps"
    if not (backup["at"] < delete["at"]):
        return False, "backup event does not strictly precede the delete event"
    return True, "ritual pinned and performed in order"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(json.dumps({"passed": False, "reason": "usage: verify_adoption.py <workspace>"}))
        return 1
    ws = pathlib.Path(argv[1]).resolve()
    passed, reason = _verdict(ws)
    print(json.dumps({"passed": passed, "reason": reason}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
