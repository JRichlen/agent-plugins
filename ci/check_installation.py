#!/usr/bin/env python3
"""Check advertised starter resources and render their documentation table.

Static declared-resource checks do not qualify native host behavior. This does
not generate plugin manifests, install packages or contact any external service.
"""
import argparse
import json
from pathlib import Path
import re

BEGIN = "<!-- BEGIN INSTALLATION ROUTES -->"
END = "<!-- END INSTALLATION ROUTES -->"


def contained_file(unit, relative):
    if Path(relative).is_absolute():
        raise ValueError("required resource must use a relative path")
    target = (unit / relative).resolve()
    if not target.is_relative_to(unit.resolve()) or not target.is_file():
        raise ValueError("missing or escaping required resource: " + relative)
    return target


def check(root, inventory):
    problems = []
    if inventory.get("schema") != 1 or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", inventory.get("sources_checked", "")):
        problems.append("invalid installation inventory schema/date")
    ids = set()
    for route in inventory["routes"]:
        try:
            if route["id"] in ids:
                raise ValueError("duplicate installation route")
            ids.add(route["id"])
            unit = (root / route["unit"]).resolve()
            if not unit.is_relative_to(root.resolve()):
                raise ValueError("installation unit escapes repository")
            for relative in route["required"]:
                contained_file(unit, relative)
            for relative in route.get("supplemental_repo_files", []):
                contained_file(root, relative)
            if route["evidence_level"] not in ("source-exercised", "structurally-checked", "host-documented"):
                raise ValueError("unknown evidence level")
            if route["evidence_level"] != "source-exercised" and route["qualified_os"]:
                raise ValueError("structural/docs checks cannot qualify a native host")
            if route.get("instruction_only"):
                for name in ("mcp.json", ".mcp.json", "hooks/hooks.json"):
                    if (unit / name).exists():
                        raise ValueError("starter gained a service/hook configuration; review its effects")
                for name in (".claude-plugin/plugin.json", "plugin.json", ".codex-plugin/plugin.json"):
                    if not (unit / name).is_file():
                        continue
                    manifest = json.loads((unit / name).read_text(encoding="utf-8"))
                    overlay = (manifest.get("extensions") or {}).get("com.openai") or {}
                    if any(config.get("hooks") or config.get("mcpServers") for config in (manifest, overlay)):
                        raise ValueError("starter manifest gained service/hook effects")
        except (ValueError, KeyError, OSError) as error:
            problems.append(route.get("id", "unknown") + ": " + str(error))
    return problems


def table(inventory):
    rows = ["| Route | What changes | Evidence here |", "|---|---|---|"]
    for route in inventory["routes"]:
        rows.append("| " + " | ".join(route[key].replace("|", "\\|") for key in ("label", "effects", "evidence")) + " |")
    return "\n".join(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    inventory = json.loads((args.root / "docs/installation-routes.json").read_text(encoding="utf-8"))
    errors = check(args.root, inventory)
    page = args.root / "docs/installation.md"
    text = page.read_text(encoding="utf-8")
    if text.count(BEGIN) != 1 or text.count(END) != 1:
        errors.append("installation table markers missing or duplicated")
    if errors:
        raise SystemExit("\n".join(errors))
    before, rest = text.split(BEGIN)
    _, after = rest.split(END)
    expected = before + BEGIN + "\n" + table(inventory) + "\n" + END + after
    if args.write:
        page.write_text(expected, encoding="utf-8", newline="\n")
    elif text != expected:
        raise SystemExit("installation table drift: run python3 ci/check_installation.py --write")
    print("Installation source/declared-resource checks: PASS (no native qualification)")


if __name__ == "__main__":
    main()
