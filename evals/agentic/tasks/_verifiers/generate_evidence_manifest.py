#!/usr/bin/env python3
"""CV-04 (evidence/manifest.json half): deterministic evidence-binding
manifest generator for one corpus fixture directory
(``tasks/<plugin>/<card>/fixtures/<kind>/``).

Usage: generate_evidence_manifest.py <card_id> <fixture_dir>

Why this exists: ``framework.controls.detect_copied_evidence`` (T08) checks
a LIVE attempt's evidence against an ``evidence/manifest.json`` bound to
that attempt's run_id/attempt_id/timestamp window -- but corpus fixtures
checked into ``tasks/**`` are static assets, not live attempts, so that
exact shape does not apply to them. This generator produces the static-
fixture analogue: a manifest binding a fixture's own content to the specific
``card_id`` it belongs to, so that copying one card's fixture verbatim into
another card's directory (CV-04's exact repro: stop-rule-pos-01's pass
fixture satisfied 74/74 other cards' verifiers) produces a manifest whose
``card_id`` no longer matches -- detectable by ``is_current`` /
``framework.controls.detect_forged_fixture_evidence`` below, wired into
``framework.validate`` for cards that opt in.

The manifest is a pure, deterministic function of (card_id, the fixture
directory's own file contents) -- no wall-clock timestamp, no run/attempt
id, no randomness -- so re-running this generator against unchanged inputs
always reproduces byte-identical output, and `is_current` can tell a
still-correct manifest from a stale or forged one without any external
state.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

MANIFEST_RELPATH = pathlib.PurePosixPath("evidence") / "manifest.json"


def _content_entries(fixture_dir: pathlib.Path) -> list[list[str]]:
    """Every file under `fixture_dir` EXCEPT the evidence/ directory itself
    (no self-reference), as sorted [relpath, sha256] pairs."""
    entries: list[list[str]] = []
    for path in sorted(fixture_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(fixture_dir).as_posix()
        if rel == str(MANIFEST_RELPATH) or rel.startswith("evidence/"):
            continue
        entries.append([rel, hashlib.sha256(path.read_bytes()).hexdigest()])
    return entries


def compute_manifest(card_id: str, fixture_dir: pathlib.Path) -> dict:
    fixture_dir = pathlib.Path(fixture_dir)
    entries = _content_entries(fixture_dir)
    content_digest = hashlib.sha256(
        json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {"card_id": card_id, "content_digest": content_digest}


def write_manifest(card_id: str, fixture_dir: pathlib.Path) -> pathlib.Path:
    fixture_dir = pathlib.Path(fixture_dir)
    manifest = compute_manifest(card_id, fixture_dir)
    evidence_dir = fixture_dir / "evidence"
    evidence_dir.mkdir(exist_ok=True)
    manifest_path = evidence_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest_path


def read_manifest(fixture_dir: pathlib.Path) -> dict | None:
    manifest_path = pathlib.Path(fixture_dir) / MANIFEST_RELPATH
    if not manifest_path.is_file():
        return None
    try:
        doc = json.loads(manifest_path.read_text())
    except json.JSONDecodeError:
        return None
    return doc if isinstance(doc, dict) else None


def is_current(card_id: str, fixture_dir: pathlib.Path) -> bool:
    """True iff `fixture_dir` carries an evidence/manifest.json that
    matches a fresh recompute for (card_id, this fixture's own current
    content) -- i.e. it is present, well-formed, names the right card, and
    was not copied from (or left stale relative to) a different fixture."""
    on_disk = read_manifest(fixture_dir)
    if on_disk is None:
        return False
    return on_disk == compute_manifest(card_id, fixture_dir)


def has_evidence_manifest(fixture_dir: pathlib.Path) -> bool:
    return (pathlib.Path(fixture_dir) / MANIFEST_RELPATH).is_file()


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: generate_evidence_manifest.py <card_id> <fixture_dir>", file=sys.stderr)
        return 2
    card_id, fixture_dir = argv[1], pathlib.Path(argv[2])
    if not fixture_dir.is_dir():
        print(f"generate_evidence_manifest: not a directory: {fixture_dir}", file=sys.stderr)
        return 2
    path = write_manifest(card_id, fixture_dir)
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
