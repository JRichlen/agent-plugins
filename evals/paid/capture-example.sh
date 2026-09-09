#!/usr/bin/env bash
#
# capture-example.sh RESULTS.json PLUGIN [--out DIR] [--commit SHA] [--captured-at ISO8601]
#                    [--run-url URL] [--attestation github|none] [--pack DIR]
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
# and provenance that DISCLOSES every model involved by role:
#   subject_model  the model that answered (from the results' provider id)
#   grader_model   the llm-rubric grader, read from the pack's promptfooconfig
#                  (defaultTest.options.provider.id) — never hard-coded here
#   judge_model    who judged the with/without divergence (a graded pair has
#                  none; the grades themselves are the judgement)
#   run_url        the GitHub Actions run that produced results.json, so a
#                  reader can open the log the outputs came from
#   attestation    "github" when the workflow signs the snapshot with
#                  actions/attest-build-provenance (verifiable with
#                  `gh attestation verify`), else "none"
# It also refuses to write a pair whose subject and grader are the same model
# family (a model grading itself is not a grade). Timestamps, commit and run URL
# come from ARGS (CI supplies them) — never Date.now()/git here, so a re-run on
# the same inputs is reproducible.
#
# A results file that lacks a usable pair for the plugin is NOT an error: it
# prints a skip notice and exits 0, so a plugin whose pack didn't run this CI
# leg simply keeps its previous snapshot.
#
# Exit: 0 captured or cleanly skipped; 2 usage / unreadable results.
set -uo pipefail

RESULTS=""; PLUGIN=""; OUT="docs/examples/data"; COMMIT=""; CAPTURED=""; RUN_URL=""; ATTEST="none"; PACK=""
while [ $# -gt 0 ]; do
  case "$1" in
    --out)         OUT="${2:?}"; shift 2 ;;
    --commit)      COMMIT="${2:?}"; shift 2 ;;
    --captured-at) CAPTURED="${2:?}"; shift 2 ;;
    --run-url)     RUN_URL="${2:?}"; shift 2 ;;
    --attestation) ATTEST="${2:?}"; shift 2 ;;
    --pack)        PACK="${2:?}"; shift 2 ;;
    -*)            echo "capture-example: unknown flag $1" >&2; exit 2 ;;
    *) if [ -z "$RESULTS" ]; then RESULTS="$1"; elif [ -z "$PLUGIN" ]; then PLUGIN="$1"; fi; shift ;;
  esac
done
[ -n "$RESULTS" ] && [ -n "$PLUGIN" ] || { echo "usage: capture-example.sh RESULTS.json PLUGIN [--out DIR] [--commit SHA] [--captured-at ISO8601] [--run-url URL] [--attestation github|none] [--pack DIR]" >&2; exit 2; }
[ -f "$RESULTS" ] || { echo "capture-example: no such file: $RESULTS" >&2; exit 2; }
case "$ATTEST" in github|none) ;; *) echo "capture-example: --attestation must be 'github' or 'none' (got '$ATTEST')" >&2; exit 2 ;; esac
# The pack directory defaults to the results file's own directory — that is
# where the promptfoo config that named the grader lives.
[ -n "$PACK" ] || PACK="$(dirname "$RESULTS")"
mkdir -p "$OUT"

python3 - "$RESULTS" "$PLUGIN" "$OUT" "$COMMIT" "$CAPTURED" "$RUN_URL" "$ATTEST" "$PACK" <<'PY'
import collections, json, os, re, sys
results, plugin, outdir, commit, captured, run_url, attest, pack = sys.argv[1:9]
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
    # A skip used to be one opaque line, so two full refresh runs (2026-09-01 and
    # 2026-09-08) captured nothing across all 12 packs and still reported success —
    # roughly 50 minutes of paid API time with no way to see why. Say exactly what
    # the results file contained and what the most common failure was, so the next
    # reader has the cause and not a mystery.
    qrows  = [r for r in rows if var(r, "question")]
    reals  = [r for r in qrows if not uses_stub(r)]
    stubs  = [r for r in qrows if uses_stub(r)]
    okr    = sum(1 for r in reals if r.get("success"))
    oks    = sum(1 for r in stubs if r.get("success"))
    reasons = collections.Counter()
    for r in reals:
        if r.get("success"):
            continue
        why = ((r.get("gradingResult") or {}).get("reason") or "").strip() or \
              ((r.get("error") or "") if isinstance(r.get("error"), str) else "") or \
              "(no reason recorded)"
        reasons[" ".join(why.split())[:160]] += 1
    print(f"capture-example: NO SNAPSHOT for '{plugin}' — nothing captured from {results}")
    print(f"  rows: {len(rows)} total, {len(qrows)} with a question "
          f"| real-skill {len(reals)} ({okr} passed) | stub/calibration {len(stubs)} ({oks} passed)")
    if not reals:
        print("  cause: NO real-skill rows at all — the pack produced no gradeable non-calibration result")
    elif okr == 0:
        print("  cause: every real-skill row FAILED — a snapshot needs at least one passing one")
        for why, n in reasons.most_common(3):
            print(f"    x{n}: {why}")
    if not stubs:
        print("  cause: NO stub/calibration row — the pack has no negative control to pair against")
    print("  the previous snapshot (if any) stands; nothing was overwritten")
    sys.exit(0)

def provider_id(r):
    p = r.get("provider")
    return (p.get("id") if isinstance(p, dict) else p) or "unknown"

def family(model_id):
    """Vendor/family of a provider id: 'anthropic:messages:claude-x' -> anthropic;
    'openrouter:nvidia/nemotron' -> nvidia; 'openrouter:anthropic/claude' -> anthropic."""
    m = str(model_id).lower()
    if m.startswith("openrouter:"):
        rest = m.split(":", 1)[1]
        return rest.split("/", 1)[0] if "/" in rest else rest
    return m.split(":", 1)[0]

def grader_from_pack(pack_dir):
    """The llm-rubric grader is whatever the pack's promptfooconfig names under
    defaultTest.options.provider — read it, never assume it."""
    cfg = os.path.join(pack_dir, "promptfooconfig.yaml")
    if not os.path.isfile(cfg):
        return None
    try:
        import yaml
        doc = yaml.safe_load(open(cfg))
        prov = (((doc or {}).get("defaultTest") or {}).get("options") or {}).get("provider")
        if isinstance(prov, dict):
            return prov.get("id")
        if isinstance(prov, str):
            return prov
    except Exception:
        pass
    # PyYAML unavailable or an odd shape: fall back to the unambiguous marker
    # the CI grader-model job also greps for.
    m = re.search(r"id:\s*(anthropic:messages:[^\s]+)", open(cfg).read())
    return m.group(1) if m else None

subject = provider_id(real)
if provider_id(stub) != subject:
    print(f"capture-example: subject provider differs between the real ({subject}) and stub ({provider_id(stub)}) rows — not a like-for-like pair; skipping", file=sys.stderr)
    sys.exit(0)
grader = grader_from_pack(pack)
if not grader:
    print(f"capture-example: cannot read the grader model from {pack}/promptfooconfig.yaml — refusing to write a snapshot with undisclosed grading", file=sys.stderr)
    sys.exit(2)
if family(subject) == family(grader):
    print(f"capture-example: subject ({subject}) and grader ({grader}) are the same model family — a model grading itself is not a grade; refusing to write", file=sys.stderr)
    sys.exit(2)

snap = {
    "plugin": plugin,
    "scenario": desc(real),
    "prompt": (var(real, "question") or "").strip(),
    "with_skill":    {"output": out_of(real).strip(), "graded": graded(real)},
    "without_skill": {"output": out_of(stub).strip(), "graded": graded(stub)},
    "provenance": {
        "source": "promptfoo",
        "workflow": (re.search(r"/actions/runs/\d+", run_url) and "github-actions") if run_url else None,
        "subject_model": subject,
        "grader_model": grader + " (llm-rubric)",
        "judge_model": "none — a graded pair: the pass/fail grades from grader_model are the judgement; no separate divergence judge",
        "same_family_judge": False,
        "commit": commit or "uncommitted",
        "captured_at": captured or "unknown",
        "run_url": run_url or None,
        "attestation": ("github — signed by actions/attest-build-provenance in the run above; verify with: gh attestation verify docs/examples/data/%s.json --repo JRichlen/agent-plugins" % plugin)
                       if attest == "github" else "none — captured without a signed attestation",
    },
}
path = os.path.join(outdir, f"{plugin}.json")
json.dump(snap, open(path, "w"), indent=2, ensure_ascii=False)
open(path, "a").write("\n")
print(f"capture-example: wrote {path} (with_skill pass={snap['with_skill']['graded']['pass']}, "
      f"without_skill pass={snap['without_skill']['graded']['pass']}; subject={subject}; grader={grader})")
PY
