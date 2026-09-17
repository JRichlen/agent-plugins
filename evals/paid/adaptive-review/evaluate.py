#!/usr/bin/env python3
"""Prepare blind labels and score the frozen adaptive-review experiment."""

import argparse
import hashlib
import json
import math
import secrets
import statistics
import subprocess
import sys
from copy import deepcopy
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]


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


def validate_digest(value, where):
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(c not in "0123456789abcdef" for c in value[7:])
    ):
        raise EvidenceError(f"{where} must be sha256 followed by 64 lowercase hex characters")


REVIEW_RUBRIC = (
    "Judge whether each revision is easy to comprehend and ready to post while "
    "preserving every listed required fact and action. Count the minimum "
    "substantive edits still needed; do not reward brevity that drops a requirement."
)
HUMAN_INSTRUCTIONS = (
    "Label without identifying arms. For each output set comprehension 1-5, "
    "edits_needed to the minimum substantive edits before posting, acceptable "
    "true/false, and missing_required_ids. Set winner to an output id or tie."
)


def require_exact_keys(value, expected, where):
    if not isinstance(value, dict):
        raise EvidenceError(f"{where} must be an object")
    extra = set(value) - set(expected)
    missing = set(expected) - set(value)
    if extra or missing:
        raise EvidenceError(
            f"{where} keys differ: missing={sorted(missing)} extra={sorted(extra)}"
        )


def output_id(task_id, arm, text, blinding_salt):
    return hashlib.sha256(
        f"{blinding_salt}\0{task_id}\0{arm}\0{text}".encode("utf-8")
    ).hexdigest()


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


def expected_agent_sha256(experiment, arm):
    return file_sha256(HERE / experiment["arms"][arm]["agent"])


def canonical_image_hash(image):
    body = {
        key: value
        for key, value in image.items()
        if key not in ("hash", "registryRevision")
    }
    encoded = json.dumps(
        body, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def validate_usage(usage, where):
    require_exact_keys(
        usage, {"input_tokens", "output_tokens", "cost_usd"}, f"{where}:usage"
    )
    if not isinstance(usage, dict):
        raise EvidenceError(f"{where}: missing usage")
    for key in ("input_tokens", "output_tokens"):
        value = usage.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise EvidenceError(f"{where}: {key} must be a non-negative integer")
    cost = usage.get("cost_usd")
    if (
        not isinstance(cost, (int, float))
        or isinstance(cost, bool)
        or not math.isfinite(cost)
        or cost < 0
    ):
        raise EvidenceError(f"{where}: cost_usd must be a known non-negative number")


def committed_bytes(commit, relative_path):
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "show", f"{commit}:{relative_path}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        raise EvidenceError(f"git_commit does not contain {relative_path}")
    return result.stdout


def validate_git_provenance(commit, provenance, experiment):
    paths = {
        "experiment_sha256": "evals/paid/adaptive-review/experiment.json",
        "corpus_sha256": "evals/paid/adaptive-review/corpus.json",
    }
    for key, relative_path in paths.items():
        digest = hashlib.sha256(committed_bytes(commit, relative_path)).hexdigest()
        if digest != provenance[key]:
            raise EvidenceError(f"git_commit {relative_path} does not match {key}")
    for arm in ("baseline", "candidate"):
        relative_path = f"evals/paid/adaptive-review/compiled/{arm}.image.json"
        try:
            image = json.loads(committed_bytes(commit, relative_path))
        except json.JSONDecodeError as error:
            raise EvidenceError(f"git_commit has invalid {arm} image JSON") from error
        if canonical_image_hash(image) != image.get("hash"):
            raise EvidenceError(f"git_commit {arm} image has an invalid canonical hash")
        if image.get("hash") != provenance[f"{arm}_image_hash"]:
            raise EvidenceError(f"git_commit {arm} image does not match its recorded hash")
        agent_path = f"evals/paid/adaptive-review/compiled/{arm}.md"
        agent_digest = hashlib.sha256(committed_bytes(commit, agent_path)).hexdigest()
        if agent_digest != provenance[f"{arm}_agent_sha256"]:
            raise EvidenceError(f"git_commit {arm} agent does not match its recorded hash")
    committed_template = committed_bytes(
        commit, "evals/paid/adaptive-review/prompt.template.txt"
    )
    if committed_template != (HERE / experiment["prompt_template"]).read_bytes():
        raise EvidenceError("git_commit prompt template differs from the evaluator checkout")


def validate_run(run, verify_git=True):
    experiment, corpus, template, tasks, held_out = load_contract()
    require_exact_keys(
        run,
        {"schema_version", "experiment_id", "provenance", "actor", "outputs"},
        "run",
    )
    if run.get("schema_version") != "adaptive-review-run/v1":
        raise EvidenceError("run schema_version must be adaptive-review-run/v1")
    if run.get("experiment_id") != experiment["experiment_id"]:
        raise EvidenceError("run experiment_id does not match the frozen experiment")

    provenance = run.get("provenance", {})
    require_exact_keys(
        provenance,
        {
            "git_commit",
            "blinding_salt",
            "corpus_sha256",
            "experiment_sha256",
            "baseline_image_hash",
            "candidate_image_hash",
            "baseline_agent_sha256",
            "candidate_agent_sha256",
        },
        "run provenance",
    )
    blinding_salt = provenance.get("blinding_salt", "")
    if (
        len(blinding_salt) != 64
        or any(c not in "0123456789abcdef" for c in blinding_salt)
    ):
        raise EvidenceError("run blinding_salt must be a private random 64-hex value")
    if provenance.get("corpus_sha256") != file_sha256(HERE / experiment["corpus"]):
        raise EvidenceError("run corpus hash does not match the frozen corpus")
    if provenance.get("experiment_sha256") != file_sha256(HERE / "experiment.json"):
        raise EvidenceError("run experiment hash does not match the frozen thresholds")
    for arm in ("baseline", "candidate"):
        key = f"{arm}_image_hash"
        if provenance.get(key) != expected_image_hash(experiment, arm):
            raise EvidenceError(f"run {key} does not match the compiled image")
        agent_key = f"{arm}_agent_sha256"
        if provenance.get(agent_key) != expected_agent_sha256(experiment, arm):
            raise EvidenceError(f"run {agent_key} does not match the rendered agent")
    commit = provenance.get("git_commit", "")
    if len(commit) != 40 or any(c not in "0123456789abcdef" for c in commit):
        raise EvidenceError("run git_commit must be a lowercase 40-hex commit")
    if verify_git:
        validate_git_provenance(commit, provenance, experiment)

    actor = run.get("actor", {})
    require_exact_keys(
        actor,
        {
            "provider",
            "model_family",
            "model",
            "model_digest",
            "context_window",
            "sequences",
            "external_fallback",
        },
        "actor",
    )
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
    if not isinstance(actor.get("model"), str) or not actor["model"].strip():
        raise EvidenceError("actor model is required")
    if required["model_digest_required"]:
        validate_digest(actor.get("model_digest"), "actor model_digest")

    expected_pairs = {(task_id, arm) for task_id in tasks for arm in ("baseline", "candidate")}
    rows = {}
    if not isinstance(run["outputs"], list):
        raise EvidenceError("run outputs must be a list")
    for row in run["outputs"]:
        require_exact_keys(
            row,
            {
                "task_id",
                "arm",
                "output",
                "output_id",
                "prompt_sha256",
                "agent_image_hash",
                "finish_reason",
                "usage",
            },
            "run output",
        )
        pair = (row.get("task_id"), row.get("arm"))
        if pair in rows:
            raise EvidenceError(f"duplicate output for {pair}")
        if pair not in expected_pairs:
            raise EvidenceError(f"unexpected task/arm pair {pair}")
        text = row.get("output")
        if not isinstance(text, str) or not text.strip():
            raise EvidenceError(f"{pair}: output must be non-empty text")
        if row.get("output_id") != output_id(pair[0], pair[1], text, blinding_salt):
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


def review_payload(experiment, held_out, rows):
    return {
        "schema_version": "adaptive-review-review-input/v1",
        "experiment_id": experiment["experiment_id"],
        "rubric": REVIEW_RUBRIC,
        "pairs": [
            {
                "task_id": task["id"],
                "source": task["source"],
                "title": task["title"],
                "input": task["input"],
                "required_facts": task["required_facts"],
                "required_actions": task["required_actions"],
                "outputs": sorted(
                    [
                        {
                            "id": rows[(task["id"], arm)]["output_id"],
                            "text": rows[(task["id"], arm)]["output"],
                        }
                        for arm in ("baseline", "candidate")
                    ],
                    key=lambda item: item["id"],
                ),
            }
            for task in held_out
        ],
    }


def review_input_sha256(experiment, held_out, rows):
    encoded = json.dumps(
        review_payload(experiment, held_out, rows),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def make_blind_sheet(run, verify_git=True):
    experiment, _, _, held_out, rows = validate_run(run, verify_git=verify_git)
    result = {
        "schema_version": "adaptive-review-human-labels/v1",
        "experiment_id": experiment["experiment_id"],
        "review_input_sha256": review_input_sha256(experiment, held_out, rows),
        "rubric": REVIEW_RUBRIC,
        "instructions": HUMAN_INSTRUCTIONS,
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
        secrets.SystemRandom().shuffle(candidates)
        result["pairs"].append(
            {
                "task_id": task_id,
                "source": task["source"],
                "title": task["title"],
                "input": task["input"],
                "required_facts": task["required_facts"],
                "required_actions": task["required_actions"],
                "outputs": candidates,
                "winner": None,
            }
        )
    return result


def index_pairs(raw_pairs, held_out, where):
    if not isinstance(raw_pairs, list):
        raise EvidenceError(f"{where} pairs must be a list")
    expected = {task["id"] for task in held_out}
    ids = [pair.get("task_id") for pair in raw_pairs if isinstance(pair, dict)]
    if len(ids) != len(raw_pairs):
        raise EvidenceError(f"{where} pairs must all be objects")
    if len(ids) != len(set(ids)):
        raise EvidenceError(f"{where} contains duplicate task labels")
    unknown = set(ids) - expected
    if unknown:
        raise EvidenceError(f"{where} contains unknown tasks {sorted(unknown)}")
    return {pair["task_id"]: pair for pair in raw_pairs}


def validate_human(sheet, experiment, tasks, held_out, rows):
    require_exact_keys(
        sheet,
        {
            "schema_version",
            "experiment_id",
            "review_input_sha256",
            "rubric",
            "instructions",
            "pairs",
        },
        "human labels",
    )
    if sheet.get("schema_version") != "adaptive-review-human-labels/v1":
        raise EvidenceError("human labels have the wrong schema_version")
    if sheet.get("experiment_id") != experiment["experiment_id"]:
        raise EvidenceError("human labels refer to another experiment")
    if sheet.get("review_input_sha256") != review_input_sha256(experiment, held_out, rows):
        raise EvidenceError("human labels do not match the canonical review input")
    if sheet.get("rubric") != REVIEW_RUBRIC:
        raise EvidenceError("human labels do not carry the frozen rubric")
    if sheet.get("instructions") != HUMAN_INSTRUCTIONS:
        raise EvidenceError("human labels do not carry the frozen instructions")
    pairs = index_pairs(sheet["pairs"], held_out, "human labels")
    labels = {}
    incomplete = []
    for task in held_out:
        task_id = task["id"]
        pair = pairs.get(task_id)
        if not pair:
            incomplete.append(f"human:{task_id}")
            continue
        require_exact_keys(
            pair,
            {
                "task_id",
                "source",
                "title",
                "input",
                "required_facts",
                "required_actions",
                "outputs",
                "winner",
            },
            f"human:{task_id}",
        )
        for key in ("source", "title", "input", "required_facts", "required_actions"):
            if pair.get(key) != task[key]:
                raise EvidenceError(f"human:{task_id}: frozen {key} changed")
        allowed_ids = {
            item["id"] for group in ("required_facts", "required_actions") for item in task[group]
        }
        expected = {rows[(task_id, arm)]["output_id"] for arm in ("baseline", "candidate")}
        entries = pair.get("outputs", [])
        if not isinstance(entries, list):
            raise EvidenceError(f"human:{task_id}: outputs must be a list")
        found_ids = [entry.get("id") for entry in entries if isinstance(entry, dict)]
        found = set(found_ids)
        if (
            len(found_ids) != len(entries)
            or len(found_ids) != len(expected)
            or len(found_ids) != len(found)
            or found != expected
        ):
            raise EvidenceError(f"human:{task_id}: output ids do not match the run")
        for entry in pair["outputs"]:
            require_exact_keys(
                entry,
                {
                    "id",
                    "text",
                    "comprehension",
                    "edits_needed",
                    "acceptable",
                    "missing_required_ids",
                },
                f"human:{task_id}:output",
            )
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


def validate_judge(judge, experiment, tasks, held_out, rows, actor):
    if judge is None:
        return {}, {}, ["judge:missing"], {}
    require_exact_keys(
        judge,
        {
            "schema_version",
            "experiment_id",
            "review_input_sha256",
            "authorization",
            "judge",
            "pairs",
        },
        "judge labels",
    )
    if judge.get("schema_version") != "adaptive-review-judge-labels/v1":
        raise EvidenceError("judge labels have the wrong schema_version")
    if judge.get("experiment_id") != experiment["experiment_id"]:
        raise EvidenceError("judge labels refer to another experiment")
    expected_input_hash = review_input_sha256(experiment, held_out, rows)
    if judge.get("review_input_sha256") != expected_input_hash:
        raise EvidenceError("judge labels do not match the canonical review input")
    meta = judge.get("judge", {})
    require_exact_keys(
        meta,
        {
            "tier",
            "external",
            "provider",
            "model_family",
            "model",
            "model_digest",
            "usage",
        },
        "judge",
    )
    if meta.get("tier") != "frontier":
        raise EvidenceError("judge tier must be frontier")
    for key in ("provider", "model_family", "model", "model_digest"):
        if not isinstance(meta.get(key), str) or not meta[key].strip():
            raise EvidenceError(f"judge {key} is required")
    validate_digest(meta["model_digest"], "judge model_digest")
    if meta["provider"].strip().casefold() == "local":
        raise EvidenceError("the frontier judge must use an external provider")
    if meta["model_family"].strip().casefold() == actor.get("model_family", "").strip().casefold():
        raise EvidenceError("judge must be from a different model family than the actor")
    validate_usage(meta.get("usage"), "judge")
    if meta.get("external") is not True:
        raise EvidenceError("the frontier judge must be recorded as external")
    authorization = judge.get("authorization", {})
    require_exact_keys(
        authorization,
        {"id", "approved_by", "approved_at", "input_sha256", "max_spend_usd"},
        "judge authorization",
    )
    for key in ("id", "approved_by", "approved_at"):
        if not isinstance(authorization.get(key), str) or not authorization[key].strip():
            raise EvidenceError(f"external judge authorization {key} is required")
    if authorization.get("input_sha256") != expected_input_hash:
        raise EvidenceError("external judge authorization is not bound to the exact review input")
    cap = authorization.get("max_spend_usd")
    if (
        not isinstance(cap, (int, float))
        or isinstance(cap, bool)
        or not math.isfinite(cap)
        or cap <= 0
    ):
        raise EvidenceError("external judge requires a finite positive max_spend_usd")
    if meta["usage"]["cost_usd"] > cap:
        raise EvidenceError("external judge cost exceeds its authorized spending limit")

    pairs = index_pairs(judge["pairs"], held_out, "judge labels")
    labels = {}
    incomplete = []
    for task in held_out:
        task_id = task["id"]
        pair = pairs.get(task_id)
        if not pair:
            incomplete.append(f"judge:{task_id}")
            continue
        require_exact_keys(
            pair, {"task_id", "winner", "outputs"}, f"judge:{task_id}"
        )
        allowed_ids = {
            item["id"] for group in ("required_facts", "required_actions") for item in task[group]
        }
        expected = {rows[(task_id, arm)]["output_id"] for arm in ("baseline", "candidate")}
        entries = pair.get("outputs", [])
        if not isinstance(entries, list):
            raise EvidenceError(f"judge:{task_id}: outputs must be a list")
        found_ids = [entry.get("id") for entry in entries if isinstance(entry, dict)]
        found = set(found_ids)
        if (
            len(found_ids) != len(entries)
            or len(found_ids) != len(expected)
            or len(found_ids) != len(found)
            or found != expected
        ):
            raise EvidenceError(f"judge:{task_id}: output ids do not match the run")
        for entry in pair["outputs"]:
            require_exact_keys(
                entry,
                {"id", "acceptable", "missing_required_ids"},
                f"judge:{task_id}:output",
            )
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


def evaluate(run, human, judge=None, verify_git=True):
    experiment, _, tasks, held_out, rows = validate_run(run, verify_git=verify_git)
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
    candidate_acceptable = []
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
            candidate_acceptable.append(candidate_label["acceptable"])
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
    judge_wins = {"baseline": 0, "candidate": 0, "tie": 0}
    judge_candidate_missing = []
    if not human_missing and not judge_missing:
        for task in held_out:
            winner_n += 1
            human_winner = human_pairs[task["id"]]["winner"]
            judge_winner = judge_pairs[task["id"]]["winner"]
            winner_agreements += human_winner == judge_winner
            judge_wins["tie" if judge_winner == "tie" else arm_by_id[judge_winner]] += 1
            candidate_id = rows[(task["id"], "candidate")]["output_id"]
            judge_candidate = next(
                entry
                for entry in judge_pairs[task["id"]]["outputs"]
                if entry["id"] == candidate_id
            )
            judge_candidate_missing.extend(judge_candidate["missing_required_ids"])

    actor_usage = {
        "input_tokens": sum(row["usage"]["input_tokens"] for row in rows.values()),
        "output_tokens": sum(row["usage"]["output_tokens"] for row in rows.values()),
        "cost_usd": round(sum(row["usage"]["cost_usd"] for row in rows.values()), 12),
    }
    judge_usage = judge_meta.get("usage") if judge_meta else None
    total_usage = dict(actor_usage)
    if judge_usage:
        total_usage = {
            "input_tokens": actor_usage["input_tokens"] + judge_usage["input_tokens"],
            "output_tokens": actor_usage["output_tokens"] + judge_usage["output_tokens"],
            "cost_usd": round(actor_usage["cost_usd"] + judge_usage["cost_usd"], 12),
        }
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
        "candidate_acceptable_rate": (
            sum(candidate_acceptable) / len(candidate_acceptable)
            if candidate_acceptable
            else None
        ),
        "judge_human_agreement": agreement if calibration_n else None,
        "judge_human_kappa": kappa,
        "judge_human_n": calibration_n,
        "winner_agreement": winner_agreements / winner_n if winner_n else None,
        "judge_wins": judge_wins if winner_n else None,
        "judge_candidate_missing_required": (
            len(judge_candidate_missing) if winner_n else None
        ),
        "actor_usage": actor_usage,
        "judge_usage": judge_usage,
        "total_usage": total_usage,
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
        and metrics["candidate_acceptable_rate"] >= thresholds["candidate_acceptable_rate"]
        and len(candidate_missing) <= thresholds["candidate_missing_required_max"]
        and agreement >= thresholds["judge_human_agreement"]
        and (kappa is None or kappa >= thresholds["judge_human_kappa"])
        and metrics["winner_agreement"] >= thresholds["judge_winner_agreement"]
        and judge_wins["candidate"] >= thresholds["judge_candidate_wins"]
        and len(judge_candidate_missing)
        <= thresholds["judge_candidate_missing_required_max"]
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
            "Held-out means excluded from development runs, not hidden from the experiment author.",
            "Human edit counts and comprehension ratings remain subjective despite blinding.",
            "The authorization record is an auditable receipt, not cryptographic attestation.",
            "A passing result qualifies only a review-scoped approval; it does not justify learning or coding transfer."
        ],
    }


def synthetic_run(experiment, corpus, template):
    images = {arm: expected_image_hash(experiment, arm) for arm in ("baseline", "candidate")}
    blinding_salt = "0" * 64
    outputs = []
    for task in corpus["tasks"]:
        for arm in ("baseline", "candidate"):
            text = f"{arm.title()} response for {task['id']} with retained requirements."
            outputs.append(
                {
                    "task_id": task["id"],
                    "arm": arm,
                    "output": text,
                    "output_id": output_id(task["id"], arm, text, blinding_salt),
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
            "blinding_salt": blinding_salt,
            "corpus_sha256": file_sha256(HERE / experiment["corpus"]),
            "experiment_sha256": file_sha256(HERE / "experiment.json"),
            "baseline_image_hash": images["baseline"],
            "candidate_image_hash": images["candidate"],
            "baseline_agent_sha256": expected_agent_sha256(experiment, "baseline"),
            "candidate_agent_sha256": expected_agent_sha256(experiment, "candidate"),
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
    return {
        "schema_version": "adaptive-review-judge-labels/v1",
        "experiment_id": run["experiment_id"],
        "review_input_sha256": sheet["review_input_sha256"],
        "authorization": {
            "id": "self-test-authorization",
            "approved_by": "self-test",
            "approved_at": "2000-01-01T00:00:00Z",
            "input_sha256": sheet["review_input_sha256"],
            "max_spend_usd": 1,
        },
        "judge": {
            "tier": "frontier",
            "external": True,
            "provider": "self-test",
            "model_family": "independent-family",
            "model": "self-test",
            "model_digest": "sha256:" + "1" * 64,
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
        sheet = fill_labels(make_blind_sheet(run, verify_git=False), run, mode)
        report = evaluate(run, sheet, synthetic_judge(sheet, run), verify_git=False)
        checks.append((f"{mode} fixture reports {expected}", report["outcome"] == expected))
    sheet = fill_labels(make_blind_sheet(run, verify_git=False), run, "improvement")
    report = evaluate(run, sheet, verify_git=False)
    checks.append(("missing judge stays inconclusive", report["outcome"] == "inconclusive"))
    unacceptable = deepcopy(sheet)
    for pair in unacceptable["pairs"]:
        candidate_id = next(
            row["output_id"]
            for row in run["outputs"]
            if row["task_id"] == pair["task_id"] and row["arm"] == "candidate"
        )
        next(entry for entry in pair["outputs"] if entry["id"] == candidate_id)["acceptable"] = False
    report = evaluate(
        run, unacceptable, synthetic_judge(unacceptable, run), verify_git=False
    )
    checks.append(
        ("unacceptable candidates cannot advance", report["outcome"] == "inconclusive")
    )
    bad_judge = synthetic_judge(sheet, run)
    del bad_judge["authorization"]["id"]
    try:
        evaluate(run, sheet, bad_judge, verify_git=False)
        checks.append(("external judge without authorization fails closed", False))
    except EvidenceError:
        checks.append(("external judge without authorization fails closed", True))
    bad_judge = synthetic_judge(sheet, run)
    bad_judge["judge"]["external"] = False
    try:
        evaluate(run, sheet, bad_judge, verify_git=False)
        checks.append(("external flag cannot bypass authorization", False))
    except EvidenceError:
        checks.append(("external flag cannot bypass authorization", True))
    bad_judge = synthetic_judge(sheet, run)
    bad_judge["judge"]["usage"]["cost_usd"] = float("nan")
    try:
        evaluate(run, sheet, bad_judge, verify_git=False)
        checks.append(("non-finite judge cost fails closed", False))
    except EvidenceError:
        checks.append(("non-finite judge cost fails closed", True))
    bad_judge = synthetic_judge(sheet, run)
    del bad_judge["judge"]["model_family"]
    try:
        evaluate(run, sheet, bad_judge, verify_git=False)
        checks.append(("missing judge identity fails closed", False))
    except EvidenceError:
        checks.append(("missing judge identity fails closed", True))
    corrupted = deepcopy(sheet)
    corrupted["pairs"][0]["required_facts"] = []
    try:
        evaluate(
            run, corrupted, synthetic_judge(corrupted, run), verify_git=False
        )
        checks.append(("changed human review inputs fail closed", False))
    except EvidenceError:
        checks.append(("changed human review inputs fail closed", True))
    leaked = deepcopy(sheet)
    leaked["pairs"][0]["outputs"][0]["arm"] = "candidate"
    try:
        evaluate(run, leaked, synthetic_judge(sheet, run), verify_git=False)
        checks.append(("arm metadata in human labels fails closed", False))
    except EvidenceError:
        checks.append(("arm metadata in human labels fails closed", True))
    judge_omission = synthetic_judge(sheet, run)
    first_task = sheet["pairs"][0]["task_id"]
    candidate_id = next(
        row["output_id"]
        for row in run["outputs"]
        if row["task_id"] == first_task and row["arm"] == "candidate"
    )
    next(
        entry
        for entry in judge_omission["pairs"][0]["outputs"]
        if entry["id"] == candidate_id
    )["missing_required_ids"] = ["no-prompt-metadata"]
    report = evaluate(run, sheet, judge_omission, verify_git=False)
    checks.append(
        ("judge-reported candidate omission blocks advancement", report["outcome"] == "inconclusive")
    )
    duplicated = deepcopy(sheet)
    duplicated["pairs"][0]["outputs"].append(deepcopy(duplicated["pairs"][0]["outputs"][0]))
    try:
        evaluate(run, duplicated, synthetic_judge(sheet, run), verify_git=False)
        checks.append(("duplicate human output labels fail closed", False))
    except EvidenceError:
        checks.append(("duplicate human output labels fail closed", True))
    duplicate_judge = synthetic_judge(sheet, run)
    duplicate_judge["pairs"].append(deepcopy(duplicate_judge["pairs"][0]))
    try:
        evaluate(run, sheet, duplicate_judge, verify_git=False)
        checks.append(("duplicate judge task labels fail closed", False))
    except EvidenceError:
        checks.append(("duplicate judge task labels fail closed", True))
    try:
        validate_run(run, verify_git=True)
        checks.append(("nonexistent git provenance fails closed", False))
    except EvidenceError:
        checks.append(("nonexistent git provenance fails closed", True))
    open_run = deepcopy(run)
    open_run["unbound"] = "field"
    try:
        validate_run(open_run, verify_git=False)
        checks.append(("unknown run fields fail closed", False))
    except EvidenceError:
        checks.append(("unknown run fields fail closed", True))
    image = read_json(HERE / experiment["arms"]["candidate"]["image"])
    valid_image_hash = canonical_image_hash(image) == image["hash"]
    tampered_image = deepcopy(image)
    tampered_image["behavior"][0]["content"] += " changed"
    checks.append(
        (
            "canonical image hash detects behavior mutation",
            valid_image_hash and canonical_image_hash(tampered_image) != image["hash"],
        )
    )
    salt = run["provenance"]["blinding_salt"]
    checks.append(
        (
            "identical arm text still gets distinct opaque ids",
            output_id("same-task", "baseline", "same", salt)
            != output_id("same-task", "candidate", "same", salt),
        )
    )
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
