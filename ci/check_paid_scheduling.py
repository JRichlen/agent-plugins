#!/usr/bin/env python3
"""Check the paid subject-call schedule without running models.

The repository's workflow uses a deliberately small YAML shape: named jobs,
flow-list needs, scalar strategy fields, and inline/block run steps. Unknown
shapes fail closed. This freezes scheduling and selection, not trial counts,
models, graders, or statistical thresholds. --self-test mutates the actual
workflow in memory; it never edits the workflow or starts a paid evaluation.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import shlex
import sys

WORKFLOW = pathlib.Path(".github/workflows/evals.yml")
FORK_GATE = "github.event_name != 'pull_request' || github.event.pull_request.head.repo.full_name == github.repository"
BEHAVIOR_GATE = (
    "!cancelled() && needs.behavioral-detect.result == 'success' && "
    "needs.grader-model.result == 'success' && "
    "needs.behavioral-detect.outputs.plugins != '[]' && (" + FORK_GATE + ")"
)


def _block(text: str, pattern: str, label: str) -> str:
    lines = text.splitlines()
    matches = [i for i, line in enumerate(lines) if re.fullmatch(pattern, line)]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {label}, found {len(matches)}")
    start = matches[0]
    indent = len(lines[start]) - len(lines[start].lstrip())
    end = start + 1
    while end < len(lines):
        line = lines[end]
        if line.strip() and not line.lstrip().startswith("#"):
            if len(line) - len(line.lstrip()) <= indent:
                break
        end += 1
    return "\n".join(lines[start:end])


def _job(text: str, name: str) -> str:
    return _block(text, rf"  {re.escape(name)}:", f"job {name}")


def _field(block: str, key: str, indent: int) -> str:
    value = _block(block, rf" {{{indent}}}{re.escape(key)}:.*", f"{key} field")
    first, *rest = value.splitlines()
    scalar = first.split(":", 1)[1].strip()
    if scalar in (">", ">-", "|", "|-"):
        return "\n".join(line.strip() for line in rest if not line.lstrip().startswith("#"))
    return scalar


def _expression(text: str) -> str:
    text = text.strip()
    if text.startswith("${{") and text.endswith("}}"):
        text = text[3:-2]
    return re.sub(r"\s+", "", text)


def check_text(text: str) -> list[str]:
    problems = []
    try:
        behavior, routing = _job(text, "behavioral-run"), _job(text, "routing-eval")
        needs = _field(behavior, "needs", 4)
        if not re.fullmatch(r"\[[a-z0-9_, -]+\]", needs):
            raise ValueError("behavioral needs must be an explicit flow list")
        names = [name.strip() for name in needs[1:-1].split(",")]
        if sorted(names) != ["behavioral-detect", "grader-model", "routing-eval"]:
            problems.append("behavioral-run must wait for detect, grader-model, and routing-eval")
        if _expression(_field(behavior, "if", 4)) != _expression(BEHAVIOR_GATE):
            problems.append("behavioral condition must retain !cancelled(), detect/grader success, nonempty packs, and fork filtering; routing failure must not skip packs")
        if _expression(_field(routing, "if", 4)) != _expression(FORK_GATE):
            problems.append("routing fork filter changed")
        strategy = _block(behavior, r"    strategy:", "behavioral strategy")
        if _field(strategy, "max-parallel", 6) != "1":
            problems.append("behavioral max-parallel must be 1")
        if _field(strategy, "fail-fast", 6) != "false":
            problems.append("behavioral fail-fast must stay false so one failed pack cannot cancel others")

        for name, job, expected_count, selected in (
            ("behavioral-run", behavior, 1, "paid"),
            ("routing-eval", routing, 2, "routing"),
        ):
            count = 0
            for step in re.split(r"(?m)^      - ", job)[1:]:
                if not re.search(r"(?m)^        run:", step):
                    continue
                script = _field(step, "run", 8).replace("\\\n", " ")
                for line in script.splitlines():
                    if "npx" not in line or line.lstrip().startswith("#"):
                        continue
                    lexer = shlex.shlex(line, posix=True, punctuation_chars=";&|")
                    lexer.whitespace_split = True
                    tokens = list(lexer)
                    if not tokens or tokens[0] != "npx":
                        continue
                    if tokens[:4] != ["npx", "--yes", "promptfoo@0.122.0", "eval"]:
                        problems.append(f"{name}: unrecognized subject eval command")
                        continue
                    count += 1
                    # Only command arguments count: an echo or comment after
                    # a shell operator cannot masquerade as a concurrency cap.
                    args = tokens[4:]
                    end = next((i for i, token in enumerate(args) if token in ("||", "&&", ";", "&", "|")), len(args))
                    args = args[:end]
                    limits = []
                    for i, token in enumerate(args):
                        if token == "--max-concurrency":
                            limits.append(args[i + 1] if i + 1 < len(args) else "missing")
                        elif token.startswith("--max-concurrency="):
                            limits.append(token.split("=", 1)[1])
                    if limits != ["1"]:
                        problems.append(f"{name} subject eval {count}: require exactly one --max-concurrency 1")
                    if _expression(_field(step, "if", 8)) != _expression(f"steps.touched.outputs.{selected} == 'true'"):
                        problems.append(f"{name} subject eval {count}: changed-path selection must remain enabled")
            if count != expected_count:
                problems.append(f"{name}: expected {expected_count} subject eval command(s), found {count}")
    except (ValueError, IndexError) as error:
        problems.append(str(error))
    return problems


def _replace(text: str, old: str, new: str, occurrence: int = 0) -> str:
    matches = list(re.finditer(re.escape(old), text))
    if occurrence >= len(matches):
        raise ValueError(f"self-test mutation target absent: {old!r}")
    match = matches[occurrence]
    return text[:match.start()] + new + text[match.end():]


def self_test(text: str) -> list[str]:
    problems = [f"positive workflow: {p}" for p in check_text(text)]
    mutations = [
        ("missing routing dependency", "behavioral-detect, grader-model, routing-eval", "behavioral-detect, grader-model"),
        ("implicit success gate", "!cancelled() &&", ""),
        ("routing failure suppresses packs", "!cancelled() &&", "!cancelled() && needs.routing-eval.result == 'success' &&"),
        ("missing detect prerequisite", "needs.behavioral-detect.result == 'success' &&", ""),
        ("missing grader prerequisite", "needs.grader-model.result == 'success' &&", ""),
        ("empty matrix filter removed", "needs.behavioral-detect.outputs.plugins != '[]' &&", ""),
        ("fork filter removed", "github.event.pull_request.head.repo.full_name == github.repository", "true"),
        ("parallel packs", "max-parallel: 1", "max-parallel: 3"),
        ("cancel other packs", "fail-fast: false", "fail-fast: true"),
    ]
    behavior = _job(text, "behavioral-run")
    for label, old, new in mutations:
        mutated = text.replace(behavior, _replace(behavior, old, new), 1)
        if not check_text(mutated):
            problems.append(f"counterfeit accepted: {label}")
    for index in range(3):
        for replacement in ("", "--max-concurrency 2", "--max-concurrency 1 --max-concurrency 3"):
            mutated = _replace(text, "--max-concurrency 1", replacement, index)
            if not check_text(mutated):
                problems.append(f"counterfeit accepted: subject command {index + 1}, cap {replacement!r}")
    for job_name, selected in (("behavioral-run", "paid"), ("routing-eval", "routing")):
        job = _job(text, job_name)
        # Mutate the actual subject step, not the earlier setup/announcement
        # steps which deliberately use the same changed-path predicate.
        for step in re.split(r"(?m)^      - ", job)[1:]:
            if re.search(r"^        run:.*npx|^          npx", step, re.MULTILINE):
                changed = _replace(step, f"steps.touched.outputs.{selected} == 'true'", "true")
                if not check_text(text.replace(step, changed, 1)):
                    problems.append(f"counterfeit accepted: {job_name} subject filter removed")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parents[1])
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        text = (args.repo / WORKFLOW).read_text(encoding="utf-8")
        problems = self_test(text) if args.self_test else check_text(text)
    except (OSError, ValueError) as error:
        problems = [str(error)]
    if problems:
        for problem in problems:
            print(f"FAIL paid-scheduling drift: {problem}")
        return 1
    print("PASS paid scheduling " + ("self-test: workflow regressions rejected" if args.self_test else "routing then serialized packs; all 3 subject commands capped at 1; selection preserved"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
