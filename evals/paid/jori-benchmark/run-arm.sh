#!/usr/bin/env bash
# run-arm.sh — run ONE isolated attempt of one activity under one arm and write one
# result JSON. This is the only place a model is called, and only when --live is given.
#
#   run-arm.sh --arm jori|baseline --task <id> --repeat <n> --out <dir> \
#              [--model <id>] [--budget <usd>] [--live | --dry-run] [--claude <bin>]
#
# Arms (exposure parity: identical prompt text, tools, permission mode, model, budget,
# working directory; the ONLY difference is the jori plugin and the /jori prefix):
#   baseline  plain `claude -p "<task prompt>"`, no plugin loaded
#   jori      `claude -p "/jori <task prompt>" --plugin-dir plugins/jori`
# --dry-run never invokes claude: it stages the workspace, applies nothing, verifies,
# and writes a result whose cost/usage fields are the string "UNKNOWN". Used by
# self-test.sh and by anyone who wants to check plumbing without spending.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(cd "$here/../../.." && pwd)"
arm=""; task=""; repeat=""; out=""; model=""; budget="2.00"; mode="dry-run"; claude_bin="claude"
while [ $# -gt 0 ]; do
  case "$1" in
    --arm) arm="$2"; shift 2;; --task) task="$2"; shift 2;; --repeat) repeat="$2"; shift 2;;
    --out) out="$2"; shift 2;; --model) model="$2"; shift 2;; --budget) budget="$2"; shift 2;;
    --live) mode="live"; shift;; --dry-run) mode="dry-run"; shift;; --claude) claude_bin="$2"; shift 2;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done
case "$arm" in jori|baseline) ;; *) echo "--arm must be jori or baseline" >&2; exit 2;; esac
[ -n "$task" ] && [ -n "$repeat" ] && [ -n "$out" ] || { echo "--task, --repeat, --out required" >&2; exit 2; }
tdir="$here/tasks/$task"
[ -f "$tdir/prompt.md" ] && [ -x "$tdir/setup.sh" ] && [ -x "$tdir/verify.sh" ] || { echo "task '$task' incomplete under $tdir" >&2; exit 2; }
mkdir -p "$out"
ws="$(mktemp -d)"; trap 'rm -rf "$ws"' EXIT
"$tdir/setup.sh" "$ws"
prompt="$(cat "$tdir/prompt.md")"
[ "$arm" = "jori" ] && prompt="/jori $prompt"
stream="$out/$arm-$repeat.stream.jsonl"; : > "$stream"
started="$(date -u +%Y-%m-%dT%H:%M:%SZ)"; t0=$(date +%s%N)
claude_exit="null"; claude_version="UNKNOWN"
if [ "$mode" = "live" ]; then
  claude_version="$("$claude_bin" --version 2>/dev/null | head -1 || echo UNKNOWN)"
  argv=("$claude_bin" -p "$prompt" --output-format stream-json --verbose
        --permission-mode acceptEdits
        --allowedTools "Bash,Read,Edit,Write,MultiEdit,Glob,Grep,Agent,Skill,TodoWrite"
        --max-budget-usd "$budget" --no-session-persistence)
  [ -n "$model" ] && argv+=(--model "$model")
  [ "$arm" = "jori" ] && argv+=(--plugin-dir "$repo/plugins/jori")
  set +e
  ( cd "$ws" && "${argv[@]}" ) > "$stream" 2> "$out/$arm-$repeat.stderr"
  claude_exit=$?
  set -e
fi
t1=$(date +%s%N); wall_ms=$(( (t1 - t0) / 1000000 ))
set +e; verify_json="$("$tdir/verify.sh" "$ws")"; verify_exit=$?; set -e
python3 - "$out/$arm-$repeat.json" "$stream" "$arm" "$task" "$repeat" "$model" "$budget" "$mode" "$claude_exit" "$verify_exit" "$verify_json" "$started" "$wall_ms" "$claude_version" <<'PY'
import json, sys
(outp, stream, arm, task, repeat, model, budget, mode, cexit, vexit, vjson, started, wall_ms, cver) = sys.argv[1:]
UNKNOWN = "UNKNOWN"
res = None; init = None; tool_uses = []; realized_models = set()
for line in open(stream, encoding="utf-8", errors="replace"):
    line = line.strip()
    if not line: continue
    try: ev = json.loads(line)
    except Exception: continue
    t = ev.get("type")
    if t == "system" and ev.get("subtype") == "init": init = ev
    elif t == "result": res = ev
    elif t == "assistant":
        msg = ev.get("message") or {}
        if isinstance(msg.get("model"), str): realized_models.add(msg["model"])
        for c in msg.get("content") or []:
            if isinstance(c, dict) and c.get("type") == "tool_use":
                tool_uses.append({"name": c.get("name"), "input": c.get("input") if isinstance(c.get("input"), dict) else {}})
def field(d, k):
    return d[k] if isinstance(d, dict) and k in d and d[k] is not None else UNKNOWN
usage = res.get("usage") if res else None
skill_uses = [u for u in tool_uses if u["name"] == "Skill"]
jori_skill = any("jori" in json.dumps(u["input"]).lower() for u in skill_uses)
agent_uses = [u for u in tool_uses if u["name"] in ("Agent", "Task")]
try: vj = json.loads(vjson)
except Exception: vj = {"outcome": "fault", "raw": vjson}
success = (vexit == "0") and vj.get("outcome") == "pass"
record = {
  "schema": "jori-benchmark/attempt/v1",
  "arm": arm, "task": task, "repeat": int(repeat), "mode": mode, "started": started,
  "model_requested": model or UNKNOWN,
  "model_realized": sorted(realized_models) if realized_models else UNKNOWN,
  "claude_code_version": cver,
  "budget_usd": float(budget),
  "claude_exit": None if cexit == "null" else int(cexit),
  "wall_clock_ms": int(wall_ms),
  "result_subtype": field(res, "subtype") if res else UNKNOWN,
  "is_error": field(res, "is_error") if res else UNKNOWN,
  "num_turns": field(res, "num_turns") if res else UNKNOWN,
  "duration_ms": field(res, "duration_ms") if res else UNKNOWN,
  "duration_api_ms": field(res, "duration_api_ms") if res else UNKNOWN,
  "total_cost_usd": field(res, "total_cost_usd") if res else UNKNOWN,
  "usage": {k: field(usage, k) for k in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")} if usage else UNKNOWN,
  "model_usage": res.get("modelUsage") if res and isinstance(res.get("modelUsage"), dict) else UNKNOWN,
  "tool_use_counts": {n: sum(1 for u in tool_uses if u["name"] == n) for n in sorted({u["name"] for u in tool_uses if u["name"]})},
  "adoption": {"jori_skill_invoked": jori_skill, "prompt_prefixed_with_slash_jori": arm == "jori",
               "delegated_subagents": len(agent_uses), "delegated": len(agent_uses) >= 1},
  "outcome": {"success": success, "verify_exit": int(vexit), "verifier": vj},
}
json.dump(record, open(outp, "w"), indent=1, sort_keys=True)
print(json.dumps({"arm": arm, "repeat": int(repeat), "mode": mode, "success": success,
                  "total_cost_usd": record["total_cost_usd"], "num_turns": record["num_turns"],
                  "delegated": record["adoption"]["delegated"]}))
PY
