#!/usr/bin/env python3
"""PreToolUse hook: compiled artifacts are never hand-edited.

Every file the renderer emits carries a header marker with its image hash.
If a Write/Edit/MultiEdit targets an existing file bearing that marker, the
edit is denied with the fix (edit the registry module, recompile, re-render).
Everything else is allowed silently — this guard fires only on the one
mutation the plugin's invariant forbids, never on ordinary files.

Protocol: hook JSON on stdin; JSON permission decision on stdout; exit 0.
Fail open on malformed input — a broken hook must never block unrelated work.
"""

import json
import os
import sys

MARKER = "compiled by agent-compiler; imageHash:"


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 — fail open
        return 0
    tool = payload.get("tool_name", "")
    if tool not in ("Write", "Edit", "MultiEdit"):
        return 0
    path = (payload.get("tool_input") or {}).get("file_path", "")
    if not path or not os.path.isfile(path):
        return 0
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            head = f.read(4096)
    except OSError:
        return 0
    if MARKER not in head:
        return 0
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                f"{os.path.basename(path)} is a compiled agent-compiler "
                "artifact (see its imageHash header) — hand-edits break "
                "provenance and are overwritten by the next render. Edit the "
                "registry behavior/view modules instead, then recompile and "
                "re-render (MCP tools: compile, render; or "
                "scripts/compile.py + scripts/render_claude_agent.py)."),
        }
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
