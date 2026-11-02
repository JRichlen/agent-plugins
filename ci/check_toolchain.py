#!/usr/bin/env python3
"""Verify locked package/lifecycle policy without initializing an evaluator."""
import argparse
import hashlib
import json
from pathlib import Path

DIST_ALGORITHM = "sha256 over UTF-8 'dist/src/<name>  <sha256>\\n' lines, sorted by case-sensitive relative POSIX path, for every dist/src/*.js and dist/src/*.d.ts"


def promptfoo_dist_manifest(home):
    paths = [path for path in (home / "dist/src").iterdir()
             if path.is_file() and path.name.endswith((".js", ".d.ts"))]
    # Path ordering is case-insensitive on Windows. Sort explicit POSIX strings
    # instead so the same package bytes produce the same manifest on every OS.
    paths.sort(key=lambda path: path.relative_to(home).as_posix())
    rows = "".join(f"{path.relative_to(home).as_posix()}  {hashlib.sha256(path.read_bytes()).hexdigest()}\n" for path in paths)
    return hashlib.sha256(rows.encode("utf-8")).hexdigest(), len(paths)


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
        home = modules / "promptfoo"
        pin = json.loads((root / "evals/redteam/pin.json").read_text(encoding="utf-8"))["promptfoo"]
        actual_package = json.loads((home / "package.json").read_text(encoding="utf-8"))
        if actual_package["version"] != pin["version"] or actual_package["version"] != package["dependencies"]["promptfoo"]:
            problems.append("installed Promptfoo version differs from lock/pin")
        if hashlib.sha256((home / "package.json").read_bytes()).hexdigest() != pin["package_json_sha256"]:
            problems.append("Promptfoo package metadata hash differs from pin")
        digest, count = promptfoo_dist_manifest(home)
        if pin["dist_manifest_algo"] != DIST_ALGORITHM or (digest, count) != (pin["dist_manifest_sha256"], pin["dist_manifest_file_count"]):
            problems.append("Promptfoo canonical distribution manifest differs from pin")
    return problems


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--modules", type=Path)
    args = parser.parse_args()
    errors = check(args.root, args.modules)
    print("\n".join(errors) if errors else "Locked tool/lifecycle policy: PASS")
    raise SystemExit(bool(errors))
