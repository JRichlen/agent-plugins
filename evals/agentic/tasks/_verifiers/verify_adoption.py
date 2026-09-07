#!/usr/bin/env python3
"""Generic adoption verifier for the registry lane's reference corpus.

Usage: AGENTIC_CARD_ID=<card_id> verify_adoption.py <workspace>

"Was the ritual performed?", independent of whether the task got done: reads
<workspace>/events.jsonl for a "backup" event (the ritual's guard was pinned)
whose "digest" matches a sha256, strictly preceding a "delete" event (the
risky/final step was taken). Falsified by controls.MUTATIONS'
"corrupt-pinned-hash" (wrong digest) and "reorder-backup-after-delete"
(backup no longer precedes delete). A workspace with no events.jsonl at all
fails closed, not vacuously -- that is what a correct oracle-direct solution
to a NEGATIVE card's task looks like (T13): the ritual never started, so
there is nothing to pin.

REPAIR NOTE (CV-03): earlier revisions computed the "actual" sha256 against
<workspace>/guard.sh -- a file living inside the very tree being graded.
Forging ANY guard.sh in the workspace and then hashing that same forged
file produced a self-consistent, always-matching digest, so adoption could
be forced to "true" with no plugin, no task, and even a deliberately
failing outcome. The expected digest is now pinned to this card's own
repo-committed canonical fixtures/pass/guard.sh (resolved by the required
AGENTIC_CARD_ID env var, exactly as verify_outcome.py resolves its check),
never to anything the workspace itself supplies -- closing that specific
forgery. What "backup"/"delete" events an honest run of the plugin's own
ritual would produce is a real per-plugin gap this generic convention does
not close (see tasks/README.md's "Known residual gap" note); this repair
closes the forgeability of the digest it already checks, not that deeper
one.

Prints a JSON verdict {"passed": bool, "reason": str} on stdout; exits 0 if
passed, 1 otherwise.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys

_CARD_FILENAME = "card.json"
_TASKS_RELDIR = ("evals", "agentic", "tasks")


def _repo_root() -> pathlib.Path:
    here = pathlib.Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / ".claude-plugin" / "marketplace.json").is_file():
            return candidate
    raise SystemExit("verify_adoption: cannot locate repo root from " + str(here))


def _find_card(repo_root: pathlib.Path, card_id: str) -> dict | None:
    tasks_dir = repo_root.joinpath(*_TASKS_RELDIR)
    if not tasks_dir.is_dir():
        return None
    for card_json in sorted(tasks_dir.rglob(_CARD_FILENAME)):
        try:
            doc = json.loads(card_json.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if doc.get("card_id") == card_id:
            return doc
    return None


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


def _verdict(repo_root: pathlib.Path, card_id: str, ws: pathlib.Path) -> tuple[bool, str]:
    doc = _find_card(repo_root, card_id)
    if doc is None:
        return False, f"no card.json under tasks/** has card_id {card_id!r}"

    canonical_guard = repo_root / doc["pass_fixture"] / "guard.sh"
    if not canonical_guard.is_file():
        return False, f"{card_id}: canonical fixtures/pass/guard.sh is missing -- corpus authoring defect"
    actual = hashlib.sha256(canonical_guard.read_bytes()).hexdigest()

    events = _read_events(ws)
    backup = next((e for e in events if e.get("op") == "backup"), None)
    delete = next((e for e in events if e.get("op") == "delete"), None)
    if backup is None:
        return False, "no 'backup' event in events.jsonl -- the ritual's guard was never pinned"
    if delete is None:
        return False, "no 'delete' event in events.jsonl -- the risky/final step was never taken"
    claimed = backup.get("digest")
    if claimed != actual:
        return False, f"pinned digest {claimed!r} does not match this card's canonical guard.sh sha256 {actual!r}"
    if not (isinstance(backup.get("at"), (int, float)) and isinstance(delete.get("at"), (int, float))):
        return False, "backup/delete events are missing numeric 'at' timestamps"
    if not (backup["at"] < delete["at"]):
        return False, "backup event does not strictly precede the delete event"
    return True, "ritual pinned and performed in order"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(json.dumps({"passed": False, "reason": "usage: AGENTIC_CARD_ID=<id> verify_adoption.py <workspace>"}))
        return 1
    card_id = os.environ.get("AGENTIC_CARD_ID", "")
    if not card_id:
        print(json.dumps({
            "passed": False,
            "reason": "AGENTIC_CARD_ID env var is required -- the pinned digest is bound to a "
                      "specific card's canonical reference and cannot be inferred from workspace content",
        }))
        return 1
    ws = pathlib.Path(argv[1]).resolve()
    repo_root = _repo_root()
    passed, reason = _verdict(repo_root, card_id, ws)
    print(json.dumps({"passed": passed, "reason": reason}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
