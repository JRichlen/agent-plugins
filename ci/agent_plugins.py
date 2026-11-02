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
import ipaddress
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

PLUGIN_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
MCP_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json"
# §5.2 closed manifest, in the spec's field order.
METADATA = ("version", "description", "author", "homepage", "repository", "license", "keywords")
NAME = re.compile(r"[a-z0-9](?:[a-z0-9.-]{0,62}[a-z0-9])?")
PLACEHOLDERS = {"${CLAUDE_PLUGIN_ROOT}": "${PLUGIN_ROOT}", "${CLAUDE_PLUGIN_DATA}": "${PLUGIN_DATA}"}
SKILL_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
SKILL_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")  # https://agentskills.io/specification
HEADER_NAME = re.compile(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+")  # RFC 9110 token
HEADER_VALUE = re.compile(r"[\t\x20-\x7e\x80-\xff]*")     # no CR, LF, NUL or controls

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


def contained(plugin: Path, relative: str, where: str) -> Path:
    """§4.1: a package path stays inside the resolved plugin root, links included."""
    if ".." in Path(relative).parts:
        raise ValueError(f"{where}: package path traverses upward (§4.1): {relative!r}")
    path = plugin / relative
    if not path.resolve().is_relative_to(plugin.resolve()):
        raise ValueError(f"{where}: package path resolves outside the plugin root (§4.1): {relative!r}")
    return path


def check_url(url: object, where: str) -> str:
    """§7.2.1: absolute HTTP(S), no userinfo or fragment, HTTP only for loopback."""
    try:
        parts = urlsplit(url) if isinstance(url, str) else None
        host = parts.hostname if parts else None
    except ValueError:
        parts = host = None
    if (not parts or parts.scheme not in ("http", "https") or not host or "@" in parts.netloc
            or "#" in url or re.search(r"[\s\\$]", url)):
        raise ValueError(f"{where}: url must be an absolute HTTP(S) URL without userinfo or fragment (§7.2.1)")
    if parts.scheme == "http" and host != "localhost":
        try:
            loopback = ipaddress.ip_address(host).is_loopback
        except ValueError:
            loopback = False
        if not loopback:
            raise ValueError(f"{where}: plain HTTP is allowed only for localhost or a loopback IP (§7.2.1)")
    return url


def check_headers(headers: object, where: str) -> dict:
    """§7.2.1: valid HTTP field names and values, no case-insensitive duplicates."""
    if not isinstance(headers, dict):
        raise ValueError(f"{where}: headers must be an object of strings")
    seen = set()
    for key, value in headers.items():
        if (not HEADER_NAME.fullmatch(key) or not isinstance(value, str)
                or not HEADER_VALUE.fullmatch(value) or key.lower() in seen):
            raise ValueError(f"{where}: invalid or duplicate header {key!r} (§7.2.1)")
        seen.add(key.lower())
    return headers


def server(plugin: Path, name: str, entry: object, where: str) -> dict:
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
        if command.startswith("./"):
            contained(plugin, command, where)
        result = {"type": "stdio", "command": command}
        if "args" in entry:
            if not isinstance(entry["args"], list) or not all(isinstance(arg, str) for arg in entry["args"]):
                raise ValueError(f"{where}: args must be a list of strings")
            result["args"] = [portable(arg, where) for arg in entry["args"]]
        if "env" in entry:
            if not isinstance(entry["env"], dict) or not all(isinstance(v, str) for v in entry["env"].values()):
                raise ValueError(f"{where}: env must map names to strings")
            # §9.2: clients supply these; Windows compares names case-insensitively.
            reserved = [key for key in entry["env"] if key.upper() in ("PLUGIN_ROOT", "PLUGIN_DATA")]
            if reserved or not all(key and "=" not in key for key in entry["env"]):
                raise ValueError(f"{where}: env may not set {reserved or 'empty or = names'} (§9.2)")
            result["env"] = {key: portable(val, where) for key, val in entry["env"].items()}
        if "cwd" in entry:
            cwd = portable(entry["cwd"], where) if isinstance(entry["cwd"], str) else None
            rooted = re.fullmatch(r"\$\{PLUGIN_(ROOT|DATA)\}(/.*)?", cwd or "")
            if cwd and cwd.startswith("./"):
                contained(plugin, cwd, where)
            elif rooted and rooted.group(1) == "ROOT":
                contained(plugin, "." + (rooted.group(2) or ""), where)
            elif not rooted or ".." in Path(rooted.group(2) or "/").parts:
                # The data directory is client-managed; only traversal is checkable here.
                raise ValueError(f"{where}: cwd must stay under ./, ${{PLUGIN_ROOT}} or ${{PLUGIN_DATA}} (§7.2.1)")
            result["cwd"] = cwd
        return result
    if kind in ("http", "streamable-http", "sse"):
        if set(entry) - {"type", "url", "headers"}:
            raise ValueError(f"{where}: unsupported remote fields")
        result = {"type": "sse" if kind == "sse" else "streamable-http", "url": check_url(entry.get("url"), where)}
        if "headers" in entry:
            result["headers"] = check_headers(entry["headers"], where)
        return result
    raise ValueError(f"{where}: unsupported transport {kind!r}")


def mcp(plugin: Path, source: dict, where: str) -> dict | None:
    servers = source.get("mcpServers")
    if isinstance(servers, str):
        path = contained(plugin, servers, where)
        servers = json.loads(path.read_text(encoding="utf-8")).get("mcpServers")
    elif servers is None and (plugin / ".mcp.json").is_file():
        servers = json.loads((plugin / ".mcp.json").read_text(encoding="utf-8")).get("mcpServers")
    if servers is None:
        return None
    if not isinstance(servers, dict):
        raise ValueError(f"{where}: mcpServers must be an object")
    return {"$schema": MCP_SCHEMA,
            "mcpServers": {name: server(plugin, name, entry, where) for name, entry in servers.items()}}


def encode(document: dict) -> bytes:
    return (json.dumps(document, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _scalar(value: str) -> object:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return {"true": True, "false": False}.get(value, value)


def simple_frontmatter(head: str) -> dict:
    """Stdlib fallback for hosts without PyYAML: the subset SKILL.md frontmatter uses —
    scalars, folded/literal blocks, one-level lists and one-level string mappings."""
    result, lines, index = {}, head.split("\n"), 0
    while index < len(lines):
        line = lines[index]
        index += 1
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.fullmatch(r"([A-Za-z][\w-]*):(?: (.*))?", line)
        if not match:
            raise ValueError(f"unsupported frontmatter line: {line!r}")
        key, value = match.group(1), (match.group(2) or "").strip()
        block = []
        while index < len(lines) and (lines[index].startswith(" ") or not lines[index].strip()):
            block.append(lines[index])
            index += 1
        while block and not block[-1].strip():
            block.pop()
        if value in (">", ">-", "|", "|-"):
            body = [item.strip() for item in block]
            result[key] = (" " if value[0] == ">" else "\n").join(body)
        elif value:
            if block:
                raise ValueError(f"unexpected indented lines after {key!r}")
            result[key] = _scalar(value)
        elif block and all(item.strip().startswith("- ") for item in block if item.strip()):
            result[key] = [_scalar(item.strip()[2:]) for item in block if item.strip()]
        else:
            result[key] = {}
            for item in (item for item in block if item.strip()):
                inner = re.fullmatch(r"\s+([\w-]+):\s*(.*)", item)
                if not inner:
                    raise ValueError(f"unsupported nested line under {key!r}: {item!r}")
                result[key][inner.group(1)] = _scalar(inner.group(2))
    return result


def parse_frontmatter(head: str) -> object:
    try:
        import yaml
    except ImportError:
        return simple_frontmatter(head)
    try:
        return yaml.safe_load(head)
    except yaml.YAMLError as error:
        raise ValueError(str(error).splitlines()[0]) from None


def check_skill(skill: Path, where: str) -> None:
    """§7.1: a skill a client would skip for violating the Agent Skills spec fails here."""
    text = skill.read_text(encoding="utf-8").replace("\r\n", "\n")
    head, sep, _ = text[4:].partition("\n---\n")
    try:
        front = parse_frontmatter(head) if text.startswith("---\n") and sep else None
    except ValueError as error:
        raise ValueError(f"{where}: unparseable frontmatter: {error}") from None
    if not isinstance(front, dict):
        raise ValueError(f"{where}: SKILL.md needs a YAML frontmatter mapping")
    problems = [f"unknown field {key!r}" for key in front if key not in SKILL_FIELDS]
    name, description = front.get("name"), front.get("description")
    if (not isinstance(name, str) or not SKILL_NAME.fullmatch(name) or len(name) > 64
            or name != skill.parent.name):
        problems.append(f"name {name!r} must be kebab-case, at most 64 chars and match its directory")
    if not isinstance(description, str) or not 1 <= len(description) <= 1024:
        problems.append("description must be 1-1024 characters")
    if "compatibility" in front and not (isinstance(front["compatibility"], str)
                                         and 1 <= len(front["compatibility"]) <= 500):
        problems.append("compatibility must be 1-500 characters")
    for key in ("license", "allowed-tools"):
        if key in front and not isinstance(front[key], str):
            problems.append(f"{key} must be a string")
    metadata = front.get("metadata", {})
    if not isinstance(metadata, dict) or not all(isinstance(k, str) and isinstance(v, str)
                                                 for k, v in metadata.items()):
        problems.append("metadata must map strings to strings")
    if problems:
        raise ValueError(f"{where}: violates the Agent Skills spec: {'; '.join(problems)}")


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
        # §7.1 discovery: immediate children of skills/ holding a SKILL.md file.
        for skill in sorted((plugin / "skills").glob("*/SKILL.md")):
            if skill.is_file():
                check_skill(skill, skill.relative_to(root).as_posix())
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
