#!/usr/bin/env python3
"""Fail before model calls if selection or the capture launcher is broken."""
import argparse
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]

def preflight(root, selected="", bash=None):
    if bash is None:
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
        from ci.host_tools import select_bash
        bash = select_bash()
    root = Path(root).resolve()
    discovery = subprocess.run([bash, "evals/paid/discover-paid-packs.sh", "promptfoo"],
                               cwd=root, capture_output=True, text=True, check=True)
    allowed = json.loads(discovery.stdout)
    chosen = selected.split() if selected.strip() else allowed
    if not chosen or len(chosen) != len(set(chosen)):
        raise ValueError("selection must be nonempty and contain no duplicates")
    if any(not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) or name not in allowed for name in chosen):
        raise ValueError("selection includes an unknown, retired or unpacked plugin")
    tracked = subprocess.check_output(["git", "ls-files", "--stage", "--", "evals/paid/capture-example.sh"],
                                      cwd=root, text=True).strip()
    if not tracked.startswith("100755 "):
        raise ValueError("capture-example.sh must be tracked executable (100755); no model calls started")
    launch = subprocess.run([bash, "evals/paid/capture-example.sh", "--help"],
                            cwd=root, capture_output=True, text=True, check=False)
    if launch.returncode != 0 or not launch.stdout.startswith("usage: capture-example.sh"):
        raise ValueError("capture launcher probe failed; no model calls started")
    return {"plugins": chosen, "capture_mode": "100755", "launch": "bash evals/paid/capture-example.sh --help",
            "model_calls": 0}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selected", default="")
    parser.add_argument("--bash", default=None, help="Bash executable (override for Git Bash on Windows)")
    parser.add_argument("--github-output", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        result = preflight(ROOT, args.selected, args.bash)
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        parser.exit(1, f"refresh preflight: {exc}\n")
    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as out:
            out.write("plugins=" + json.dumps(result["plugins"], separators=(",", ":")) + "\n")
            out.write("selected=" + " ".join(result["plugins"]) + "\n")
    if args.report:
        args.report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("refresh preflight: capture launch and " + str(len(result["plugins"])) + " selected packs verified; no model calls")
    return 0

if __name__ == "__main__": raise SystemExit(main())
