#!/usr/bin/env python3
"""Build a deterministic source candidate from an exact Git commit; never publish."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile


def git(repo: Path, *args: str) -> bytes:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True).stdout


def build(repo: Path, revision: str, output: Path) -> dict:
    # Resolve only commits. Working tree contents and caller-supplied names are
    # never interpolated into shell commands or archive paths.
    commit = git(repo, "rev-parse", "--verify", revision + "^{commit}").decode().strip()
    tree = git(repo, "rev-parse", commit + "^{tree}").decode().strip()
    epoch = int(git(repo, "show", "-s", "--format=%ct", commit))
    records = git(repo, "ls-tree", "-rz", "--full-tree", commit).split(b"\0")
    symlinks = {record.split(b"\t", 1)[1].decode("utf-8") for record in records
                if record and record.startswith(b"120000 ")}
    files = []
    archive = io.BytesIO()
    prefix = "agent-plugins-" + commit[:12]
    with tarfile.open(fileobj=archive, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for record in records:
            if not record:
                continue
            metadata, raw_name = record.split(b"\t", 1)
            mode, kind, oid = metadata.decode().split()
            name = raw_name.decode("utf-8")
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts or "\\" in name:
                raise ValueError("unsafe archive path: " + name)
            if kind != "blob" or mode not in ("100644", "100755", "120000"):
                raise ValueError("unsupported Git entry: " + name + " (" + mode + ")")
            data = git(repo, "cat-file", "blob", oid)
            item = tarfile.TarInfo(prefix + "/" + name)
            item.mtime = epoch
            item.uid = item.gid = 0
            item.uname = item.gname = ""
            if mode == "120000":
                target = data.decode("utf-8")
                # Reject absolute and escaping symlinks without dereferencing.
                target_path = PurePosixPath(target)
                resolved = list(path.parent.parts)
                if target_path.is_absolute() or "\\" in target:
                    raise ValueError("unsafe symlink: " + name)
                for part in target_path.parts:
                    if part == "..":
                        if not resolved:
                            raise ValueError("escaping symlink: " + name)
                        resolved.pop()
                    elif part != ".":
                        resolved.append(part)
                        # Lexical normalization cannot model alias/.. safely.
                        # Conservative policy: no committed symlink component,
                        # including a final link, may be traversed by a target.
                        if "/".join(resolved) in symlinks:
                            raise ValueError("symlink-component traversal: " + name)
                item.type = tarfile.SYMTYPE
                item.linkname = target
                item.mode = 0o777
                tar.addfile(item)
            else:
                item.mode = 0o755 if mode == "100755" else 0o644
                item.size = len(data)
                tar.addfile(item, io.BytesIO(data))
            files.append({"path": name, "mode": mode, "git_blob": oid, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
    compressed = io.BytesIO()
    with gzip.GzipFile(fileobj=compressed, mode="wb", filename="", mtime=0) as gz:
        gz.write(archive.getvalue())
    payload = compressed.getvalue()
    archive_name = prefix + ".tar.gz"
    manifest = {"schema": 1, "kind": "source-candidate", "commit": commit, "tree": tree,
                "archive": archive_name, "archive_sha256": hashlib.sha256(payload).hexdigest(),
                "files": files, "qualification": "Not a release or proof of host/behavioral effectiveness."}
    # Refuse even an existing empty directory or dangling directory symlink.
    # Exclusive file creation also refuses a raced-in dangling file symlink.
    output.mkdir(parents=True, exist_ok=False)
    manifest_bytes = (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode()
    for name, content in ((archive_name, payload), ("manifest.json", manifest_bytes),
                          ("SHA256SUMS", f"{manifest['archive_sha256']}  {archive_name}\n{hashlib.sha256(manifest_bytes).hexdigest()}  manifest.json\n".encode())):
        with (output / name).open("xb") as destination:
            destination.write(content)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build(args.repo, args.revision, args.output)
    print(json.dumps({key: result[key] for key in ("kind", "commit", "tree", "archive", "archive_sha256")}))


if __name__ == "__main__":
    main()
