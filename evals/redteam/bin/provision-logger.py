#!/usr/bin/env python3
"""Explicit, hash-locked lifecycle backport for the offline tool installation.

Normal invocations use --check only. --apply is a separate provisioning action;
it never downloads packages, changes versions, or accepts an unknown preimage.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import shlex
import stat
import subprocess
import sys
import tempfile

PATCHES = pathlib.Path(__file__).resolve().parents[1] / "patches"
MANIFEST = PATCHES / "winston-3.19.0-drain.json"


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _inspect(home: pathlib.Path, consumer: pathlib.Path, manifest: dict, name: str, version: str):
    # Refuse NODE_PATH/global fallbacks outside this explicit npm installation.
    choices = (consumer / "node_modules" / name, home.parent / name)
    dependency = next((p for p in choices if (p / "package.json").is_file()), None)
    if dependency is None:
        raise ValueError(f"{name} dependency missing from the controlled tool installation")
    dependency = dependency.resolve(strict=True)
    if not dependency.is_relative_to(home.parent):
        raise ValueError(f"{name} dependency escapes the controlled tool installation")
    package = json.loads((dependency / "package.json").read_text(encoding="utf-8"))
    if package.get("name") != name or package.get("version") != version:
        raise ValueError(f"unexpected {name} package/version for logger backport")
    source = dependency / manifest["source"]
    if source.is_symlink() or not source.resolve(strict=True).is_relative_to(dependency):
        raise ValueError(f"{name} logger source escapes its package")
    before = source.read_bytes()
    observed = digest(before)
    patch = (PATCHES / manifest["patch"]).read_bytes()
    if digest(patch) != manifest["patch_sha256"]:
        raise ValueError(f"{name} backport patch hash mismatch")
    if observed not in (manifest["source_sha256_before"], manifest["source_sha256_after"]):
        raise ValueError(f"unexpected {name} logger source sha256={observed}; refusing mutation")
    return dependency, source, before, patch, manifest


def provision(promptfoo_home: pathlib.Path, *, apply: bool = False) -> str:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    transport = json.loads((PATCHES / "winston-transport-4.9.0-batch.json").read_text(encoding="utf-8"))
    home = promptfoo_home.resolve(strict=True)
    package = json.loads((home / "package.json").read_text(encoding="utf-8"))
    if package.get("name") != "promptfoo" or package.get("version") != manifest["promptfoo_version"]:
        raise ValueError("unexpected Promptfoo package/version for logger backport")
    logger = _inspect(home, home, manifest, "winston", manifest["winston_version"])
    batch = _inspect(home, logger[0], transport, transport["name"], transport["version"])
    pending = [entry for entry in (logger, batch)
               if digest(entry[2]) != entry[4]["source_sha256_after"]]
    if pending and not apply:
        command = shlex.join(["python3", str(pathlib.Path(__file__).resolve()),
                              "--promptfoo-home", str(home), "--apply"])
        raise ValueError(f"logger lifecycle backports are not provisioned; run explicitly: {command}")

    # Validate every original and candidate before replacing either package.
    # Atomic replacements also avoid changing a hard-linked pristine receipt.
    candidates = []
    try:
        for _, source, before, patch, record in pending:
            fd, name = tempfile.mkstemp(prefix=".logger-backport-", dir=source.parent)
            os.close(fd)
            candidate = pathlib.Path(name)
            candidates.append((candidate, source, before))
            result = subprocess.run(
                ["patch", "--batch", "--fuzz=0", "--output", str(candidate), str(source)],
                input=patch, capture_output=True, timeout=10,
            )
            if result.returncode != 0:
                raise ValueError("logger lifecycle patch failed: " + result.stderr.decode("utf-8", errors="replace"))
            if digest(candidate.read_bytes()) != record["source_sha256_after"]:
                raise ValueError("logger backport postimage hash mismatch; installed source preserved")
            candidate.chmod(stat.S_IMODE(source.stat().st_mode))
        if any(source.read_bytes() != before for _, source, before in candidates):
            raise ValueError("logger dependency source changed during provisioning; refusing replacement")
        for candidate, source, _ in candidates:
            candidate.replace(source)
    finally:
        for candidate, _, _ in candidates:
            candidate.unlink(missing_ok=True)
    return "logger lifecycle backports verified: winston 3.19.0 + winston-transport 4.9.0"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--promptfoo-home", type=pathlib.Path, required=True)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--apply", action="store_true")
    action.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        print(provision(args.promptfoo_home, apply=args.apply))
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(f"redteam FAIL logger: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
