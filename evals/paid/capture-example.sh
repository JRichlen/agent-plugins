#!/usr/bin/env bash
#
# capture-example.sh RESULTS.json PLUGIN [--out DIR] [--commit SHA] [--captured-at ISO8601]
#
# Turn a promptfoo results.json into a committed, publishable before/after
# example snapshot for one plugin — the raw material for the GitHub Pages
# example gallery (docs/examples/). The gallery's whole point is verification:
# every published "with skill vs without skill" pair is a REAL, graded model
# run, never hand-written marketing, so this script only ever copies what the
# eval actually produced. It fabricates nothing.
#
# It pairs the plugin's real-skill scenario with its negative-control
# (calibration / stub) scenario from the SAME results file:
#   with_skill    = a passing real-skill test row (the skill steered the output)
#   without_skill = the calibration row (same bait, generic stub — the
#                   naturally-helpful baseline the skill is measured against)
# and writes docs/examples/data/<plugin>.json with both outputs, both grades,
# and provenance (model, grader, source, commit, capture time). Timestamps and
# commit come from ARGS (CI supplies them) — never Date.now()/git here, so a
# re-run on the same inputs is reproducible.
#
# A results file that lacks a usable pair for the plugin is NOT an error: it
# prints a skip notice and exits 0, so a plugin whose pack didn't run this CI
# leg simply keeps its previous snapshot.
#
# Exit: 0 captured or cleanly skipped; 2 usage / unreadable results.
set -uo pipefail

RESULTS=""; PLUGIN=""; OUT="docs/examples/data"; COMMIT=""; CAPTURED=""
while [ $# -gt 0 ]; do
  case "$1" in
    --out)         OUT="${2:?}"; shift 2 ;;
    --commit)      COMMIT="${2:?}"; shift 2 ;;
    --captured-at) CAPTURED="${2:?}"; shift 2 ;;
    -*)            echo "capture-example: unknown flag $1" >&2; exit 2 ;;
    *) if [ -z "$RESULTS" ]; then RESULTS="$1"; elif [ -z "$PLUGIN" ]; then PLUGIN="$1"; fi; shift ;;
  esac
done
[ -n "$RESULTS" ] && [ -n "$PLUGIN" ] || { echo "usage: capture-example.sh RESULTS.json PLUGIN [--out DIR] [--commit SHA] [--captured-at ISO8601]" >&2; exit 2; }
[ -f "$RESULTS" ] || { echo "capture-example: no such file: $RESULTS" >&2; exit 2; }
mkdir -p "$OUT"

python3 - "$RESULTS" "$PLUGIN" "$OUT" "$COMMIT" "$CAPTURED" <<'PY'
import json, os, sys
results, plugin, outdir, commit, captured = sys.argv[1:6]
try:
    doc = json.load(open(results))
except Exception as e:
    print(f"capture-example: cannot parse {results}: {e}", file=sys.stderr); sys.exit(2)

res = doc.get("results")
rows = res.get("results") if isinstance(res, dict) else (res if isinstance(res, list) else [])

def out_of(r):
    o = r.get("response", {}) or {}
    val = o.get("output", r.get("output", ""))
    return val if isinstance(val, str) else json.dumps(val)
def var(r, k):
    v = (r.get("vars") or {}) or ((r.get("testCase") or {}).get("vars") or {})
    return v.get(k)
def desc(r):
    return (r.get("testCase") or {}).get("description") or r.get("description") or ""
def graded(r):
    gr = r.get("gradingResult") or {}
    return {"pass": bool(r.get("success")), "reason": (gr.get("reason") or "").strip()}
def uses_stub(r):
    s = var(r, "skill") or ""
    return "calibration" in str(s).lower() or "stub" in str(desc(r)).lower()

real = next((r for r in rows if r.get("success") and not uses_stub(r) and var(r, "question")), None)
stub = next((r for r in rows if uses_stub(r) and var(r, "question")), None)
if not real or not stub:
    print(f"capture-example: no usable real+stub pair for '{plugin}' in {results} — keeping any existing snapshot")
    sys.exit(0)

snap = {
    "plugin": plugin,
    "scenario": desc(real),
    "prompt": (var(real, "question") or "").strip(),
    "with_skill":    {"output": out_of(real).strip(), "graded": graded(real)},
    "without_skill": {"output": out_of(stub).strip(), "graded": graded(stub)},
    "provenance": {
        "source": "promptfoo",
        "model": ((real.get("provider") or {}).get("id")
                  if isinstance(real.get("provider"), dict) else real.get("provider")) or "unknown",
        "grader": "anthropic:messages (llm-rubric)",
        "commit": commit or "uncommitted",
        "captured_at": captured or "unknown",
    },
}
path = os.path.join(outdir, f"{plugin}.json")
json.dump(snap, open(path, "w"), indent=2, ensure_ascii=False)
open(path, "a").write("\n")
print(f"capture-example: wrote {path} (with_skill pass={snap['with_skill']['graded']['pass']}, "
      f"without_skill pass={snap['without_skill']['graded']['pass']})")
PY
