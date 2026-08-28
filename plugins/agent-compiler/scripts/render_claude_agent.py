#!/usr/bin/env python3
"""Render a compiled AgentImage into a Claude Code subagent markdown file.

Renderers are versioned SEPARATELY from the compiler: the image hash covers
the canonical AgentImage only, and the rendered artifact records
(imageHash, rendererVersion) in its header so rendering can evolve without
invalidating image identity. This renderer targets Claude Code's
`.claude/agents/<name>.md` format; the same image can be rendered for any
other harness by a sibling renderer (harness-agnostic by design — the image,
not this output format, is the contract).

Usage: render_claude_agent.py --image FILE [--out FILE]
"""

import argparse
import json
import sys

RENDERER_VERSION = "0.1.0"
STRENGTH_ORDER = {"must": 0, "should": 1}


def render(image):
    name = image.get("query", {}).get("name", "compiled-agent")
    query = image.get("query", {})
    lines = []
    lines.append("---")
    lines.append(f"name: {name}")
    role = query.get("role", "agent")
    task = query.get("task", "")
    desc = f"Compiled {role} agent" + (f" for {task}" if task else "")
    lines.append(f"description: {desc}. Effects capped at: "
                 + ", ".join(image.get("effectCeiling", [])) + ".")
    lines.append("---")
    lines.append("")
    lines.append(f"<!-- compiled by agent-compiler; imageHash: {image['hash']}; "
                 f"rendererVersion: {RENDERER_VERSION}; DO NOT EDIT BY HAND — "
                 f"edit the registry modules and recompile -->")
    lines.append("")
    lines.append(f"# {name}")
    lines.append("")
    if query.get("stance"):
        lines.append("Stance: " + ", ".join(query["stance"]) + ".")
        lines.append("")

    rules = [u for u in image["behavior"] if u["kind"] == "rule"]
    probes = [u for u in image["behavior"] if u["kind"] == "probe"]
    examples = [u for u in image["behavior"] if u["kind"] == "example"]
    antipatterns = [u for u in image["behavior"] if u["kind"] == "antipattern"]

    if rules:
        lines.append("## Rules")
        lines.append("")
        for u in sorted(rules, key=lambda u: (STRENGTH_ORDER.get(u.get("strength", "should"), 9), u["id"])):
            tag = u.get("strength", "should").upper()
            lines.append(f"- **{tag}** {u['content']}  <!-- {u['id']} -->")
        lines.append("")
    if probes:
        lines.append("## Probes to run")
        lines.append("")
        for u in probes:
            lines.append(f"- {u['content']}  <!-- {u['id']} -->")
        lines.append("")
    if antipatterns:
        lines.append("## Never")
        lines.append("")
        for u in antipatterns:
            lines.append(f"- {u['content']}  <!-- {u['id']} -->")
        lines.append("")
    if examples:
        lines.append("## Examples")
        lines.append("")
        for u in examples:
            lines.append(f"- {u['content']}  <!-- {u['id']} -->")
        lines.append("")
    if image.get("capabilities"):
        lines.append("## Required capabilities")
        lines.append("")
        lines.append("This agent needs implementations of these provider-independent")
        lines.append("interfaces; wire them to the tools your harness actually exposes:")
        lines.append("")
        for cap in image["capabilities"]:
            lines.append(f"- `{cap}`")
        lines.append("")
        lines.append("Effects this agent may exercise: "
                     + ", ".join(f"`{e}`" for e in image["effects"])
                     + f" (ceiling: {', '.join(image['effectCeiling'])}).")
        lines.append("")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="render_claude_agent.py")
    parser.add_argument("--image", required=True)
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    with open(args.image, encoding="utf-8") as f:
        image = json.load(f)
    rendered = render(image) + "\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(rendered)
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    sys.exit(main())
