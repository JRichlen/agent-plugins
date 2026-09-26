#!/usr/bin/env python3
"""Run canonical task acceptance checks in a networkless bubblewrap sandbox.

Usage: AGENTIC_CARD_ID=<id> verify_outcome.py <workspace>

Only explicitly declared grading helpers may be seeded into the disposable
subject workspace. Equal pass/fail bytes never make a deliverable a helper.
The sandbox cannot read corpus reference fixtures or user credentials, and
there is no host-execution fallback when isolation is unavailable.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import resource
import secrets
import selectors
import shutil
import signal
import subprocess
import sys
import tempfile
import time

_MARKER = "# GUARD_CHECK"
_CARD_FILENAME = "card.json"
_TASKS_RELDIR = ("evals", "agentic", "tasks")


class SandboxUnavailableError(RuntimeError):
    """Isolation failed before a candidate command could be evaluated."""


def _repo_root() -> pathlib.Path:
    here = pathlib.Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / ".claude-plugin" / "marketplace.json").is_file():
            return candidate
    raise SystemExit("verify_outcome: cannot locate repo root from " + str(here))


def _find_card(repo_root: pathlib.Path, card_id: str) -> dict | None:
    """Scans tasks/** for the card.json whose own card_id field matches --
    never trusts a caller-supplied path, only a caller-supplied identity."""
    match = re.fullmatch(r"([a-z0-9-]+)-(pos|neg|near)-[0-9]+", card_id)
    if not match:
        return None
    path = repo_root.joinpath(*_TASKS_RELDIR, match[1], card_id, _CARD_FILENAME)
    try:
        doc = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if doc.get("card_id") != card_id:
        return None
    doc["_card_dir"] = str(path.parent)
    return doc


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
    """Only explicit grader-owned helpers may be injected, never outputs.

    Equal pass/fail bytes do not imply ownership: negative cards often
    share their correct deliverable across both sides.
    """
    declaration = pathlib.Path(doc["_card_dir"]) / "grading-helpers.json"
    if not declaration.is_file():
        return {}
    helpers: dict[str, bytes] = {}
    for name in json.loads(declaration.read_text()):
        rel = pathlib.PurePosixPath(name)
        if rel.is_absolute() or ".." in rel.parts:
            raise ValueError("invalid grading helper path")
        helpers[name] = (repo_root / doc["pass_fixture"] / name).read_bytes()
    return helpers


def _sandbox(repo_root: pathlib.Path, workspace: pathlib.Path, command: list[str], *,
             readonly_inputs: pathlib.Path | None = None, expose_grading_code: bool = True,
             timeout_s: float = 20, output_limit_bytes: int = 1024 * 1024,
             protocol_requests: list[dict] | None = None) -> subprocess.CompletedProcess:
    """No host fallback, credentials, home, host sockets, or network.

    Graders may read canonical code; subjects receive only explicitly staged
    inputs and the runtime. Capture is bounded while the process is running.
    """
    bwrap = shutil.which("bwrap")
    if not bwrap:
        raise SandboxUnavailableError("bubblewrap (bwrap) is required to grade executable artifacts safely")
    args = [bwrap, "--unshare-all", "--unshare-user", "--die-with-parent", "--new-session", "--clearenv",
            "--setenv", "PATH", "/usr/bin:/bin", "--setenv", "HOME", "/nonexistent",
            "--setenv", "LC_ALL", "C.UTF-8", "--setenv", "PYTHONDONTWRITEBYTECODE", "1",
            "--setenv", "AGENTIC_REPO_ROOT", "/repo"]
    for path in ("/usr", "/bin", "/lib", "/lib64"):
        if pathlib.Path(path).exists():
            args += ["--ro-bind", path, path]
    args += ["--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp"]
    if expose_grading_code:
        args += ["--setenv", "PYTHONSAFEPATH", "1",
                 "--ro-bind", str(repo_root / "plugins"), "/repo/plugins",
                 "--ro-bind", str(repo_root / "evals/agentic/tasks/_verifiers"), "/repo/evals/agentic/tasks/_verifiers",
                 "--ro-bind", str(repo_root / ".claude-plugin"), "/repo/.claude-plugin"]
    args += ["--bind", str(workspace), "/work"]
    if readonly_inputs is not None:
        args += ["--ro-bind", str(readonly_inputs), "/inputs"]
    args += ["--chdir", "/work", "--"] + command
    def limits():
        resource.setrlimit(resource.RLIMIT_AS, (768 * 1024 * 1024,) * 2)
        resource.setrlimit(resource.RLIMIT_FSIZE, (16 * 1024 * 1024,) * 2)
        resource.setrlimit(resource.RLIMIT_CPU, (15, 15))
        resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))

    captured = {"stdout": bytearray(), "stderr": bytearray()}
    status_bytes = bytearray()
    protocol_buffer = bytearray()
    protocol_results = []
    protocol_error = None
    challenge = None
    next_request = 0
    protocol_closed = False
    overflow = False
    deadline = time.monotonic() + timeout_s
    status_reader, status_writer = os.pipe()
    block_reader, block_writer = os.pipe()
    process_limit_applied = False
    with (os.fdopen(status_reader, "rb", buffering=0) as status,
          os.fdopen(status_writer, "wb", buffering=0) as sink,
          os.fdopen(block_reader, "rb", buffering=0) as blocked,
          os.fdopen(block_writer, "wb", buffering=0) as release):
        args[1:1] = ["--json-status-fd", str(sink.fileno()), "--block-fd", str(blocked.fileno())]
        try:
            proc = subprocess.Popen(args, stdin=subprocess.PIPE if protocol_requests is not None else subprocess.DEVNULL,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    start_new_session=True, preexec_fn=limits,
                                    pass_fds=(sink.fileno(), blocked.fileno()))
        except (OSError, subprocess.SubprocessError) as exc:
            raise SandboxUnavailableError("sandbox could not start: " + str(exc)) from exc
        sink.close()
        blocked.close()
        with proc:
            try:
                with selectors.DefaultSelector() as streams:
                    streams.register(proc.stdout, selectors.EVENT_READ, "stdout")
                    streams.register(proc.stderr, selectors.EVENT_READ, "stderr")
                    streams.register(status, selectors.EVENT_READ, "status")
                    while streams.get_map() and not overflow and not protocol_error:
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            raise subprocess.TimeoutExpired(args, timeout_s)
                        for key, _ in streams.select(remaining):
                            block = os.read(key.fd, 65536)
                            if not block:
                                streams.unregister(key.fileobj)
                                continue
                            if key.data == "status":
                                if len(status_bytes) + len(block) > 4096:
                                    raise SandboxUnavailableError("sandbox status exceeded capture limit")
                                status_bytes.extend(block)
                                if not process_limit_applied and b"\n" in status_bytes:
                                    try:
                                        child_pid = json.loads(status_bytes.splitlines()[0])["child-pid"]
                                        if type(child_pid) is not int or child_pid <= 0:
                                            raise ValueError("invalid namespace process id")
                                        if os.readlink(f"/proc/{child_pid}/ns/user") == os.readlink("/proc/self/ns/user"):
                                            raise ValueError("child did not enter an independent user namespace")
                                        # RLIMIT_NPROC counts the real user's tasks in
                                        # its user namespace. Applying it before clone
                                        # incorrectly charges the shared host UID.
                                        # bwrap's block fd prevents candidate execution
                                        # until this unchanged bound is installed.
                                        inherited = resource.prlimit(child_pid, resource.RLIMIT_NPROC)
                                        bound = min([256] + [n for n in inherited if n != resource.RLIM_INFINITY])
                                        resource.prlimit(child_pid, resource.RLIMIT_NPROC, (bound, bound))
                                        process_limit_applied = True
                                        release.write(b"1")
                                        release.close()
                                    except (OSError, ValueError, KeyError) as exc:
                                        raise SandboxUnavailableError("cannot apply process limit in sandbox namespace: " + str(exc)) from exc
                                continue
                            available = output_limit_bytes - sum(map(len, captured.values()))
                            captured[key.data].extend(block[:available])
                            if len(block) > available:
                                overflow = True
                                break
                            if protocol_requests is not None and key.data == "stdout":
                                protocol_buffer.extend(block)
                                while b"\n" in protocol_buffer and not protocol_error:
                                    line, _, rest = protocol_buffer.partition(b"\n")
                                    protocol_buffer = bytearray(rest)
                                    try:
                                        reply = json.loads(line)
                                        if challenge is None:
                                            if reply != {"ready": True} or reply.get("ready") is not True:
                                                raise ValueError("missing ready response")
                                        elif protocol_closed or not isinstance(reply, dict) or set(reply) != {"challenge", "value"} or reply["challenge"] != challenge:
                                            raise ValueError("unbound or unexpected response")
                                        elif next_request > len(protocol_requests):
                                            if reply["value"] != {"closed": True} or reply["value"].get("closed") is not True:
                                                raise ValueError("missing close response")
                                            protocol_closed = True
                                            proc.stdin.close()
                                            continue
                                        else:
                                            protocol_results.append(reply["value"])
                                        # Generate each challenge only after the previous
                                        # response; the subject cannot pre-record a transcript.
                                        challenge = secrets.token_hex(32)
                                        request = (protocol_requests[next_request] if next_request < len(protocol_requests)
                                                   else {"operation": "close"})
                                        proc.stdin.write(json.dumps({**request, "challenge": challenge}).encode() + b"\n")
                                        proc.stdin.flush()
                                        next_request += 1
                                    except (ValueError, TypeError, BrokenPipeError) as exc:
                                        protocol_error = "candidate protocol failed: " + str(exc)
                                        break
                if not overflow and not protocol_error:
                    proc.wait(timeout=max(0, deadline - time.monotonic()))
            finally:
                # Killing only the direct process can leave children holding pipes
                # or writing artifacts. Kill the host process group and reap bwrap;
                # destroying its PID namespace also kills children that called setsid.
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.wait()
    out, err = (captured[key].decode("utf-8", errors="replace") for key in ("stdout", "stderr"))
    if overflow:
        err = f"sandbox output exceeded {output_limit_bytes} byte capture limit"
    elif not protocol_error:
        # bwrap owns this pipe and closes it before executing candidate code.
        # Its exit-code record exists only if command startup succeeded; its
        # earlier child-pid record alone does not prove mounts or exec succeeded.
        try:
            statuses = [json.loads(line) for line in status_bytes.splitlines()]
        except (ValueError, UnicodeError) as exc:
            raise SandboxUnavailableError("sandbox returned malformed startup status") from exc
        if not any(isinstance(doc, dict) and type(doc.get("exit-code")) is int for doc in statuses):
            raise SandboxUnavailableError("sandbox could not start: " + err.strip()[:400])
        if protocol_requests is not None and (not protocol_closed or protocol_buffer or len(protocol_results) != len(protocol_requests)):
            protocol_error = "candidate protocol ended before all requested results and close were observed"
    if protocol_error:
        err = protocol_error
    result = subprocess.CompletedProcess(args, 1 if overflow or protocol_error else proc.returncode, out, err)
    result.output_truncated = overflow
    result.protocol_results = protocol_results
    return result


def _verdict(repo_root: pathlib.Path, card_id: str, src_ws: pathlib.Path) -> tuple[bool, str]:
    doc = _find_card(repo_root, card_id)
    if doc is None:
        return False, f"no card.json under tasks/** has card_id {card_id!r}"

    canonical_dir = repo_root / doc["pass_fixture"]
    task_inputs = pathlib.Path(doc["_card_dir"]) / "task"
    if card_id == "verify-before-claim-pos-01":
        for name in ("module_test.py", "inputs/module_test.py"):
            supplied = src_ws / name
            if supplied.exists() and supplied.read_bytes() != (task_inputs / "module_test.py").read_bytes():
                return False, "supplied test target is immutable; replacement cannot establish verification"
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

        try:
            proc = _sandbox(repo_root, tmp_ws, ["env", "AGENTIC_CARD_ID=" + card_id, "bash", "-c", check_cmd],
                            readonly_inputs=task_inputs if task_inputs.is_dir() else None)
        except subprocess.TimeoutExpired as exc:
            return False, "candidate grading exceeded the execution time limit: " + str(exc)
        if proc.returncode == 0:
            return True, f"guard check passed: {check_cmd.strip()}"
        if proc.returncode == 99 and check_cmd.strip().startswith('python3 "$AGENTIC_REPO_ROOT/evals/agentic/tasks/_verifiers/check_task.py"'):
            raise SandboxUnavailableError("nested candidate sandbox unavailable: " + proc.stderr.strip()[:400])
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
