"""evals.agentic.framework.protocols — real hooks, real MCP, real subprocesses
(protocol lane, contract §3.8).

Everything here spawns REAL subprocesses of REAL repository scripts. Nothing in
this module invents a fixed list of plugins or hooks: ``discover_hooks`` always
parses whatever ``plugins/*/hooks/hooks.json`` files exist on disk under the
``repo_root`` it is given, so a hook added to any plugin tomorrow is discovered
without a code change here.

Only ``contract.py`` is imported from this lane's own framework package (per
contract §6 — the eager package ``__init__`` imports nothing else, so this
module is imported by path: ``from evals.agentic.framework import protocols``).
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import pathlib
import selectors
import signal
import subprocess
import time
from collections.abc import Mapping, Sequence
from typing import Any

from .contract import now_rfc3339

__all__ = [
    "HookSpec", "HookResult", "discover_hooks", "run_hook",
    "McpStdioClient",
    "snapshot_tree", "diff_tree",
    "WorkerResult", "WorkerPool", "leaked_pids",
]

_PLUGIN_ROOT_VAR = "${CLAUDE_PLUGIN_ROOT}"


# ---------------------------------------------------------------------------
# Hooks: discovery and real subprocess execution.
# ---------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True, slots=True)
class HookSpec:
    plugin: str
    event: str
    matcher: str
    command: str
    source_file: str


@dataclasses.dataclass(frozen=True, slots=True)
class HookResult:
    spec: HookSpec
    exit_code: int
    stdout: str
    stderr: str
    json: Mapping[str, Any] | None
    duration_ms: int


def discover_hooks(repo_root: pathlib.Path) -> tuple[HookSpec, ...]:
    """Parse every ``plugins/*/hooks/hooks.json`` under ``repo_root``.

    NEVER a literal plugin list: this walks whatever plugin directories exist on
    disk right now and reads whatever event/matcher/command triples their own
    ``hooks.json`` declares. A plugin gaining a fourth hook is discovered the
    next time this runs, with zero code changes here (T19's negative control).
    """
    repo_root = pathlib.Path(repo_root)
    plugins_dir = repo_root / "plugins"
    specs: list[HookSpec] = []
    if not plugins_dir.is_dir():
        return tuple()
    for plugin_dir in sorted(plugins_dir.iterdir()):
        if not plugin_dir.is_dir():
            continue
        hooks_json = plugin_dir / "hooks" / "hooks.json"
        if not hooks_json.is_file():
            continue
        with open(hooks_json, encoding="utf-8") as fh:
            doc = json.load(fh)
        plugin_root = str(plugin_dir.resolve())
        events = doc.get("hooks") or {}
        for event_name, groups in events.items():
            if not isinstance(groups, list):
                continue
            for group in groups:
                matcher = group.get("matcher", "") or ""
                for hook in group.get("hooks", []):
                    if hook.get("type") != "command":
                        continue
                    raw_command = hook.get("command", "")
                    command = raw_command.replace(_PLUGIN_ROOT_VAR, plugin_root)
                    specs.append(HookSpec(
                        plugin=plugin_dir.name,
                        event=event_name,
                        matcher=matcher,
                        command=command,
                        source_file=str(hooks_json.resolve()),
                    ))
    specs.sort(key=lambda s: (s.plugin, s.event, s.matcher, s.command))
    return tuple(specs)


def _scrubbed_env(home: pathlib.Path) -> dict[str, str]:
    """A minimal environment: no API keys, no ambient secrets, HOME redirected."""
    keep = ("PATH", "LANG", "LC_ALL", "LANGUAGE")
    env = {k: os.environ[k] for k in keep if k in os.environ}
    env.setdefault("PATH", "/usr/bin:/bin")
    env["HOME"] = str(home)
    return env


def _parse_single_json_object(stdout: str) -> Mapping[str, Any] | None:
    text = stdout.strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


def run_hook(spec: HookSpec, payload: Mapping[str, Any], *, cwd: pathlib.Path,
             timeout_s: float = 20.0, env: Mapping[str, str] | None = None) -> HookResult:
    """Run ``spec`` as a real subprocess, feeding ``payload`` on stdin.

    ``cwd`` MUST be a scratch directory (a temp copy), never the real repository
    tree — a hook exercised here may legitimately try to read/write relative to
    its cwd (redgate's guard reads ``.redgate/*/manifest`` under cwd).
    """
    if env is None:
        env = _scrubbed_env(pathlib.Path(cwd) / ".home")
        pathlib.Path(env["HOME"]).mkdir(parents=True, exist_ok=True)
    stdin_text = json.dumps(dict(payload))
    started = time.monotonic()
    try:
        proc = subprocess.run(
            spec.command, shell=True, cwd=str(cwd), env=dict(env),
            input=stdin_text, capture_output=True, text=True, timeout=timeout_s,
        )
        exit_code = proc.returncode
        stdout, stderr = proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        exit_code = 124
        stdout = exc.stdout or "" if isinstance(exc.stdout, str) else (exc.stdout or b"").decode("utf-8", "replace")
        stderr = exc.stderr or "" if isinstance(exc.stderr, str) else (exc.stderr or b"").decode("utf-8", "replace")
    duration_ms = int((time.monotonic() - started) * 1000)
    parsed = _parse_single_json_object(stdout)
    return HookResult(
        spec=spec, exit_code=exit_code, stdout=stdout, stderr=stderr,
        json=parsed, duration_ms=duration_ms,
    )


# ---------------------------------------------------------------------------
# MCP: a real JSON-RPC stdio client.
# ---------------------------------------------------------------------------

class McpStdioClient:
    """A minimal MCP client speaking JSON-RPC 2.0 over newline-delimited stdio.

    Drives a REAL subprocess (e.g. the agent-compiler kernel's
    ``scripts/mcp_server.py``). No mocked transport anywhere.
    """

    def __init__(self, argv: Sequence[str], *, cwd: pathlib.Path,
                 env: Mapping[str, str] | None = None, timeout_s: float = 30.0) -> None:
        self._argv = list(argv)
        self._cwd = pathlib.Path(cwd)
        if env is None:
            home = self._cwd / ".mcp-home"
            home.mkdir(parents=True, exist_ok=True)
            env = _scrubbed_env(home)
        self._env = dict(env)
        self._timeout_s = timeout_s
        self._proc: subprocess.Popen | None = None
        self._next_id = 1

    def __enter__(self) -> "McpStdioClient":
        self._proc = subprocess.Popen(
            self._argv, cwd=str(self._cwd), env=self._env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1,
        )
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None,
                 exc_tb: object) -> None:
        proc = self._proc
        if proc is None:
            return
        try:
            if proc.stdin is not None and not proc.stdin.closed:
                proc.stdin.close()
        except (BrokenPipeError, OSError):
            pass
        if exc_type is not None and issubclass(exc_type, TimeoutError):
            # A per-call read deadline (see _read_response) already burned the
            # full timeout_s budget waiting on this process. Do not wait a
            # second full timeout_s here -- kill-and-reap immediately so a
            # single stuck call never costs more than ~timeout_s total.
            if proc.poll() is None:
                proc.kill()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
        else:
            try:
                proc.wait(timeout=self._timeout_s)
            except subprocess.TimeoutExpired:
                proc.kill()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass
        for stream in (proc.stdout, proc.stderr):
            if stream is not None:
                try:
                    stream.close()
                except OSError:
                    pass

    def _send(self, method: str, params: Mapping[str, Any] | None, *, notify: bool) -> int | None:
        assert self._proc is not None and self._proc.stdin is not None
        msg: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        msg_id = None
        if not notify:
            msg_id = self._next_id
            self._next_id += 1
            msg["id"] = msg_id
        if params is not None:
            msg["params"] = params
        self._proc.stdin.write(json.dumps(msg) + "\n")
        self._proc.stdin.flush()
        return msg_id

    def _read_response(self) -> Mapping[str, Any]:
        """Read one newline-delimited JSON-RPC response, bounded by ``timeout_s``.

        ``readline()`` on its own blocks forever against a server that never
        writes a line (a hang, not a crash) -- ``timeout_s`` would then be a
        documented-but-unenforced constructor parameter. Poll the underlying
        fd against a wall-clock deadline instead, so every call through this
        client (``initialize``/``tools_list``/``call_tool``) is bounded by
        ``timeout_s`` even when the server never speaks at all.
        """
        assert self._proc is not None and self._proc.stdout is not None
        deadline = time.monotonic() + self._timeout_s
        sel = selectors.DefaultSelector()
        sel.register(self._proc.stdout, selectors.EVENT_READ)
        try:
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError(
                        f"MCP server did not respond within timeout_s={self._timeout_s}s"
                    )
                if sel.select(timeout=remaining):
                    break
        finally:
            sel.close()
        line = self._proc.stdout.readline()
        if not line:
            stderr = self._proc.stderr.read() if self._proc.stderr else ""
            raise RuntimeError(
                f"MCP server closed stdout before responding (stderr: {stderr!r})"
            )
        return json.loads(line)

    def _call(self, method: str, params: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        self._send(method, params, notify=False)
        resp = self._read_response()
        if "error" in resp:
            raise RuntimeError(f"MCP error calling {method}: {resp['error']}")
        return resp.get("result", {})

    def initialize(self) -> Mapping[str, Any]:
        result = self._call("initialize", {
            "protocolVersion": "2025-06-18",
            "clientInfo": {"name": "evals-agentic-protocols", "version": "1"},
            "capabilities": {},
        })
        self._send("notifications/initialized", None, notify=True)
        return result

    def tools_list(self) -> tuple[Mapping[str, Any], ...]:
        result = self._call("tools/list")
        return tuple(result.get("tools", ()))

    def call_tool(self, name: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        return self._call("tools/call", {"name": name, "arguments": dict(arguments)})

    @property
    def pid(self) -> int | None:
        return self._proc.pid if self._proc is not None else None


# ---------------------------------------------------------------------------
# Filesystem snapshot/diff, for asserting a probe made zero unexpected writes.
# ---------------------------------------------------------------------------

def _sha256_of(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot_tree(root: pathlib.Path, *, exclude: Sequence[str] = ()) -> Mapping[str, str]:
    root = pathlib.Path(root)
    out: dict[str, str] = {}
    if not root.is_dir():
        return out
    excluded = tuple(exclude)
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root)
        dirnames[:] = [
            d for d in dirnames
            if not any((os.path.join(rel_dir, d) if rel_dir != "." else d).startswith(e) for e in excluded)
        ]
        for name in filenames:
            full = pathlib.Path(dirpath) / name
            rel = os.path.relpath(full, root)
            if any(rel == e or rel.startswith(e.rstrip("/") + "/") for e in excluded):
                continue
            try:
                out[rel] = _sha256_of(full)
            except OSError:
                out[rel] = "UNREADABLE"
    return out


def diff_tree(before: Mapping[str, str], after: Mapping[str, str]) -> tuple[str, ...]:
    changed = set()
    for path, digest in after.items():
        if before.get(path) != digest:
            changed.add(path)
    for path in before:
        if path not in after:
            changed.add(path)
    return tuple(sorted(changed))


# ---------------------------------------------------------------------------
# Subprocess worker coordination, fault, and late-result handling.
# ---------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True, slots=True)
class WorkerResult:
    worker_id: str
    exit_code: int | None
    signalled: str | None
    stdout: str
    stderr: str
    started_at: str
    ended_at: str
    arrived_after_terminal: bool


class WorkerPool:
    """Coordinates real ``python3`` (or any argv) worker subprocesses.

    Each worker runs in its own process group (``start_new_session=True``) so
    :meth:`cancel` can signal the whole subtree it may have spawned, never just
    the immediate child.
    """

    def __init__(self, *, cwd: pathlib.Path, timeout_s: float = 30.0) -> None:
        self._cwd = pathlib.Path(cwd)
        self._timeout_s = timeout_s
        self._procs: dict[str, subprocess.Popen] = {}
        self._order: list[str] = []
        self._started_at: dict[str, str] = {}
        self._terminal_marked: dict[str, bool] = {}
        self._collected: set[str] = set()
        self._closed = False

    def spawn(self, worker_id: str, argv: Sequence[str]) -> int:
        if worker_id in self._procs:
            raise ValueError(f"worker_id {worker_id!r} already spawned in this pool")
        proc = subprocess.Popen(
            list(argv), cwd=str(self._cwd),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            start_new_session=True,
        )
        self._procs[worker_id] = proc
        self._order.append(worker_id)
        self._started_at[worker_id] = now_rfc3339()
        self._terminal_marked[worker_id] = False
        return proc.pid

    def pids(self) -> frozenset[int]:
        return frozenset(p.pid for p in self._procs.values() if p.pid is not None)

    def cancel(self, worker_id: str) -> None:
        proc = self._procs[worker_id]
        self._terminal_marked[worker_id] = True
        if proc.poll() is None:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                pass

    def collect(self) -> tuple[WorkerResult, ...]:
        """Deterministic order = spawn order, independent of completion order."""
        results = []
        for wid in self._order:
            if wid in self._collected:
                continue
            proc = self._procs[wid]
            marked_before = self._terminal_marked[wid]
            try:
                stdout, stderr = proc.communicate(timeout=self._timeout_s)
            except subprocess.TimeoutExpired:
                self._terminal_marked[wid] = True
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
                stdout, stderr = proc.communicate()
            ended_at = now_rfc3339()
            code = proc.returncode
            signalled = None
            exit_code: int | None = code
            if code is not None and code < 0:
                try:
                    signalled = signal.Signals(-code).name
                except ValueError:
                    signalled = f"SIG{-code}"
                exit_code = None
            arrived_after_terminal = marked_before or self._terminal_marked[wid]
            self._collected.add(wid)
            results.append(WorkerResult(
                worker_id=wid,
                exit_code=exit_code,
                signalled=signalled,
                stdout=stdout or "",
                stderr=stderr or "",
                started_at=self._started_at[wid],
                ended_at=ended_at,
                arrived_after_terminal=arrived_after_terminal,
            ))
        return tuple(results)

    def close(self) -> None:
        """Reap everything; idempotent."""
        if self._closed:
            return
        for wid, proc in self._procs.items():
            if proc.poll() is None:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
            except Exception:
                pass
            for stream in (proc.stdout, proc.stderr):
                if stream is not None:
                    try:
                        stream.close()
                    except OSError:
                        pass
        self._closed = True


def leaked_pids(before: frozenset[int], after: frozenset[int]) -> frozenset[int]:
    return frozenset(after) - frozenset(before)


def _live_descendant_pids(root_pid: int) -> frozenset[int]:
    """Process-tree accounting: every live pid descended from ``root_pid``.

    Walks ``/proc`` once, builds the full parent->children map, then does a BFS
    from ``root_pid`` so a worker that itself forked a grandchild is still
    caught by :func:`leaked_pids` if that grandchild survives past cleanup.
    Linux-only (this environment's only supported platform); returns an empty
    set if ``/proc`` is unavailable rather than raising, since leak accounting
    degrading to "nothing observed" is a safe (fail-visible, not fail-silent)
    default for a helper that is not itself a pass/fail gate.
    """
    try:
        pid_dirs = [p for p in os.listdir("/proc") if p.isdigit()]
    except FileNotFoundError:
        return frozenset()
    children: dict[int, list[int]] = {}
    for p in pid_dirs:
        pid = int(p)
        try:
            with open(f"/proc/{p}/stat", encoding="utf-8", errors="replace") as fh:
                stat = fh.read()
        except OSError:
            continue
        try:
            after_comm = stat.rsplit(")", 1)[1].split()
            ppid = int(after_comm[1])
        except (IndexError, ValueError):
            continue
        children.setdefault(ppid, []).append(pid)
    seen: set[int] = set()
    frontier = [root_pid]
    while frontier:
        cur = frontier.pop()
        for child in children.get(cur, ()):
            if child not in seen:
                seen.add(child)
                frontier.append(child)
    return frozenset(seen)
