#!/usr/bin/env python3
"""One MCP computation tool, confined to a fresh row's task workspace.

The model supplies a command only. The coordinator fixes the card and workspace
at startup; inputs come from the same validated declaration as the prompt.
Commands reuse the corpus bubblewrap sandbox, never execute on the host, and
cannot read homes, credentials, undeclared plugin skills, hidden graders,
reference fixtures or network endpoints.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SERVER_NAME = "task_compute"
ALLOWED_TOOL = "mcp__task_compute__run"
NATIVE_ARGV = ("--tools", "", "--setting-sources", "", "--disable-slash-commands")
MAX_COMMAND_BYTES = 65_536
MAX_OUTPUT_BYTES = 100_000


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _workspace(path):
    value = pathlib.Path(path)
    if not value.is_absolute() or value.is_symlink() or not value.is_dir():
        raise ValueError("workspace must be an existing absolute directory without symlinks")
    if value.resolve() != value or any(value.iterdir()):
        raise ValueError("task workspace must be canonical and empty at server startup")
    return value


class TaskTools:
    def __init__(self, workspace, card_id):
        self.workspace = _workspace(workspace)
        task = _load(ROOT / "evals/redteam/bin/verify_task.py", "task_tool_inputs")
        self.outcome = task.load_outcome()
        files = task.safe_files(task.task_inputs(card_id))
        self.inputs = tempfile.TemporaryDirectory(prefix="task-inputs-", dir=self.workspace.parent)
        for name, contents in files.items():
            path = pathlib.Path(self.inputs.name) / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(contents, encoding="utf-8")

    def close(self):
        self.inputs.cleanup()

    def run(self, arguments):
        if not isinstance(arguments, dict) or set(arguments) != {"command"}:
            raise ValueError("run accepts only command; paths and card identity are fixed by the coordinator")
        command = arguments["command"]
        if not isinstance(command, str) or not command.strip() or "\x00" in command:
            raise ValueError("command must be a nonempty string without NUL bytes")
        if len(command.encode("utf-8")) > MAX_COMMAND_BYTES:
            raise ValueError("command exceeds 64 KiB")
        # Limits are installed inside the sandbox before interpreting the
        # command; passing it as $1 avoids any host-side shell interpolation.
        argv = ["bash", "-c", "ulimit -t 10; ulimit -f 4096; ulimit -v 524288; exec bash -c \"$1\"",
                "task-compute", command]
        try:
            result = self.outcome._sandbox(ROOT, self.workspace, argv,
                                           readonly_inputs=pathlib.Path(self.inputs.name),
                                           expose_grading_code=False, output_limit_bytes=MAX_OUTPUT_BYTES)
            data = {"exit_code": result.returncode, "stdout": result.stdout,
                    "stderr": result.stderr, "output_truncated": result.output_truncated}
        except subprocess.TimeoutExpired:
            data = {"exit_code": 124, "stdout": "", "stderr": "sandbox command timed out after 20 seconds",
                    "output_truncated": False}
        except (OSError, RuntimeError) as exc:
            # No host fallback. A missing sandbox is an actual tool failure.
            data = {"exit_code": None, "stdout": "", "stderr": "sandbox unavailable: " + str(exc),
                    "output_truncated": False}
        data["scope"] = "isolated task computation; /inputs read-only, /work writable, no network"
        return {"content": [{"type": "text", "text": json.dumps(data)}],
                "structuredContent": data, "isError": data["exit_code"] != 0}

    def request(self, request):
        method = request.get("method")
        params = request.get("params") or {}
        if method == "initialize":
            version = params.get("protocolVersion")
            if version not in {"2024-11-05", "2025-03-26", "2025-06-18"}:
                version = "2025-06-18"
            return {"protocolVersion": version, "capabilities": {"tools": {}},
                    "serverInfo": {"name": SERVER_NAME, "version": "1"}}
        if method == "ping":
            return {}
        if method == "tools/list":
            return {"tools": [{"name": "run",
                    "description": "Run a shell command in the isolated task sandbox. Explicit task inputs: /inputs (read-only). Persistent scratch and outputs: /work. Python and bash are available. No home, host filesystem, undeclared plugin skills, hidden grading code, credentials or network access.",
                    "inputSchema": {"type": "object", "properties": {"command": {"type": "string"}},
                                    "required": ["command"], "additionalProperties": False},
                    "annotations": {"readOnlyHint": False, "destructiveHint": True,
                                    "idempotentHint": False, "openWorldHint": False}}]}
        if method == "tools/call":
            if params.get("name") != "run":
                raise ValueError("unknown computation tool")
            return self.run(params.get("arguments"))
        raise LookupError("method not found")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--card-id", required=True)
    args = parser.parse_args()
    tools = TaskTools(args.workspace, args.card_id)
    try:
        for line in sys.stdin:
            request = None
            try:
                request = json.loads(line)
                if not isinstance(request, dict) or request.get("jsonrpc") != "2.0":
                    raise ValueError("expected JSON-RPC 2.0 object")
                if "id" not in request:
                    continue
                response = {"jsonrpc": "2.0", "id": request["id"], "result": tools.request(request)}
            except (ValueError, TypeError, LookupError) as exc:
                response = {"jsonrpc": "2.0", "id": request.get("id") if isinstance(request, dict) else None,
                            "error": {"code": -32602, "message": str(exc)}}
            print(json.dumps(response), flush=True)
    finally:
        tools.close()


if __name__ == "__main__":
    main()
