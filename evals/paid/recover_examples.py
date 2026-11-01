#!/usr/bin/env python3
"""Recover active gallery pairs from downloaded results; no model or download."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def validate_recovered(prov):
    """Validate recorded field formats, not remote authenticity or attestation."""
    errors = []
    for field, width in (("commit", 40), ("results_sha256", 64), ("source_config_sha256", 64)):
        value = prov.get(field)
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{%d}" % width, value):
            errors.append(field + " must be a full lowercase hexadecimal identity")
    value = prov.get("artifact_id")
    if not isinstance(value, str) or not re.fullmatch(r"[1-9][0-9]*", value):
        errors.append("artifact_id must be a positive decimal string")
    value = prov.get("artifact_path")
    if not isinstance(value, str) or not value or "\\" in value or Path(value).is_absolute() or any(part in (".", "..") for part in value.split('/')):
        errors.append("artifact_path must be a relative artifact member")
    try:
        value = prov.get("recovered_at")
        moment = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else None
        if moment is None or moment.utcoffset() is None:
            raise ValueError()
    except ValueError:
        errors.append("recovered_at must be an ISO timestamp with timezone")
    rows = prov.get("source_rows")
    if not isinstance(rows, dict) or set(rows) != {"with_skill", "without_skill"}:
        errors.append("source_rows must identify both arms")
    else:
        for side, row in rows.items():
            if not isinstance(row, dict) or type(row.get("index")) is not int or row["index"] < 0 or (row.get("id") is not None and not isinstance(row.get("id"), str)):
                errors.append(side + " source row requires a nonnegative integer index and string/null id")
    return errors


def recover(repo, inputs, output, source_commit, run_id, artifact_id, recovered_at, bash=None):
    if output.exists() and any(output.iterdir()):
        raise ValueError("recovery output must be empty")
    if bash is None:
        from ci.host_tools import select_bash
        bash = select_bash()
    moment = datetime.fromisoformat(recovered_at.replace("Z", "+00:00"))
    if moment.utcoffset() is None:
        raise ValueError("recovery time must include timezone")
    if not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise ValueError("full source commit required")
    if not re.fullmatch(r"[1-9][0-9]*", str(run_id)) or not re.fullmatch(r"[1-9][0-9]*", str(artifact_id)):
        raise ValueError("positive numeric source run and artifact IDs required")
    active = json.loads((repo / ".claude-plugin/marketplace.json").read_text(encoding="utf-8"))["plugins"]
    names = {p["name"] for p in active}
    available = {p.parent.parent.parent.name for p in inputs.glob("*/evals/promptfoo/results.json")}
    receipt = {"captured": [], "items": [], "status": "in_progress", "new_model_calls": 0,
               "source_commit": source_commit, "run_id": str(run_id), "artifact_id": str(artifact_id), "recovered_at": recovered_at}
    output.mkdir(parents=True, exist_ok=True)
    def save():
        (output / "recovery-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8", newline="\n")
    save()
    with tempfile.TemporaryDirectory(prefix="recovery-config-") as folder:
        pack = Path(folder)
        for plugin in sorted(names | available):
            item = {"plugin": plugin}
            receipt["items"].append(item)
            result = inputs / plugin / "evals/promptfoo/results.json"
            if plugin not in names:
                item.update(status="skipped", reason="not in current active marketplace")
            elif not result.is_file():
                item.update(status="skipped", reason="no results file in artifact")
            else:
                try:
                    config = subprocess.run(["git", "--no-replace-objects", "-C", str(repo), "show", source_commit + ":plugins/" + plugin + "/evals/promptfoo/promptfooconfig.yaml"], capture_output=True, check=True).stdout
                    (pack / "promptfooconfig.yaml").write_bytes(config)
                    subprocess.run([bash, (repo / "evals/paid/capture-example.sh").as_posix(), result.as_posix(), plugin,
                                    "--pack", pack.as_posix(), "--out", output.as_posix(), "--commit", source_commit,
                                    "--captured-at", "unknown", "--run-url", "https://github.com/JRichlen/agent-plugins/actions/runs/" + str(run_id)], check=True, capture_output=True)
                    snapshot = output / (plugin + ".json")
                    if not snapshot.exists():
                        item.update(status="skipped", reason="no eligible matching real/control pair")
                    else:
                        data = json.loads(snapshot.read_text(encoding="utf-8"))
                        data["provenance"].update({"source": "promptfoo-recovered", "recovered_at": recovered_at,
                            "artifact_id": str(artifact_id), "artifact_path": result.relative_to(inputs).as_posix(),
                            "source_config_sha256": hashlib.sha256(config).hexdigest(),
                            "source_config_url": "https://github.com/JRichlen/agent-plugins/blob/" + source_commit + "/plugins/" + plugin + "/evals/promptfoo/promptfooconfig.yaml",
                            "grading_comparability": "Arm-specific rubrics; pass booleans are not a common outcome scale.",
                            "attestation": "none — recovered after failed capture; no original snapshot or signature existed"})
                        problems = validate_recovered(data["provenance"])
                        if problems:
                            raise ValueError('; '.join(problems))
                        data["notice"] = "Recovered from existing CI results without new model calls. Original capture time is unknown; this snapshot is not attested. Each arm uses its own criterion; both passing does not mean equal behavior or prove causal improvement."
                        snapshot.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
                        receipt["captured"].append(plugin)
                        item.update(status="captured", snapshot=snapshot.name)
                except (OSError, ValueError, subprocess.SubprocessError) as error:
                    item.update(status="failed", reason=type(error).__name__ + ": " + str(error))
                    # Never leave an unlabelled capture posing as recovered evidence.
                    (output / (plugin + ".json")).unlink(missing_ok=True)
            save()
    receipt["status"] = "partial_failure" if any(item['status'] == 'failed' for item in receipt['items']) else "complete"
    save()
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--artifact-id", required=True)
    parser.add_argument("--recovered-at", required=True, help="actual recovery time, not original capture time")
    args = parser.parse_args()
    # A new directory avoids mistaking an earlier snapshot for a new capture.
    args.output.mkdir(parents=True, exist_ok=False)
    receipt = recover(args.repo, args.inputs, args.output, args.source_commit,
                      args.run_id, args.artifact_id, args.recovered_at)
    print(json.dumps(receipt, indent=2))
    return 1 if receipt["status"] == "partial_failure" else 0


if __name__ == "__main__":
    raise SystemExit(main())
