#!/usr/bin/env python3
"""Generic outcome verifier for the registry lane's reference corpus.

Usage: AGENTIC_CARD_ID=<card_id> verify_outcome.py <workspace>

REPAIR NOTE (CV-01/CV-02/CV-04): earlier revisions of this script trusted
whatever bytes it found at ``<workspace>/guard.sh`` -- since that file lives
inside the very tree being graded, anyone (or anything) populating the
workspace could write ``true  # GUARD_CHECK`` and force a pass (CV-01), and
copying one card's ENTIRE pass fixture into a different card's workspace
satisfied that other card's grading too (CV-04), because the verdict never
depended on WHICH card was being graded. A correct direct solution to a
card's actual task also never disclosed (and had no reason to disclose)
``guard.sh``, so it failed grading for a reason unrelated to the task
(CV-02).

The check command is now resolved from this repo's own committed
``fixtures/pass/guard.sh`` for the specific ``card_id`` named by the
required ``AGENTIC_CARD_ID`` environment variable -- never from the subject
workspace. Grading happens against a throwaway COPY of the workspace (the
real workspace, and the repo's own fixtures, are never written to): any
harness-scaffolding files the check command needs (a helper script like
``check.sh`` that is byte-identical across this card's own fixtures/{pass,
fail[,near-fail]} -- i.e. part of the grading apparatus, not the agent's
deliverable) are seeded into that copy before the check runs, so a correct
direct solution that never heard of ``guard.sh`` is graded purely on the
real, task-relevant property. Whatever the subject workspace already
contains that is NOT one of those harness files (the agent's actual
deliverable -- e.g. ``delete-originals.sh``, ``docs/design-notes.md``) is
left exactly as found.

Prints a JSON verdict {"passed": bool, "reason": str} on stdout; exits 0 if
passed, 1 otherwise.
"""
from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

_MARKER = "# GUARD_CHECK"
_CARD_FILENAME = "card.json"
_TASKS_RELDIR = ("evals", "agentic", "tasks")


def _repo_root() -> pathlib.Path:
    here = pathlib.Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / ".claude-plugin" / "marketplace.json").is_file():
            return candidate
    raise SystemExit("verify_outcome: cannot locate repo root from " + str(here))


def _find_card(repo_root: pathlib.Path, card_id: str) -> dict | None:
    """Scans tasks/** for the card.json whose own card_id field matches --
    never trusts a caller-supplied path, only a caller-supplied identity."""
    tasks_dir = repo_root.joinpath(*_TASKS_RELDIR)
    if not tasks_dir.is_dir():
        return None
    for card_json in sorted(tasks_dir.rglob(_CARD_FILENAME)):
        try:
            doc = json.loads(card_json.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if doc.get("card_id") == card_id:
            doc["_card_dir"] = str(card_json.parent)
            return doc
    return None


def _active_marker_line(text: str) -> str | None:
    marker_lines = [ln for ln in text.splitlines() if _MARKER in ln]
    active = [ln for ln in marker_lines if not ln.lstrip().startswith("#")]
    return active[0] if len(active) == 1 else None


def _fixture_dirs(repo_root: pathlib.Path, doc: dict) -> list[pathlib.Path]:
    dirs = []
    for key in ("pass_fixture", "fail_fixture"):
        rel = doc.get(key)
        if rel:
            dirs.append(repo_root / rel)
    near_fail = pathlib.Path(doc["_card_dir"]) / "fixtures" / "near-fail"
    if near_fail.is_dir():
        dirs.append(near_fail)
    return dirs


def _harness_helpers(repo_root: pathlib.Path, doc: dict) -> dict[str, bytes]:
    """Files that are byte-identical across every fixture variant this card
    ships (pass, fail, and near-fail when present) are the grading
    apparatus, not the differentiated task deliverable -- a deliverable
    fixture necessarily differs between a passing and a failing workspace,
    or pass/fail would be indistinguishable. Verified empirically: guard.sh
    is byte-identical across pass/fail for all 75 corpus cards today, and
    across pass/fail/near-fail for all 25 near-miss cards."""
    fixture_dirs = _fixture_dirs(repo_root, doc)
    if not fixture_dirs:
        return {}
    first, *rest = fixture_dirs
    helpers: dict[str, bytes] = {}
    for f in sorted(first.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(first).as_posix()
        data = f.read_bytes()
        identical_everywhere = True
        for other in rest:
            other_f = other / rel
            if not other_f.is_file() or other_f.read_bytes() != data:
                identical_everywhere = False
                break
        if identical_everywhere:
            helpers[rel] = data
    return helpers


def _verdict(repo_root: pathlib.Path, card_id: str, src_ws: pathlib.Path) -> tuple[bool, str]:
    doc = _find_card(repo_root, card_id)
    if doc is None:
        return False, f"no card.json under tasks/** has card_id {card_id!r}"

    canonical_dir = repo_root / doc["pass_fixture"]
    guard_ref = canonical_dir / "guard.sh"
    if not guard_ref.is_file():
        return False, f"{card_id}: canonical fixtures/pass/guard.sh is missing -- corpus authoring defect"
    check_cmd = _active_marker_line(guard_ref.read_text())
    if check_cmd is None:
        return False, (
            f"{card_id}: canonical fixtures/pass/guard.sh does not carry exactly one active "
            f"'{_MARKER}' line -- corpus authoring defect"
        )

    with tempfile.TemporaryDirectory(prefix="agentic-outcome-") as tmp:
        tmp_ws = pathlib.Path(tmp) / "ws"
        if src_ws.is_dir():
            shutil.copytree(src_ws, tmp_ws)
        else:
            tmp_ws.mkdir(parents=True)

        for relpath, data in _harness_helpers(repo_root, doc).items():
            target = tmp_ws / relpath
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)

        env = dict(os.environ)
        env["AGENTIC_REPO_ROOT"] = str(repo_root)
        proc = subprocess.run(
            ["bash", "-c", check_cmd],
            cwd=tmp_ws,
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
        print(json.dumps({"passed": False, "reason": "usage: AGENTIC_CARD_ID=<id> verify_outcome.py <workspace>"}))
        return 1
    card_id = os.environ.get("AGENTIC_CARD_ID", "")
    if not card_id:
        print(json.dumps({
            "passed": False,
            "reason": "AGENTIC_CARD_ID env var is required -- the outcome check is bound to a "
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
