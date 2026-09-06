#!/usr/bin/env python3
"""bin/freeze.py — writes/checks evals/redteam/corpus/manifest.json (T44).

Python 3.12 standard library only.

    python3 evals/redteam/bin/freeze.py --write     # developer command; never called by run.sh
    python3 evals/redteam/bin/freeze.py --check      # called by run.sh before anything else

`--check` enforces, each with its own FAIL substring so the counterfeit corpus
can target them individually (design §5.3):

  1. every manifest entry's file exists and its sha256 matches            -> "hash drift"
  2. every file under corpus/{clean,adversarial}/** appears in manifest   -> "unmanifested file"
  3. `counts` matches the actual file count in both directions            -> "count drift"
  4. every adversarial file has its clean twin and vice versa             -> "unmatched twin"

Plus a fifth class this lane also freezes into the same manifest (design §6.5):
the deterministic control providers, the effects scanner, and the generic
guidance block, so that "fix a failing probe by silently editing the target"
becomes a visible manifest diff instead of an invisible one.

There is no code path here that lets a run PRODUCE the corpus. `load()` is the
only way anything else in this tree may read corpus text, and it refuses any
path not already in the manifest (`CorpusNotFrozen`).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REDTEAM_ROOT = Path(__file__).resolve().parents[1]
CORPUS_DIR = REDTEAM_ROOT / "corpus"
MANIFEST_PATH = CORPUS_DIR / "manifest.json"
FAMILIES = (
    "authority-forgery", "evidence-forgery", "destructive-shortcut", "secret-exfil",
    "egress-bypass", "repo-prompt-injection", "terminal-output-injection", "sandbox-escape",
)
CONDITIONS = ("clean", "adversarial")

# Non-corpus assets frozen into the same manifest (design §6.5), paths
# relative to REDTEAM_ROOT.
FROZEN_EXTRA = (
    "providers/control-safe.js",
    "providers/control-vulnerable.js",
    "providers/control-refusenik.js",
    "providers/lib/effects.js",
    "targets/generic-guidance.md",
    "fixtures/counterfeit/held-out.json",
)


class CorpusNotFrozen(Exception):
    """Raised by load() for any path not present (by hash) in manifest.json."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fail(msg: str) -> "NoReturn":  # noqa: F821 - used only for typing hint clarity
    # Frozen ordering (lane name first): contract §8.8/§8.6.
    print(f"redteam FAIL corpus: {msg}", file=sys.stderr)
    sys.exit(1)


def _discover_corpus_files() -> list[Path]:
    out: list[Path] = []
    for condition in CONDITIONS:
        d = CORPUS_DIR / condition
        if not d.is_dir():
            continue
        for family_dir in sorted(d.iterdir()):
            if not family_dir.is_dir():
                continue
            for f in sorted(family_dir.glob("*.txt")):
                out.append(f)
    return out


def build_manifest() -> dict:
    files = []
    for f in _discover_corpus_files():
        condition = f.parent.parent.name
        family = f.parent.name
        index = int(f.stem)
        other_condition = "adversarial" if condition == "clean" else "clean"
        twin = f"{other_condition}/{family}/{f.name}"
        rel = f.relative_to(CORPUS_DIR).as_posix()
        files.append({
            "path": rel,
            "sha256": _sha256(f),
            "bytes": f.stat().st_size,
            "family": family,
            "condition": condition,
            "index": index,
            "twin": twin,
        })
    files.sort(key=lambda e: e["path"])

    counts = {
        "clean": sum(1 for e in files if e["condition"] == "clean"),
        "adversarial": sum(1 for e in files if e["condition"] == "adversarial"),
    }
    counts["total"] = counts["clean"] + counts["adversarial"]

    frozen_extra = []
    for rel in FROZEN_EXTRA:
        p = REDTEAM_ROOT / rel
        if not p.is_file():
            continue
        frozen_extra.append({"path": rel, "sha256": _sha256(p), "bytes": p.stat().st_size})

    return {
        "version": 1,
        "algo": "sha256",
        "families": list(FAMILIES),
        "counts": counts,
        "files": files,
        "frozen_extra": frozen_extra,
    }


def cmd_write() -> int:
    manifest = build_manifest()
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    print(f"redteam corpus: wrote {MANIFEST_PATH} "
          f"({manifest['counts']['total']} corpus files, {len(manifest['frozen_extra'])} frozen extras)")
    return 0


def cmd_check() -> int:
    if not MANIFEST_PATH.is_file():
        _fail(f"manifest missing at {MANIFEST_PATH}")
    try:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        _fail(f"manifest does not parse: {exc}")
        return 1

    entries = manifest.get("files", [])
    manifested_paths = {e["path"] for e in entries}

    # 1. hash drift (and existence)
    for e in entries:
        p = CORPUS_DIR / e["path"]
        if not p.is_file():
            _fail(f"missing file {e['path']}")
        actual = _sha256(p)
        if actual != e["sha256"]:
            _fail(f"hash drift {e['path']} expected {e['sha256']} got {actual}")

    # 2. unmanifested files (reverse direction)
    on_disk = {f.relative_to(CORPUS_DIR).as_posix() for f in _discover_corpus_files()}
    for path in sorted(on_disk - manifested_paths):
        _fail(f"unmanifested file {path}")
    for path in sorted(manifested_paths - on_disk):
        _fail(f"unmanifested file {path} (present in manifest, missing on disk)")

    # 3. count drift, both directions
    counts = manifest.get("counts", {})
    actual_counts = {
        "clean": sum(1 for e in entries if e["condition"] == "clean"),
        "adversarial": sum(1 for e in entries if e["condition"] == "adversarial"),
    }
    actual_counts["total"] = actual_counts["clean"] + actual_counts["adversarial"]
    disk_counts = {
        "clean": sum(1 for p in on_disk if p.startswith("clean/")),
        "adversarial": sum(1 for p in on_disk if p.startswith("adversarial/")),
    }
    disk_counts["total"] = disk_counts["clean"] + disk_counts["adversarial"]
    if counts != actual_counts or counts != disk_counts:
        _fail(f"count drift manifest={counts} entries={actual_counts} disk={disk_counts}")

    # 4. matched twins, both directions
    for e in entries:
        if e["twin"] not in manifested_paths:
            _fail(f"unmatched twin {e['path']} (twin {e['twin']} not manifested)")

    # 5. frozen_extra hash drift
    for e in manifest.get("frozen_extra", []):
        p = REDTEAM_ROOT / e["path"]
        if not p.is_file():
            _fail(f"missing file {e['path']}")
        actual = _sha256(p)
        if actual != e["sha256"]:
            _fail(f"hash drift {e['path']} expected {e['sha256']} got {actual}")

    print(f"redteam corpus: OK — {counts['total']} corpus files "
          f"({counts['clean']} clean, {counts['adversarial']} adversarial), "
          f"{len(manifest.get('frozen_extra', []))} frozen extras, all hashes match")
    return 0


def load(rel_path: str) -> str:
    """The only sanctioned way to read corpus text. Re-hashes on read and
    refuses (`CorpusNotFrozen`) any path not present in the manifest with a
    matching hash — there is no code path that reads a corpus .txt directly."""
    if not MANIFEST_PATH.is_file():
        raise CorpusNotFrozen(f"no manifest at {MANIFEST_PATH}")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    entry = next((e for e in manifest.get("files", []) if e["path"] == rel_path), None)
    if entry is None:
        raise CorpusNotFrozen(f"{rel_path} is not in corpus/manifest.json")
    p = CORPUS_DIR / rel_path
    if not p.is_file():
        raise CorpusNotFrozen(f"{rel_path} is manifested but missing on disk")
    actual = _sha256(p)
    if actual != entry["sha256"]:
        raise CorpusNotFrozen(f"{rel_path} hash drift: expected {entry['sha256']} got {actual}")
    return p.read_text(encoding="utf-8")


def load_manifest() -> dict:
    if not MANIFEST_PATH.is_file():
        raise CorpusNotFrozen(f"no manifest at {MANIFEST_PATH}")
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if args.write:
        return cmd_write()
    return cmd_check()


if __name__ == "__main__":
    raise SystemExit(main())
