#!/usr/bin/env python3
"""Verify locked package/lifecycle policy without initializing an evaluator."""
import argparse
import hashlib
import json
from pathlib import Path


def check(root, modules=None):
    package = json.loads((root / "ci/tools/package.json").read_text(encoding="utf-8"))
    lock = json.loads((root / "ci/tools/package-lock.json").read_text(encoding="utf-8"))
    policy = json.loads((root / "ci/tools/lifecycle-policy.json").read_text(encoding="utf-8"))
    problems = []
    if package["dependencies"] != lock["packages"][""]["dependencies"]:
        problems.append("direct dependencies differ from lock")
    actual = {name.removeprefix("node_modules/"): value["version"] for name, value in lock["packages"].items() if value.get("hasInstallScript")}
    if actual != {name: value["version"] for name, value in policy["packages"].items()}:
        problems.append("lifecycle inventory differs from reviewed policy")
    if any(not isinstance(value.get("run_installer"), bool) for value in policy["packages"].values()):
        problems.append("installer decisions must be explicit booleans")
    allowed = [name for name, value in policy["packages"].items() if value.get("run_installer") is True]
    if allowed != ["@anthropic-ai/claude-code"]:
        problems.append("only the reviewed Claude platform-copy installer may run")
    for name, value in lock["packages"].items():
        if name and (not value.get("resolved", "").startswith("https://registry.npmjs.org/") or not value.get("integrity")):
            problems.append("unqualified package source: " + name)
        if name.endswith("node_modules/simple-git") and value["version"] != "4.0.1":
            problems.append("simple-git advisory override missing")
        if name.endswith("node_modules/@simple-git/argv-parser") and value["version"] != "2.0.1":
            problems.append("argv-parser advisory override missing")
    if modules:
        approved = policy["approved_installer"]
        path = modules / approved["package"] / approved["path"]
        if not path.resolve().is_relative_to(modules.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != approved["sha256"]:
            problems.append("approved installer source/hash mismatch")
    return problems


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--modules", type=Path)
    args = parser.parse_args()
    errors = check(args.root, args.modules)
    print("\n".join(errors) if errors else "Locked tool/lifecycle policy: PASS")
    raise SystemExit(bool(errors))
