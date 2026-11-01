#!/usr/bin/env python3
"""Offline source-contract checks; not a measurement of model behavior."""
import argparse
import json
import pathlib
import re

FILES = {
    "skill": "skills/delegated-intelligence/SKILL.md",
    "templates": "skills/delegated-intelligence/references/templates.md",
    "recovery": "skills/delegated-intelligence/references/recovery.md",
}
RULES = [
    ("skill", "Invariant", "bounded, self-contained brief and an output owner"),
    ("skill", "Invariant", "No assignment ends with unaccounted workers"),
    ("skill", "Entry and exit", "real worker tool is available"),
    ("skill", "Entry and exit", "Keep small or tightly coupled work direct"),
    ("skill", "Entry and exit", "returned, verified, blocked or stopped"),
    ("skill", "Assign", "Reuse the current task/project record"),
    ("skill", "Assign", "Wayfinder owns persistent plans"),
    ("skill", "Assign", "coordinator, workers, review, retries, duplicated context and handoffs"),
    ("skill", "Assign", "an estimate is not an enforced cap"),
    ("skill", "Assign", "Workers never receive agent-spawning or session-control tools"),
    ("skill", "Assign", "scheduling, messaging and connectors that send or spend"),
    ("skill", "Assign", "disjoint output ownership"),
    ("skill", "Assign", "do not launch downstream work before its dependencies exist"),
    ("skill", "Assign", "one integrator for shared/derived files"),
    ("skill", "Hand back and integrate", "existence, non-empty content, expected change and a diff for unrelated edits"),
    ("skill", "Hand back and integrate", "Then check the acceptance condition"),
    ("skill", "Hand back and integrate", "cannot declare the coordinator's check complete"),
    ("skill", "Hand back and integrate", "Attribute reported findings"),
    ("skill", "Recover or stop", "owns retry accounting, bounds and stop reports"),
    ("skill", "Recover or stop", "no second retry quota"),
    ("skill", "Recover or stop", "stop dispatching, account for in-flight actions and uncertain outcomes"),
    ("recovery", "Inspect before relaunch", "source versions"),
    ("recovery", "Inspect before relaunch", "Preserve a valid completed output"),
    ("recovery", "Limit the repair", "only if it consumed an invalid dependency"),
    ("recovery", "Limit the repair", "same task under stop-rule's accounting"),
    ("recovery", "Interrupts and user stops", "Do not relaunch because a file is missing while a stop remains active"),
    ("recovery", "Return control", "sequential self-review is not an independent check"),
]
FIELDS = {
    "Delegation brief": ("TASK ID:", "OBJECTIVE:", "PURPOSE:", "CONTEXT:", "SCOPE:", "TIER:", "TOOLS ALLOWED:", "CONTROL TOOLS:", "ALLOWANCE:", "OUTPUT PATH:", "RETURN:", "DONE WHEN:", "STOP WHEN:", "IF BLOCKED:"),
    "Return brief": ("TASK ID:", "STATE:", "OUTPUT:", "FINDINGS:", "CHECKS:", "GAPS:", "ALLOWANCE USED:", "NEXT ACTION:"),
}
FORBIDDEN = ("You are the coordinator", "Haiku", "Sonnet", "Opus", "two retries", "automatically for high-stakes", "ENFORCED ALTERNATIVE", "plugins/jori")


def section(text, heading):
    match = re.search(r"^## " + re.escape(heading) + r"\s*$([\s\S]*?)(?=^## |\Z)", text, re.M)
    return " ".join(match.group(1).split()) if match else ""


def failures(texts):
    errors = [f"{key}/{heading}: {clause}" for key, heading, clause in RULES if clause not in section(texts[key], heading)]
    errors += [f"template/{heading}: {field}" for heading, fields in FIELDS.items() for field in fields if field not in section(texts["templates"], heading)]
    body = "\n".join(texts.values()).lower()
    errors += ["retired policy: " + clause for clause in FORBIDDEN if clause.lower() in body]
    if "../../context/OPERATING.md" not in texts["skill"]:
        errors.append("packaged core reference missing")
    return errors


def mutate_section(text, heading, old):
    pattern = r"(^## " + re.escape(heading) + r"\s*$)[\s\S]*?(?=^## |\Z)"
    changed = section(text, heading).replace(old, "REMOVED", 1)
    return re.sub(pattern, lambda m: m.group(1) + "\n\n" + changed + "\n\n", text, count=1, flags=re.M)


def self_test(texts):
    count = 0
    for key, heading, clause in RULES:
        changed = dict(texts)
        changed[key] = mutate_section(texts[key], heading, clause)
        assert f"{key}/{heading}: {clause}" in failures(changed), clause
        count += 1
    for heading, fields in FIELDS.items():
        for field in fields:
            changed = dict(texts)
            changed["templates"] = mutate_section(texts["templates"], heading, field)
            assert f"template/{heading}: {field}" in failures(changed), field
            count += 1
    for clause in FORBIDDEN:
        changed = dict(texts)
        changed["skill"] += "\n" + clause
        assert "retired policy: " + clause in failures(changed), clause
        count += 1
    print(f"mutation controls: {count} rejected; source unchanged")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=pathlib.Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    texts = {key: (args.package / path).read_text(encoding="utf-8") for key, path in FILES.items()}
    errors = failures(texts)
    manifest = json.loads((args.package / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
    if manifest.get("name") != "delegated-intelligence" or manifest.get("version") != "0.2.0":
        errors.append("manifest identity/version")
    if not 0 < len(manifest.get("description", "")) <= 250:
        errors.append("manifest description budget")
    if errors:
        print("contract FAIL: " + "; ".join(errors))
        return 1
    print(f"contract: {len(RULES) + sum(map(len, FIELDS.values()))} operative checks passed")
    if args.self_test:
        self_test(texts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
