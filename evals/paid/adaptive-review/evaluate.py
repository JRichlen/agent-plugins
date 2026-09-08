#!/usr/bin/env python3
"""Prepare blind labels and score the frozen adaptive-review experiment."""

import argparse
import hashlib
import json
import statistics
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent


class EvidenceError(ValueError):
    pass


def read_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path, value):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def file_sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def output_id(task_id, text):
    return hashlib.sha256(f"{task_id}\0{text}".encode("utf-8")).hexdigest()


def rendered_prompt(task, template):
    return template.replace("{{input}}", task["input"])


def prompt_sha256(task, template):
    return hashlib.sha256(rendered_prompt(task, template).encode("utf-8")).hexdigest()


def load_contract():
    experiment = read_json(HERE / "experiment.json")
    corpus = read_json(HERE / experiment["corpus"])
    template = (HERE / experiment["prompt_template"]).read_text(encoding="utf-8")
    tasks = {task["id"]: task for task in corpus["tasks"]}
    if len(tasks) != len(corpus["tasks"]):
        raise EvidenceError("corpus contains duplicate task ids")
    held_out = [task for task in corpus["tasks"] if task["split"] == "held-out"]
    if len(held_out) < experiment["thresholds"]["minimum_held_out_pairs"]:
        raise EvidenceError("frozen corpus is smaller than minimum_held_out_pairs")
    return experiment, corpus, template, tasks, held_out


def expected_image_hash(experiment, arm):
    image = read_json(HERE / experiment["arms"][arm]["image"])
    return image["hash"]


def validate_usage(usage, where):
    if not isinstance(usage, dict):
        raise EvidenceError(f"{where}: missing usage")
    for key in ("input_tokens", "output_tokens"):
        value = usage.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise EvidenceError(f"{where}: {key} must be a non-negative integer")
    cost = usage.get("cost_usd")
    if not isinstance(cost, (int, float)) or isinstance(cost, bool) or cost < 0:
        raise EvidenceError(f"{where}: cost_usd must be a known non-negative number")


def validate_run(run):
    experiment, corpus, template, tasks, held_out = load_contract()
    if run.get("schema_version") != "adaptive-review-run/v1":
        raise EvidenceError("run schema_version must be adaptive-review-run/v1")
    if run.get("experiment_id") != experiment["experiment_id"]:
        raise EvidenceError("run experiment_id does not match the frozen experiment")

    provenance = run.get("provenance", {})
    if provenance.get("corpus_sha256") != file_sha256(HERE / experiment["corpus"]):
        raise EvidenceError("run corpus hash does not match the frozen corpus")
    for arm in ("baseline", "candidate"):
        key = f"{arm}_image_hash"
        if provenance.get(key) != expected_image_hash(experiment, arm):
            raise EvidenceError(f"run {key} does not match the compiled image")
    commit = provenance.get("git_commit", "")
    if len(commit) != 40 or any(c not in "0123456789abcdef" for c in commit):
        raise EvidenceError("run git_commit must be a lowercase 40-hex commit")

    actor = run.get("actor", {})
    required = experiment["actor_qualification"]
    checks = {
        "provider": "local",
        "model_family": required["model_family"],
        "context_window": required["context_window"],
        "sequences": required["sequences"],
        "external_fallback": required["external_fallback"],
    }
    for key, expected in checks.items():
        if actor.get(key) != expected:
            raise EvidenceError(f"actor {key} must be {expected!r}")
    if required["model_digest_required"] and not actor.get("model_digest"):
        raise EvidenceError("actor model_digest is required")

    expected_pairs = {(task_id, arm) for task_id in tasks for arm in ("baseline", "candidate")}
    rows = {}
    for row in run.get("outputs", []):
        pair = (row.get("task_id"), row.get("arm"))
        if pair in rows:
            raise EvidenceError(f"duplicate output for {pair}")
        if pair not in expected_pairs:
            raise EvidenceError(f"unexpected task/arm pair {pair}")
        text = row.get("output")
        if not isinstance(text, str) or not text.strip():
            raise EvidenceError(f"{pair}: output must be non-empty text")
        if row.get("output_id") != output_id(pair[0], text):
            raise EvidenceError(f"{pair}: output_id does not match task and output")
        if row.get("prompt_sha256") != prompt_sha256(tasks[pair[0]], template):
            raise EvidenceError(f"{pair}: prompt hash does not match the shared frozen prompt")
        if row.get("agent_image_hash") != expected_image_hash(experiment, pair[1]):
            raise EvidenceError(f"{pair}: agent image hash does not match its arm")
        validate_usage(row.get("usage"), f"{pair}")
        rows[pair] = row
    missing = sorted(expected_pairs - set(rows))
    if missing:
        raise EvidenceError(f"run is missing {len(missing)} task/arm outputs")
    return experiment, corpus, tasks, held_out, rows


def make_blind_sheet(run):
    experiment, _, _, held_out, rows = validate_run(run)
    result = {
        "schema_version": "adaptive-review-human-labels/v1",
        "experiment_id": experiment["experiment_id"],
        "instructions": (
            "Label without identifying arms. For each output set comprehension 1-5, "
            "edits_needed to the minimum substantive edits before posting, acceptable "
            "true/false, and missing_required_ids. Set winner to an output id or tie."
        ),
        "pairs": [],
    }
    for task in held_out:
        task_id = task["id"]
        candidates = [
            {
                "id": rows[(task_id, arm)]["output_id"],
                "text": rows[(task_id, arm)]["output"],
                "comprehension": None,
                "edits_needed": None,
                "acceptable": None,
                "missing_required_ids": [],
            }
            for arm in ("baseline", "candidate")
        ]
        if int(hashlib.sha256(f"{experiment['experiment_id']}:{task_id}".encode()).hexdigest(), 16) % 2:
            candidates.reverse()
        result["pairs"].append({"task_id": task_id, "outputs": candidates, "winner": None})
    return result


def validate_human(sheet, experiment, tasks, held_out, rows):
    if sheet.get("schema_version") != "adaptive-review-human-labels/v1":
        raise EvidenceError("human labels have the wrong schema_version")
    if sheet.get("experiment_id") != experiment["experiment_id"]:
        raise EvidenceError("human labels refer to another experiment")
    pairs = {pair.get("task_id"): pair for pair in sheet.get("pairs", [])}
    labels = {}
    incomplete = []
    for task in held_out:
        task_id = task["id"]
        pair = pairs.get(task_id)
        if not pair:
            incomplete.append(f"human:{task_id}")
            continue
        allowed_ids = {
            item["id"] for group in ("required_facts", "required_actions") for item in task[group]
        }
        expected = {rows[(task_id, arm)]["output_id"] for arm in ("baseline", "candidate")}
        found = {entry.get("id") for entry in pair.get("outputs", [])}
        if found != expected:
            raise EvidenceError(f"human:{task_id}: output ids do not match the run")
        for entry in pair["outputs"]:
            output = next(r for (tid, _), r in rows.items() if tid == task_id and r["output_id"] == entry["id"])
            if entry.get("text") != output["output"]:
                raise EvidenceError(f"human:{task_id}: retained output text changed")
            comprehension = entry.get("comprehension")
            edits = entry.get("edits_needed")
            acceptable = entry.get("acceptable")
            missing = entry.get("missing_required_ids")
            if (
                not isinstance(comprehension, int)
                or isinstance(comprehension, bool)
                or comprehension not in range(1, 6)
                or not isinstance(edits, int)
                or isinstance(edits, bool)
                or edits < 0
                or not isinstance(acceptable, bool)
                or not isinstance(missing, list)
            ):
                incomplete.append(f"human:{task_id}:{entry['id'][:12]}")
                continue
            unknown = set(missing) - allowed_ids
            if unknown:
                raise EvidenceError(f"human:{task_id}: unknown required ids {sorted(unknown)}")
            labels[entry["id"]] = {
                "comprehension": comprehension,
                "edits_needed": edits,
                "acceptable": acceptable,
                "missing_required_ids": sorted(set(missing)),
            }
        if pair.get("winner") not in expected | {"tie"}:
            incomplete.append(f"human:{task_id}:winner")
    return pairs, labels, incomplete


def judge_input_sha256(rows):
    payload = [
        {"output_id": row["output_id"], "output": row["output"]}
        for row in sorted(rows.values(), key=lambda item: item["output_id"])
    ]
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def validate_judge(judge, experiment, tasks, held_out, rows, actor):
    if judge is None:
        return {}, {}, ["judge:missing"], {}
    if judge.get("schema_version") != "adaptive-review-judge-labels/v1":
        raise EvidenceError("judge labels have the wrong schema_version")
    if judge.get("experiment_id") != experiment["experiment_id"]:
        raise EvidenceError("judge labels refer to another experiment")
    meta = judge.get("judge", {})
    if meta.get("tier") != "frontier":
        raise EvidenceError("judge tier must be frontier")
    if meta.get("model_family") == actor.get("model_family"):
        raise EvidenceError("judge must be from a different model family than the actor")
    validate_usage(meta.get("usage"), "judge")
    if meta.get("external"):
        if not meta.get("authorization_id"):
            raise EvidenceError("external judge requires a separate authorization_id")
        if meta.get("authorized_input_sha256") != judge_input_sha256(rows):
            raise EvidenceError("external judge authorization is not bound to the exact output inputs")
        cap = meta.get("max_spend_usd")
        if not isinstance(cap, (int, float)) or isinstance(cap, bool) or cap <= 0:
            raise EvidenceError("external judge requires a positive max_spend_usd")
        if meta["usage"]["cost_usd"] > cap:
            raise EvidenceError("external judge cost exceeds its authorized spending limit")

    pairs = {pair.get("task_id"): pair for pair in judge.get("pairs", [])}
    labels = {}
    incomplete = []
    for task in held_out:
        task_id = task["id"]
        pair = pairs.get(task_id)
        if not pair:
            incomplete.append(f"judge:{task_id}")
            continue
        allowed_ids = {
            item["id"] for group in ("required_facts", "required_actions") for item in task[group]
        }
        expected = {rows[(task_id, arm)]["output_id"] for arm in ("baseline", "candidate")}
        found = {entry.get("id") for entry in pair.get("outputs", [])}
        if found != expected:
            raise EvidenceError(f"judge:{task_id}: output ids do not match the run")
        for entry in pair["outputs"]:
            acceptable = entry.get("acceptable")
            missing = entry.get("missing_required_ids")
            if not isinstance(acceptable, bool) or not isinstance(missing, list):
                incomplete.append(f"judge:{task_id}:{entry['id'][:12]}")
                continue
            unknown = set(missing) - allowed_ids
            if unknown:
                raise EvidenceError(f"judge:{task_id}: unknown required ids {sorted(unknown)}")
            labels[entry["id"]] = acceptable
        if pair.get("winner") not in expected | {"tie"}:
            incomplete.append(f"judge:{task_id}:winner")
    return pairs, labels, incomplete, meta


def cohen_kappa(a, b):
    keys = sorted(set(a) & set(b))
    if len(keys) < 2:
        return None, 0.0, len(keys)
    agree = sum(a[key] == b[key] for key in keys)
    observed = agree / len(keys)
    a_true = sum(a[key] for key in keys) / len(keys)
    b_true = sum(b[key] for key in keys) / len(keys)
    expected = a_true * b_true + (1 - a_true) * (1 - b_true)
    kappa = None if abs(1 - expected) < 1e-12 else (observed - expected) / (1 - expected)
    return kappa, observed, len(keys)


def evaluate(run, human, judge=None):
    experiment, _, tasks, held_out, rows = validate_run(run)
    human_pairs, human_labels, human_missing = validate_human(
        human, experiment, tasks, held_out, rows
    )
    judge_pairs, judge_labels, judge_missing, judge_meta = validate_judge(
        judge, experiment, tasks, held_out, rows, run["actor"]
    )

    missing_evidence = sorted(set(human_missing + judge_missing))
    thresholds = experiment["thresholds"]
    arm_by_id = {row["output_id"]: arm for (_, arm), row in rows.items()}
    wins = {"baseline": 0, "candidate": 0, "tie": 0}
    comprehension_deltas = []
    edit_deltas = []
    candidate_missing = []
    word_deltas = []
    human_complete = not human_missing

    if human_complete:
        for task in held_out:
            task_id = task["id"]
            pair = human_pairs[task_id]
            winner = pair["winner"]
            wins["tie" if winner == "tie" else arm_by_id[winner]] += 1
            baseline_id = rows[(task_id, "baseline")]["output_id"]
            candidate_id = rows[(task_id, "candidate")]["output_id"]
            baseline_label = human_labels[baseline_id]
            candidate_label = human_labels[candidate_id]
            comprehension_deltas.append(
                candidate_label["comprehension"] - baseline_label["comprehension"]
            )
            edit_deltas.append(
                baseline_label["edits_needed"] - candidate_label["edits_needed"]
            )
            candidate_missing.extend(candidate_label["missing_required_ids"])
            word_deltas.append(
                len(rows[(task_id, "baseline")]["output"].split())
                - len(rows[(task_id, "candidate")]["output"].split())
            )

    kappa, agreement, calibration_n = cohen_kappa(
        {key: value["acceptable"] for key, value in human_labels.items()},
        judge_labels,
    )
    winner_agreements = 0
    winner_n = 0
    if not human_missing and not judge_missing:
        for task in held_out:
            winner_n += 1
            winner_agreements += human_pairs[task["id"]]["winner"] == judge_pairs[task["id"]]["winner"]

    actor_usage = {
        "input_tokens": sum(row["usage"]["input_tokens"] for row in rows.values()),
        "output_tokens": sum(row["usage"]["output_tokens"] for row in rows.values()),
        "cost_usd": round(sum(row["usage"]["cost_usd"] for row in rows.values()), 12),
    }
    judge_usage = judge_meta.get("usage") if judge_meta else None
    cutoffs = [
        {"task_id": task_id, "arm": arm, "finish_reason": row.get("finish_reason")}
        for (task_id, arm), row in rows.items()
        if row.get("finish_reason") != "stop"
    ]
    if cutoffs:
        missing_evidence.append("actor:non-stop-finish")

    metrics = {
        "held_out_pairs": len(held_out),
        "wins": wins if human_complete else None,
        "mean_comprehension_lift": (
            sum(comprehension_deltas) / len(comprehension_deltas)
            if comprehension_deltas
            else None
        ),
        "median_edit_reduction": (
            statistics.median(edit_deltas) if edit_deltas else None
        ),
        "mean_word_reduction": (
            sum(word_deltas) / len(word_deltas) if word_deltas else None
        ),
        "candidate_missing_required": len(candidate_missing) if human_complete else None,
        "judge_human_agreement": agreement if calibration_n else None,
        "judge_human_kappa": kappa,
        "judge_human_n": calibration_n,
        "winner_agreement": winner_agreements / winner_n if winner_n else None,
        "actor_usage": actor_usage,
        "judge_usage": judge_usage,
        "cutoffs": cutoffs,
    }

    regression = human_complete and (
        len(candidate_missing) > thresholds["candidate_missing_required_max"]
        or wins["baseline"] > wins["candidate"]
        or metrics["mean_comprehension_lift"] < 0
        or metrics["median_edit_reduction"] < 0
    )
    improvement = (
        not missing_evidence
        and human_complete
        and wins["candidate"] >= thresholds["candidate_wins"]
        and wins["baseline"] <= thresholds["baseline_wins_max"]
        and metrics["mean_comprehension_lift"] >= thresholds["mean_comprehension_lift"]
        and metrics["median_edit_reduction"] >= thresholds["median_edit_reduction"]
        and len(candidate_missing) <= thresholds["candidate_missing_required_max"]
        and agreement >= thresholds["judge_human_agreement"]
        and kappa is not None
        and kappa >= thresholds["judge_human_kappa"]
    )
    if regression:
        outcome = "regression"
        recommendation = "reject-candidate"
    elif improvement:
        outcome = "improvement"
        recommendation = "eligible-for-scoped-human-approval"
    else:
        outcome = "inconclusive"
        recommendation = "do-not-install; collect-or-correct-evidence"

    return {
        "schema_version": "adaptive-review-report/v1",
        "experiment_id": experiment["experiment_id"],
        "outcome": outcome,
        "recommendation": recommendation,
        "automatic_install": False,
        "thresholds": thresholds,
        "metrics": metrics,
        "missing_evidence": sorted(set(missing_evidence)),
        "limitations": [
            "The frozen corpus is small and repository-specific.",
            "Human edit counts and comprehension ratings remain subjective despite blinding.",
            "A passing result qualifies only a review-scoped approval; it does not justify learning or coding transfer."
        ],
    }


def synthetic_run(experiment, corpus, template):
    images = {arm: expected_image_hash(experiment, arm) for arm in ("baseline", "candidate")}
    outputs = []
    for task in corpus["tasks"]:
        for arm in ("baseline", "candidate"):
            text = f"{arm.title()} response for {task['id']} with retained requirements."
            outputs.append(
                {
                    "task_id": task["id"],
                    "arm": arm,
                    "output": text,
                    "output_id": output_id(task["id"], text),
                    "prompt_sha256": prompt_sha256(task, template),
                    "agent_image_hash": images[arm],
                    "finish_reason": "stop",
                    "usage": {"input_tokens": 100, "output_tokens": 20, "cost_usd": 0},
                }
            )
    return {
        "schema_version": "adaptive-review-run/v1",
        "experiment_id": experiment["experiment_id"],
        "provenance": {
            "git_commit": "0" * 40,
            "corpus_sha256": file_sha256(HERE / experiment["corpus"]),
            "baseline_image_hash": images["baseline"],
            "candidate_image_hash": images["candidate"],
        },
        "actor": {
            "provider": "local",
            "model_family": "Qwen 27B",
            "model": "self-test",
            "model_digest": "sha256:" + "0" * 64,
            "context_window": 32768,
            "sequences": 1,
            "external_fallback": False,
        },
        "outputs": outputs,
    }


def fill_labels(sheet, run, mode):
    arm_by_id = {row["output_id"]: row["arm"] for row in run["outputs"]}
    for index, pair in enumerate(sheet["pairs"]):
        ids = {arm_by_id[entry["id"]]: entry["id"] for entry in pair["outputs"]}
        for entry in pair["outputs"]:
            arm = arm_by_id[entry["id"]]
            entry["acceptable"] = arm == "candidate" or index % 2 == 0
            entry["missing_required_ids"] = []
            if mode == "improvement":
                entry["comprehension"] = 5 if arm == "candidate" else 3
                entry["edits_needed"] = 0 if arm == "candidate" else 2
            elif mode == "regression":
                entry["comprehension"] = 2 if arm == "candidate" else 4
                entry["edits_needed"] = 3 if arm == "candidate" else 0
            else:
                entry["comprehension"] = 4
                entry["edits_needed"] = 1
        pair["winner"] = (
            ids["candidate"]
            if mode == "improvement"
            else ids["baseline"]
            if mode == "regression"
            else ("tie" if index >= 3 else ids["candidate"])
        )
    if mode == "regression":
        first = sheet["pairs"][0]
        candidate = next(entry for entry in first["outputs"] if arm_by_id[entry["id"]] == "candidate")
        candidate["missing_required_ids"] = ["no-prompt-metadata"]
    return sheet


def synthetic_judge(sheet, run):
    labels = {
        pair["task_id"]: {
            "task_id": pair["task_id"],
            "winner": pair["winner"],
            "outputs": [
                {
                    "id": entry["id"],
                    "acceptable": entry["acceptable"],
                    "missing_required_ids": entry["missing_required_ids"],
                }
                for entry in pair["outputs"]
            ],
        }
        for pair in sheet["pairs"]
    }
    _, _, _, _, rows = validate_run(run)
    return {
        "schema_version": "adaptive-review-judge-labels/v1",
        "experiment_id": run["experiment_id"],
        "judge": {
            "tier": "frontier",
            "external": True,
            "provider": "self-test",
            "model_family": "independent-family",
            "model": "self-test",
            "authorization_id": "self-test-authorization",
            "authorized_input_sha256": judge_input_sha256(rows),
            "max_spend_usd": 1,
            "usage": {"input_tokens": 100, "output_tokens": 10, "cost_usd": 0.01},
        },
        "pairs": list(labels.values()),
    }


def self_test():
    experiment, corpus, template, _, _ = load_contract()
    run = synthetic_run(experiment, corpus, template)
    checks = []
    for mode, expected in (
        ("improvement", "improvement"),
        ("regression", "regression"),
        ("inconclusive", "inconclusive"),
    ):
        sheet = fill_labels(make_blind_sheet(run), run, mode)
        report = evaluate(run, sheet, synthetic_judge(sheet, run))
        checks.append((f"{mode} fixture reports {expected}", report["outcome"] == expected))
    sheet = fill_labels(make_blind_sheet(run), run, "improvement")
    report = evaluate(run, sheet)
    checks.append(("missing judge stays inconclusive", report["outcome"] == "inconclusive"))
    bad_judge = synthetic_judge(sheet, run)
    del bad_judge["judge"]["authorization_id"]
    try:
        evaluate(run, sheet, bad_judge)
        checks.append(("external judge without authorization fails closed", False))
    except EvidenceError:
        checks.append(("external judge without authorization fails closed", True))
    ok = True
    for name, passed in checks:
        print(f"{'PASS' if passed else 'FAIL'}: {name}")
        ok = ok and passed
    return 0 if ok else 1


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    sub = parser.add_subparsers(dest="command")
    blind = sub.add_parser("blind")
    blind.add_argument("--run", required=True)
    blind.add_argument("--out", required=True)
    score = sub.add_parser("evaluate")
    score.add_argument("--run", required=True)
    score.add_argument("--human", required=True)
    score.add_argument("--judge")
    score.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        if args.self_test:
            return self_test()
        if args.command == "blind":
            write_json(args.out, make_blind_sheet(read_json(args.run)))
            return 0
        if args.command == "evaluate":
            judge = read_json(args.judge) if args.judge else None
            report = evaluate(read_json(args.run), read_json(args.human), judge)
            write_json(args.out, report)
            print(f"adaptive-review: {report['outcome']}")
            return 0
        parser.print_help()
        return 2
    except (EvidenceError, KeyError, TypeError, json.JSONDecodeError) as error:
        print(f"adaptive-review: invalid evidence: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
