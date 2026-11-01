#!/usr/bin/env python3
"""Build a deterministic source candidate from an exact Git commit; never publish."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import platform
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
import tempfile
import zlib


def git_environment():
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_OPTIONAL_LOCKS="0")
    return env


def git(repo: Path, *args: str, input_data=None) -> bytes:
    command = ["git", "--no-replace-objects", "--no-pager", "-c", "log.showSignature=false",
               "-c", "color.ui=false", "-C", str(repo), *args]
    result = subprocess.run(command, input=input_data, env=git_environment(), capture_output=True)
    if result.returncode:
        raise ValueError("git " + args[0] + " failed: " + result.stderr.decode("utf-8", "replace").strip()[:500])
    return result.stdout


def blobs(repo, oids):
    requested = list(dict.fromkeys(oids))
    raw = git(repo, "cat-file", "--batch", input_data=("\n".join(requested) + "\n").encode())
    algorithm = git(repo, "rev-parse", "--show-object-format").decode().strip()
    if algorithm not in ("sha1", "sha256"):
        raise ValueError("unsupported Git object format")
    result, offset = {}, 0
    for oid in requested:
        end = raw.index(b"\n", offset)
        header = raw[offset:end].decode().split()
        if len(header) != 3 or header[:2] != [oid, "blob"]:
            raise ValueError("unexpected batch object: " + oid)
        size = int(header[2])
        data = raw[end + 1:end + 1 + size]
        offset = end + 2 + size
        if len(data) != size or raw[offset - 1:offset] != b"\n":
            raise ValueError("truncated batch object: " + oid)
        actual = hashlib.new(algorithm, b"blob " + str(size).encode() + b"\0" + data).hexdigest()
        if actual != oid:
            raise ValueError("Git object identity mismatch: " + oid)
        result[oid] = data
    if offset != len(raw):
        raise ValueError("unexpected trailing batch data")
    return result


def build(repo: Path, revision: str, output: Path) -> dict:
    # Resolve only commits. Working tree contents and caller-supplied names are
    # never interpolated into shell commands or archive paths.
    commit = git(repo, "rev-parse", "--verify", revision + "^{commit}").decode().strip()
    tree = git(repo, "rev-parse", commit + "^{tree}").decode().strip()
    epoch = int(git(repo, "log", "-1", "--no-show-signature", "--format=%ct", commit))
    records = sorted((record for record in git(repo, "ls-tree", "-rz", "--full-tree", commit).split(b"\0") if record), key=lambda record: record.split(b"\t", 1)[1])
    try:
        [record.split(b"\t", 1)[1].decode("utf-8") for record in records]
    except UnicodeDecodeError:
        raise ValueError("source tree contains a non-UTF-8 filename") from None
    symlinks = {record.split(b"\t", 1)[1].decode("utf-8") for record in records
                if record and record.startswith(b"120000 ")}
    files = []
    for record in records:
        mode, kind, _oid = record.split(b"\t", 1)[0].decode().split()
        if kind != "blob" or mode not in ("100644", "100755", "120000"):
            raise ValueError("unsupported Git entry mode: " + mode)
    contents = blobs(repo, [record.split(b"\t", 1)[0].decode().split()[2] for record in records]) if records else {}
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
            if not path.parts or path.is_absolute() or ".." in path.parts or "\\" in name or any(part.casefold().rstrip(" .") == ".git" for part in path.parts):
                raise ValueError("unsafe archive path: " + name)
            if kind != "blob" or mode not in ("100644", "100755", "120000"):
                raise ValueError("unsupported Git entry: " + name + " (" + mode + ")")
            data = contents[oid]
            item = tarfile.TarInfo(prefix + "/" + name)
            item.mtime = epoch
            item.uid = item.gid = 0
            item.uname = item.gname = ""
            if mode == "120000":
                try:
                    target = data.decode("utf-8")
                except UnicodeDecodeError:
                    raise ValueError("symlink target is not UTF-8: " + name) from None
                # Reject absolute and escaping symlinks without dereferencing.
                target_path = PurePosixPath(target)
                resolved = list(path.parent.parts)
                if not target or "\0" in target or target_path.is_absolute() or "\\" in target or any(part.casefold().rstrip(" .") == ".git" for part in target_path.parts):
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
    builder_path = Path(__file__).resolve()
    try:
        builder_commit = git(builder_path.parents[1], "rev-parse", "HEAD").decode().strip()
    except ValueError:
        builder_commit = None
    manifest = {"schema": 1, "kind": "source-candidate", "commit": commit, "tree": tree,
                "archive": archive_name, "archive_sha256": hashlib.sha256(payload).hexdigest(),
                "builder": {"commit": builder_commit, "source_sha256": hashlib.sha256(builder_path.read_bytes()).hexdigest(),
                            "python": platform.python_version(), "zlib_build": zlib.ZLIB_VERSION,
                            "zlib_runtime": zlib.ZLIB_RUNTIME_VERSION, "git": git(repo, "--version").decode().strip()},
                "files": files, "qualification": "Not a release or proof of host/behavioral effectiveness."}
    # Stage in a private sibling, then publish a complete directory. Never write
    # through caller-controlled output entries; failures clean up staged bytes.
    if os.path.lexists(output):
        raise FileExistsError("candidate output already exists: " + str(output))
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest_bytes = (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode()
    with tempfile.TemporaryDirectory(prefix="." + output.name + ".build-", dir=output.parent) as temporary:
        staging = Path(temporary)
        for name, content in ((archive_name, payload), ("manifest.json", manifest_bytes),
                              ("SHA256SUMS", f"{manifest['archive_sha256']}  {archive_name}\n{hashlib.sha256(manifest_bytes).hexdigest()}  manifest.json\n".encode())):
            with (staging / name).open("xb") as destination:
                destination.write(content)
        if os.path.lexists(output):
            raise FileExistsError("candidate output appeared during build")
        os.rename(staging, output)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = build(args.repo, args.revision, args.output)
    except (OSError, ValueError, tarfile.TarError) as error:
        parser.exit(2, "candidate: " + str(error) + "\n")
    print(json.dumps({key: result[key] for key in ("kind", "commit", "tree", "archive", "archive_sha256")}))


if __name__ == "__main__":
    main()
