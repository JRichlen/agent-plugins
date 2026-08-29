#!/usr/bin/env python3
"""agent-compiler MCP server: the read-only facade over the kernel.

Exposes exactly the pure operations the design's trust boundary allows —
inspect, compile, explain, render — as MCP tools over stdio. There is no
execute: the server performs no effectful action, writes no files, and makes
no network calls. Every tool call is a pure function of the registry on disk
and the arguments, so results carry the same determinism guarantee as the
CLI (identical inputs → identical AgentImage bytes and hash).

Stdlib-only, like the kernel: JSON-RPC 2.0 over newline-delimited stdio,
implementing the minimal MCP surface (initialize, ping, tools/list,
tools/call). Registry resolution order for each call: explicit `registry`
argument → AGENT_COMPILER_REGISTRY env var → the plugin's bundled registry.

Run directly: python3 mcp_server.py   (speaks MCP on stdin/stdout)
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compile as kernel  # noqa: E402  (the deterministic kernel)
import render_claude_agent as renderer  # noqa: E402

SERVER_NAME = "agent-compiler"
SERVER_VERSION = "0.2.0"
PROTOCOL_VERSION = "2025-06-18"
SUPPORTED_PROTOCOLS = ("2025-06-18", "2025-03-26", "2024-11-05")

DEFAULT_REGISTRY = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "registry"))


def resolve_registry(args):
    return (args.get("registry")
            or os.environ.get("AGENT_COMPILER_REGISTRY")
            or DEFAULT_REGISTRY)


# --- tool implementations (each returns (payload_dict, is_error)) -----------

def tool_inspect(args):
    modules, revision = kernel.load_registry(resolve_registry(args))
    rows = []
    for mid in sorted(modules):
        mod = modules[mid]
        tags = sorted(set(mod["meta"].get("tasks", []))
                      | set(mod["meta"].get("domains", []))
                      | set(mod["meta"].get("roles", [])))
        if args.get("id") and mid != args["id"]:
            continue
        if args.get("kind") and mod["kind"] != args["kind"]:
            continue
        if args.get("tag") and args["tag"] not in tags:
            continue
        rows.append({"id": mid, "kind": mod["kind"], "version": mod["version"],
                     "source": mod["source"], "tags": tags,
                     "requires": sorted(mod["meta"].get("requires", [])),
                     "capabilities": sorted(mod["meta"].get("capabilities", [])),
                     "effects": sorted(mod["meta"].get("effects", [])),
                     "units": [u["id"] for u in mod["units"]]})
    return {"registryRevision": revision, "modules": rows}, False


def tool_compile(args):
    query = args.get("query")
    if not isinstance(query, dict):
        return {"diagnostics": [kernel.diag(
            "BAD_QUERY", "'query' must be an AgentQuery object")]}, True
    image = kernel.compile_image(resolve_registry(args), query)
    return image, False


def tool_explain(args):
    image = args.get("image")
    if not isinstance(image, dict):
        return {"diagnostics": [kernel.diag(
            "BAD_IMAGE", "'image' must be a compiled AgentImage object")]}, True
    unit_id = args.get("unit", "")
    for unit in image.get("behavior", []):
        if unit.get("id") == unit_id:
            return unit, False
    return {"diagnostics": [kernel.diag(
        "UNKNOWN_UNIT", f"unit '{unit_id}' is not in image "
        f"{image.get('hash', '?')}")]}, True


def tool_render(args):
    image = args.get("image")
    if not isinstance(image, dict):
        return {"diagnostics": [kernel.diag(
            "BAD_IMAGE", "'image' must be a compiled AgentImage object")]}, True
    return {"markdown": renderer.render(image) + "\n",
            "imageHash": image.get("hash", ""),
            "rendererVersion": renderer.RENDERER_VERSION}, False


REGISTRY_PROP = {"type": "string", "description":
                 "Registry directory. Defaults to $AGENT_COMPILER_REGISTRY, "
                 "then the plugin's bundled registry."}

TOOLS = [
    {
        "name": "inspect",
        "description": (
            "Pure discovery over the behavior registry: list modules (behavior, "
            "view, capability_interface) with their versions, tags, edges, and "
            "unit ids. Filter by exact id, kind, or tag. Use this to find the "
            "exact module ids a compile query needs — fuzzy discovery may "
            "suggest ids here, but compile consumes exact ids only."),
        "inputSchema": {"type": "object", "properties": {
            "registry": REGISTRY_PROP,
            "id": {"type": "string", "description": "exact module id"},
            "kind": {"type": "string",
                     "enum": ["behavior", "view", "capability_interface"]},
            "tag": {"type": "string",
                    "description": "matches a module's tasks/domains/roles"},
        }},
        "fn": tool_inspect,
    },
    {
        "name": "compile",
        "description": (
            "Deterministically compile a typed AgentQuery into an immutable, "
            "content-hashed AgentImage. Identical inputs yield byte-identical "
            "output and the same hash. Fails closed with structured diagnostics "
            "(CONFLICT, MISSING_DEPENDENCY, DEPENDENCY_CYCLE, EFFECT_CEILING, "
            "NO_EFFECT_CEILING…) — a failed compile produces no image. The "
            "query must carry an effect ceiling (effectCeiling, or a selected "
            "view's max_effects)."),
        "inputSchema": {"type": "object", "properties": {
            "registry": REGISTRY_PROP,
            "query": {"type": "object", "description":
                      "AgentQuery: name, role, task, domains[], views[], "
                      "stance[], environment, risk, effectCeiling[], facts{}"},
        }, "required": ["query"]},
        "fn": tool_compile,
    },
    {
        "name": "explain",
        "description": (
            "Trace one behavior unit of a compiled AgentImage to its "
            "provenance: source module, version, file, and line range."),
        "inputSchema": {"type": "object", "properties": {
            "image": {"type": "object", "description": "a compiled AgentImage"},
            "unit": {"type": "string", "description":
                     "unit id, e.g. security.iam.review#least-privilege"},
        }, "required": ["image", "unit"]},
        "fn": tool_explain,
    },
    {
        "name": "render",
        "description": (
            "Render a compiled AgentImage into a Claude Code agent definition "
            "(markdown). Returns the text — it never writes files; saving the "
            "artifact is the caller's decision."),
        "inputSchema": {"type": "object", "properties": {
            "image": {"type": "object", "description": "a compiled AgentImage"},
        }, "required": ["image"]},
        "fn": tool_render,
    },
]


# --- JSON-RPC / MCP plumbing -------------------------------------------------

def result_content(payload, is_error):
    return {
        "content": [{"type": "text",
                     "text": json.dumps(payload, sort_keys=True, indent=2)}],
        "isError": bool(is_error),
    }


def handle(msg):
    """Return a response dict for a request, or None for a notification."""
    method, msg_id = msg.get("method", ""), msg.get("id")
    if method.startswith("notifications/"):
        return None

    def ok(result):
        return {"jsonrpc": "2.0", "id": msg_id, "result": result}

    def err(code, message):
        return {"jsonrpc": "2.0", "id": msg_id,
                "error": {"code": code, "message": message}}

    if method == "initialize":
        requested = (msg.get("params") or {}).get("protocolVersion", "")
        version = requested if requested in SUPPORTED_PROTOCOLS else PROTOCOL_VERSION
        return ok({
            "protocolVersion": version,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            "instructions": (
                "Read-only facade over the agent-compiler kernel. inspect "
                "finds exact module ids; compile turns a typed AgentQuery "
                "into a hashed AgentImage or structured diagnostics; explain "
                "traces a unit to its source; render emits the agent "
                "markdown. Nothing here has side effects."),
        })
    if method == "ping":
        return ok({})
    if method == "tools/list":
        return ok({"tools": [{k: t[k] for k in
                              ("name", "description", "inputSchema")}
                             for t in TOOLS]})
    if method == "tools/call":
        params = msg.get("params") or {}
        name = params.get("name", "")
        args = params.get("arguments") or {}
        tool = next((t for t in TOOLS if t["name"] == name), None)
        if tool is None:
            return err(-32602, f"unknown tool: {name}")
        try:
            payload, is_error = tool["fn"](args)
        except kernel.CompileError as e:
            payload, is_error = {"diagnostics": e.diagnostics}, True
        except Exception as e:  # noqa: BLE001 — surface, never crash the server
            payload, is_error = {"diagnostics": [kernel.diag(
                "INTERNAL", f"{type(e).__name__}: {e}")]}, True
        return ok(result_content(payload, is_error))
    if msg_id is not None:
        return err(-32601, f"method not found: {method}")
    return None


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            resp = {"jsonrpc": "2.0", "id": None,
                    "error": {"code": -32700, "message": "parse error"}}
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
            continue
        resp = handle(msg)
        if resp is not None:
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
