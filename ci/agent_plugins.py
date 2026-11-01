#!/usr/bin/env python3
"""Project each registered plugin's Claude manifest into Agent Plugins 1.0.0 files.

Agent Plugins 1.0.0 (https://github.com/agentplugins/agent-plugins-spec,
spec/1.0.0.md) requires a closed root `plugin.json` and, for MCP servers, a root
`mcp.json`. `.claude-plugin/plugin.json` stays the edited source; this script
generates the portable copies and `--check` fails on drift or on any rule the
spec makes fatal. Claude-only components (commands, hooks, agents) are outside
the v1 component types and are left where Claude Code discovers them.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import re
import sys

PLUGIN_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
MCP_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json"
# §5.2 closed manifest, in the spec's field order.
METADATA = ("version", "description", "author", "homepage", "repository", "license", "keywords")
NAME = re.compile(r"[a-z0-9](?:[a-z0-9.-]{0,62}[a-z0-9])?")
PLACEHOLDERS = {"${CLAUDE_PLUGIN_ROOT}": "${PLUGIN_ROOT}", "${CLAUDE_PLUGIN_DATA}": "${PLUGIN_DATA}"}

_sync_spec = importlib.util.spec_from_file_location(
    "core_sync", Path(__file__).resolve().parent.parent / "core" / "sync.py")
_sync = importlib.util.module_from_spec(_sync_spec)
_sync_spec.loader.exec_module(_sync)
simple_path, atomic_write = _sync.simple_path, _sync.atomic_write


def check_name(name: object) -> str:
    """§5.5: 1-64 chars of a-z 0-9 - ., alphanumeric ends, no -- or ..."""
    if (not isinstance(name, str) or not NAME.fullmatch(name)
            or "--" in name or ".." in name):
        raise ValueError(f"plugin name violates Agent Plugins §5.5: {name!r}")
    return name


def manifest(source: dict) -> dict:
    result = {"$schema": PLUGIN_SCHEMA, "name": check_name(source.get("name"))}
    for field in METADATA:
        if field not in source:
            continue
        value = source[field]
        if field == "author":
            if not isinstance(value, dict) or set(value) - {"name", "email", "url"}:
                raise ValueError(f"{result['name']}: author may hold only name, email and url (§5.4)")
        elif field == "keywords":
            if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                raise ValueError(f"{result['name']}: keywords must be a list of strings (§5.4)")
        if field == "author":
            if not all(isinstance(item, str) for item in value.values()):
                raise ValueError(f"{result['name']}: author fields must be strings (§5.4)")
        elif field != "keywords" and not isinstance(value, str):
            raise ValueError(f"{result['name']}: {field} must be a string (§5.4)")
        result[field] = value
    return result


def portable(value: str, where: str) -> str:
    for claude, standard in PLACEHOLDERS.items():
        value = value.replace(claude, standard)
    if "${CLAUDE_" in value:
        raise ValueError(f"{where}: Claude-only placeholder has no Agent Plugins equivalent: {value}")
    return value


def server(name: str, entry: object, where: str) -> dict:
    """Map one Claude MCP entry onto the closed stdio / remote variants of §7.2.1."""
    where = f"{where} mcpServers.{name}"
    if not isinstance(entry, dict):
        raise ValueError(f"{where}: server entry must be an object")
    kind = entry.get("type", "stdio" if "command" in entry else None)
    if kind == "stdio":
        if set(entry) - {"type", "command", "args", "env", "cwd"}:
            raise ValueError(f"{where}: unsupported stdio fields {sorted(set(entry) - {'type', 'command', 'args', 'env', 'cwd'})}")
        command = entry.get("command")
        if (not isinstance(command, str) or not command or "$" in command or " " in command
                or ("/" in command and not command.startswith("./"))):
            raise ValueError(f"{where}: command must be one bare executable or ./ path (§7.2.1): {command!r}")
        result = {"type": "stdio", "command": command}
        if "args" in entry:
            if not isinstance(entry["args"], list) or not all(isinstance(arg, str) for arg in entry["args"]):
                raise ValueError(f"{where}: args must be a list of strings")
            result["args"] = [portable(arg, where) for arg in entry["args"]]
        if "env" in entry:
            if not isinstance(entry["env"], dict) or not all(isinstance(v, str) for v in entry["env"].values()):
                raise ValueError(f"{where}: env must map names to strings")
            result["env"] = {key: portable(val, where) for key, val in entry["env"].items()}
        if "cwd" in entry:
            cwd = portable(entry["cwd"], where) if isinstance(entry["cwd"], str) else None
            if not cwd or not (cwd.startswith("./") or re.fullmatch(r"\$\{PLUGIN_(ROOT|DATA)\}(/.*)?", cwd)):
                raise ValueError(f"{where}: cwd must be ./, ${{PLUGIN_ROOT}} or ${{PLUGIN_DATA}} rooted (§7.2.1)")
            result["cwd"] = cwd
        return result
    if kind in ("http", "streamable-http", "sse"):
        if set(entry) - {"type", "url", "headers"}:
            raise ValueError(f"{where}: unsupported remote fields")
        url = entry.get("url")
        if not isinstance(url, str) or not re.match(r"https://|http://(localhost|127\.|\[::1\])", url) or "$" in url:
            raise ValueError(f"{where}: url must be a literal HTTPS (or loopback HTTP) URL (§7.2.1)")
        result = {"type": "sse" if kind == "sse" else "streamable-http", "url": url}
        if "headers" in entry:
            result["headers"] = entry["headers"]
        return result
    raise ValueError(f"{where}: unsupported transport {kind!r}")


def mcp(plugin: Path, source: dict, where: str) -> dict | None:
    servers = source.get("mcpServers")
    if isinstance(servers, str):
        servers = json.loads((plugin / servers).read_text(encoding="utf-8")).get("mcpServers")
    elif servers is None and (plugin / ".mcp.json").is_file():
        servers = json.loads((plugin / ".mcp.json").read_text(encoding="utf-8")).get("mcpServers")
    if servers is None:
        return None
    if not isinstance(servers, dict):
        raise ValueError(f"{where}: mcpServers must be an object")
    return {"$schema": MCP_SCHEMA,
            "mcpServers": {name: server(name, entry, where) for name, entry in servers.items()}}


def encode(document: dict) -> bytes:
    return (json.dumps(document, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def projections(root: Path) -> list[tuple[Path, bytes | None]]:
    """Every expected (path, bytes) pair; bytes None means the file must not exist."""
    marketplace = json.loads((root / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    outputs = []
    for entry in marketplace.get("plugins", []):
        relative = entry.get("source", "")
        if not isinstance(relative, str) or not relative.startswith("./plugins/"):
            raise ValueError(f"unsupported marketplace source for {entry.get('name')!r}: {relative!r}")
        plugin = root / relative[2:]
        source_path = plugin / ".claude-plugin" / "plugin.json"
        simple_path(root, source_path)
        source = json.loads(source_path.read_text(encoding="utf-8"))
        where = source_path.relative_to(root).as_posix()
        if source.get("name") != entry.get("name"):
            raise ValueError(f"{where}: name {source.get('name')!r} != marketplace entry {entry.get('name')!r}")
        skills = source.get("skills", "./skills/")
        if skills not in ("./skills", "./skills/"):
            raise ValueError(f"{where}: skills must live in the fixed ./skills/ location (§6.1)")
        outputs.append((plugin / "plugin.json", encode(manifest(source))))
        servers = mcp(plugin, source, where)
        outputs.append((plugin / "mcp.json", None if servers is None else encode(servers)))
    for path, _ in outputs:
        simple_path(root, path)
    return outputs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--check", action="store_true", help="report drift without writing")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        outputs = projections(root)
        drift = []
        for path, content in outputs:
            current = path.read_bytes().replace(b"\r\n", b"\n") if path.is_file() else None
            if current != content:
                drift.append((path, content))
        if args.check:
            for path, content in drift:
                state = "UNEXPECTED" if content is None else "DRIFT"
                print(f"{state} {path.relative_to(root).as_posix()}")
            if drift:
                print("run: python3 ci/agent_plugins.py", file=sys.stderr)
                return 1
            print(f"agent plugins: {sum(c is not None for _, c in outputs)} portable files in sync")
            return 0
        for path, content in drift:
            if content is None:
                path.unlink()
            else:
                atomic_write(path, content)
        print(f"agent plugins: {len(outputs)} checked, {len(drift)} updated")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"agent plugins: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
