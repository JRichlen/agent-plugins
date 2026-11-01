#!/usr/bin/env python3
"""Validate explicit comparison cells and emit a dry-run receipt. Never call a model."""
import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def number(value, label, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(label + " must be an integer >= " + str(minimum))
    return value


def keys(value, allowed, label):
    if not isinstance(value, dict) or set(value) != set(allowed):
        raise ValueError(label + " has missing or unknown fields")


def plan(models, suites, experiment, read_source):
    keys(models, ("schema_version", "models"), "model registry")
    keys(suites, ("schema_version", "suites"), "suite registry")
    keys(experiment, ("schema_version", "limits", "cells"), "experiment")
    if any(data.get("schema_version") != 1 for data in (models, suites, experiment)):
        raise ValueError("unsupported schema version")
    registry = models["models"]
    definitions = suites["suites"]
    for model in registry.values():
        keys(model, ("provider", "revision", "family", "roles", "effort", "tokenizer", "compatibility", "pricing"), "model")
        if not isinstance(model["provider"], str) or not model["provider"] or not isinstance(model["family"], str) or not model["family"] or not isinstance(model["roles"], list) or not model["roles"] or not set(model["roles"]) <= {"subject", "judge"}:
            raise ValueError("model needs an explicit provider, family and supported roles")
    limits = experiment["limits"]
    keys(limits, ("subject_attempts", "judge_attempts", "estimated_usd"), "limits")
    caps = {role: number(limits[role + "_attempts"], role + " attempts") for role in ("subject", "judge")}
    budget = Decimal(str(limits["estimated_usd"]))
    if not budget.is_finite() or budget < 0:
        raise ValueError("estimated_usd must be finite and nonnegative")
    totals = {"subject": 0, "judge": 0}
    estimates = []
    cells = []
    seen = set()
    for cell in experiment["cells"]:
        expected = {"id", "suite", "subject", "judge", "cases", "arms", "repeats", "max_attempts", "execution_mode", "token_bounds"}
        if cell.get("execution_mode") == "replay":
            expected.add("saved_outputs")
        keys(cell, expected, "cell")
        keys(cell["token_bounds"], ("subject_input", "subject_output", "judge_input", "judge_output"), "token bounds")
        if cell["id"] in seen:
            raise ValueError("duplicate cell: " + cell["id"])
        seen.add(cell["id"])
        suite = definitions[cell["suite"]]
        if not re.fullmatch(r"[0-9a-f]{40}", suite["source_commit"]):
            raise ValueError("suite source must be an immutable commit")
        for path, expected in suite["files"].items():
            if PurePosixPath(path).is_absolute() or ".." in PurePosixPath(path).parts or "\\" in path:
                raise ValueError("unsafe suite path")
            if hashlib.sha256(read_source(suite["source_commit"], path)).hexdigest() != expected:
                raise ValueError("frozen suite drift: " + path)
        cases = cell["cases"]
        arms = cell["arms"]
        if not cases or len(cases) != len(set(cases)) or not set(cases) <= set(suite["cases"]):
            raise ValueError("select unique explicit suite cases")
        if not arms or len(arms) != len(set(arms)) or not set(arms) <= set(suite["arms"]):
            raise ValueError("select unique explicit suite arms")
        subject, judge = registry[cell["subject"]], registry[cell["judge"]]
        if "subject" not in subject["roles"] or "judge" not in judge["roles"]:
            raise ValueError("model role mismatch")
        if subject["family"] == judge["family"]:
            raise ValueError("same-family self-grading is not allowed")
        mode = cell["execution_mode"]
        if mode not in ("sync", "provider_batch", "replay"):
            raise ValueError("unknown execution mode")
        if mode == "provider_batch":
            raise ValueError("provider_batch is unsupported by the pinned execution path; no sync fallback")
        observations = len(cases) * len(arms) * number(cell["repeats"], "repeats", 1)
        attempts = number(cell["max_attempts"], "max_attempts", 1)
        counts = {"subject": 0 if mode == "replay" else observations * attempts,
                  "judge": observations * attempts}
        if mode == "replay":
            saved = cell.get("saved_outputs") or {}
            if not saved.get("path") or not re.fullmatch(r"[0-9a-f]{64}", saved.get("sha256", "")):
                raise ValueError("saved-output comparison needs exact file identity")
        estimated = Decimal(0)
        unknown_price = False
        for role, model in (("subject", subject), ("judge", judge)):
            totals[role] += counts[role]
            pricing = model.get("pricing") or {}
            for direction in ("input", "output"):
                tokens = number(cell["token_bounds"][role + "_" + direction], role + " token bound")
                rate = pricing.get(direction + "_per_million")
                if counts[role] and rate is None:
                    unknown_price = True
                elif rate is not None:
                    price = Decimal(str(rate))
                    if not price.is_finite() or price < 0:
                        raise ValueError("invalid price")
                    estimated += counts[role] * tokens * price / Decimal(1000000)
        estimates.append(None if unknown_price else estimated)
        identity = hashlib.sha256(canonical({"cell": cell, "suite": suite, "subject": subject, "judge": judge})).hexdigest()
        cells.append({"id": cell["id"], "identity": identity, "state": "planned", "attempt_bounds": counts,
                      "estimated_usd": None if unknown_price else str(estimated),
                      "suite_kind": suite["kind"], "execution_mode": mode,
                      "suite": {"id": cell["suite"], "source_commit": suite["source_commit"], "files": suite["files"]},
                      "models": {"subject": subject, "judge": judge},
                      "selection": {key: cell[key] for key in ("cases", "arms", "repeats", "max_attempts", "token_bounds")},
                      "human_gold_status": suite.get("human_gold_status", "not established"),
                      "holdout_status": suite.get("holdout_status", "not established"),
                      "limits": ["No execution adapter is enabled.", "Live compatibility and human calibration are not established."]})
    if any(totals[role] > caps[role] for role in totals):
        raise ValueError("selected cells exceed attempt cap")
    total = None if any(value is None for value in estimates) else sum(estimates, Decimal(0))
    if total is not None and total > budget:
        raise ValueError("estimated token-bound cost exceeds cap")
    return {"schema_version": 1, "execution_enabled": False, "cells": cells,
            "attempt_bounds": totals, "estimated_usd": None if total is None else str(total),
            "budget_check": "unknown" if total is None else "within declared estimate cap",
            "estimate_limit": "Token/rate estimate only, not billed cost or execution authority; unknown prices remain unknown.",
            "config_sha256": hashlib.sha256(canonical([models, suites, experiment])).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", type=Path, default=Path(__file__).with_name("models.json"))
    parser.add_argument("--suites", type=Path, default=Path(__file__).with_name("suites.json"))
    parser.add_argument("--experiment", type=Path, default=Path(__file__).with_name("comparison.json"))
    parser.add_argument("--receipt", type=Path, help="new output file only; no overwrite")
    args = parser.parse_args()
    def source(commit, path):
        return subprocess.check_output(["git", "-C", str(ROOT), "show", commit + ":" + path])
    receipt = plan(*(json.loads(path.read_text(encoding="utf-8")) for path in (args.models, args.suites, args.experiment)), source)
    rendered = json.dumps(receipt, indent=2) + "\n"
    if args.receipt:
        with args.receipt.open("x", encoding="utf-8", newline="\n") as out:
            out.write(rendered)
    print(rendered, end="")


if __name__ == "__main__":
    main()
