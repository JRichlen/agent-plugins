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


def recover(repo, inputs, output, source_commit, run_id, artifact_id, recovered_at, bash="bash"):
    if output.exists() and any(output.iterdir()):
        raise ValueError("recovery output must be empty")
    moment = datetime.fromisoformat(recovered_at.replace("Z", "+00:00"))
    if moment.utcoffset() is None:
        raise ValueError("recovery time must include timezone")
    if not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise ValueError("full source commit required")
    if not str(run_id).isdigit() or not str(artifact_id).isdigit():
        raise ValueError("numeric source run and artifact IDs required")
    active = json.loads((repo / ".claude-plugin/marketplace.json").read_text(encoding="utf-8"))["plugins"]
    captured = []
    with tempfile.TemporaryDirectory(prefix="recovery-config-") as folder:
        pack = Path(folder)
        for plugin in sorted(p["name"] for p in active):
            result = inputs / plugin / "evals/promptfoo/results.json"
            if not result.is_file():
                continue
            config = subprocess.run(["git", "-C", str(repo), "show", source_commit + ":plugins/" + plugin + "/evals/promptfoo/promptfooconfig.yaml"], capture_output=True, check=True).stdout
            (pack / "promptfooconfig.yaml").write_bytes(config)
            subprocess.run([bash, (repo / "evals/paid/capture-example.sh").as_posix(), result.as_posix(), plugin,
                            "--pack", pack.as_posix(), "--out", output.as_posix(), "--commit", source_commit,
                            "--captured-at", "unknown", "--run-url", "https://github.com/JRichlen/agent-plugins/actions/runs/" + str(run_id)], check=True)
            snapshot = output / (plugin + ".json")
            if not snapshot.exists():
                continue
            data = json.loads(snapshot.read_text(encoding="utf-8"))
            data["provenance"].update({"source": "promptfoo-recovered", "recovered_at": recovered_at,
                "artifact_id": str(artifact_id), "artifact_path": result.relative_to(inputs).as_posix(),
                "source_config_sha256": hashlib.sha256(config).hexdigest(),
                "attestation": "none — recovered after the failed capture; no original snapshot or signature existed"})
            data["notice"] = "Recovered from existing CI results without new model calls. Original capture time is unknown; this snapshot is not attested. Both grades are shown below; a passing pair does not establish improvement."
            snapshot.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
            captured.append(plugin)
    return {"captured": captured, "new_model_calls": 0, "source_commit": source_commit,
            "run_id": str(run_id), "artifact_id": str(artifact_id), "recovered_at": recovered_at}


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
    print(json.dumps(recover(args.repo, args.inputs, args.output, args.source_commit,
                             args.run_id, args.artifact_id, args.recovered_at,
                             os.environ.get("TEST_BASH", "bash")), indent=2))


if __name__ == "__main__":
    main()
