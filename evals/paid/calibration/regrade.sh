#!/usr/bin/env bash
# evals/paid/calibration/regrade.sh — re-grade a finished run's cached outputs
# with another grader, or the same grader again (issue #102, measurement 3).
#
# Writes, beside the pack, an overlay config whose provider is the replay
# provider (evals/paid/calibration/replay-provider.js) and whose tests are one
# per usable sample of RESULTS.json: the sample's own vars plus `__replay`, and
# the sample's own assertions copied from the results row. The grader is the
# one named on the command line. Nothing in the pack is modified; the overlay,
# the replay map and the regrade results are git-ignored.
#
# Samples are keyed exactly as sample-for-labelling.py keys them (sha256 of
# scenario + NUL + output), so the verdicts a regrade produces join the
# original verdicts in agreement.py on the same hash. Only MODEL-GRADED
# assertions are replayed (llm-rubric and its relatives): a deterministic
# assertion such as `icontains` would force the same verdict on both sides
# and inflate agreement. Compare against original verdicts drawn with
# sample-for-labelling.py --model-graded-only for the same reason. The
# replayed text is the sampler's canonical text (a non-string output is
# replayed as the canonical JSON that was hashed), never the raw object.
#
# Usage:
#   regrade.sh PACK_DIR RESULTS.json --grader ID [--label NAME]   # write overlay + replay map; print the overlay path
#   regrade.sh PACK_DIR --grader-id [--from RESULTS.json]         # print the grader that graded RESULTS (its rows, or a
#                                                                  #   config beside it), else the pack's own grader; says which
#   regrade.sh --self-test                                        # offline fixture; non-zero on failure
# Exit: 0 ok; 2 usage or nothing usable; 3 PyYAML missing (said, never silent).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

py() { python3 - "$HERE" "$@" <<'PY'
import sys, os, json, hashlib, importlib.util
here = sys.argv[1]; argv = sys.argv[2:]
try:
    import yaml
except Exception:
    print("regrade: PyYAML is not available; cannot read the pack config (exit 3)", file=sys.stderr); sys.exit(3)
spec = importlib.util.spec_from_file_location("sampler", os.path.join(here, "sample-for-labelling.py"))
sampler = importlib.util.module_from_spec(spec); spec.loader.exec_module(sampler)
USAGE = "usage: regrade.sh PACK_DIR RESULTS.json --grader ID [--label NAME] | PACK_DIR --grader-id [--from RESULTS.json] | --self-test"
MODEL_GRADED = ("llm-rubric", "model-graded-closedqa", "model-graded-factuality", "factuality", "answer-relevance",
                "context-faithfulness", "context-recall", "context-relevance", "g-eval", "select-best", "pi")
def model_graded(a):
    t = str(a.get("type", ""))
    return t in MODEL_GRADED or t.startswith("llm-") or t.startswith("model-graded")

def grader_of(results):
    """The grader that graded RESULTS: from its rows (defaultTest options are merged
    into every testCase), else from a promptfooconfig*.yaml beside it. None if unknown."""
    try:
        doc = json.load(open(results))
    except Exception:
        return None, None
    for r in sampler.rows_of(doc):
        prov = (((r.get("testCase") or {}).get("options") or {}).get("provider"))
        gid = prov.get("id") if isinstance(prov, dict) else prov
        if gid:
            return str(gid), "the results rows"
    import glob
    for cfg in sorted(glob.glob(os.path.join(os.path.dirname(os.path.abspath(results)), "promptfooconfig*.yaml"))):
        try:
            c = yaml.safe_load(open(cfg)) or {}
        except Exception:
            continue
        prov = ((c.get("defaultTest") or {}).get("options") or {}).get("provider")
        gid = prov.get("id") if isinstance(prov, dict) else prov
        if gid:
            return str(gid), os.path.basename(cfg) + " beside the results"
    return None, None

def build(pack, results, grader, label):
    src = os.path.join(pack, "promptfooconfig.yaml")
    if not os.path.isfile(src):
        print(f"regrade: no promptfooconfig.yaml in {pack}", file=sys.stderr); return 2
    cfg = yaml.safe_load(open(src)) or {}
    try:
        doc = json.load(open(results))
    except Exception as e:
        print(f"regrade: cannot parse {results}: {e}", file=sys.stderr); return 2
    tests, replay, seen, skipped = [], {}, set(), 0
    for r in sampler.rows_of(doc):
        if sampler.is_fault(r):
            continue
        body = sampler.output_text(r)
        if not body.strip():
            continue
        sc = sampler.scenario(r)
        h = hashlib.sha256((sc + "\x00" + body).encode("utf-8")).hexdigest()
        if h in seen:
            continue
        tc = r.get("testCase") or {}
        asserts = tc.get("assert")
        if not asserts:
            asserts = [c.get("assertion") for c in ((r.get("gradingResult") or {}).get("componentResults") or []) if c.get("assertion")]
        asserts = [a for a in (asserts or []) if isinstance(a, dict) and a.get("type") and model_graded(a)]
        if not asserts:
            skipped += 1; continue
        seen.add(h)
        vars_ = dict((r.get("vars") or {}) or (tc.get("vars") or {}))
        vars_["__replay"] = h
        replay[h] = body   # the canonical text that was hashed, never the raw object
        tests.append({"description": sc, "vars": vars_, "assert": asserts})
    if not tests:
        print("regrade: no usable rows with assertions in the results (exit 2)", file=sys.stderr); return 2
    provider_js = os.path.join(here, "replay-provider.js")
    replay_path = os.path.join(pack, f"replay.{label}.json")
    overlay = {k: v for k, v in cfg.items() if k not in ("providers", "tests", "evaluateOptions", "defaultTest")}
    overlay["providers"] = [{"id": "file://" + os.path.abspath(provider_js), "label": "replay", "config": {"file": os.path.abspath(replay_path)}}]
    eo = dict(cfg.get("evaluateOptions") or {}); eo.pop("repeat", None)
    if eo: overlay["evaluateOptions"] = eo
    dt = json.loads(json.dumps(cfg.get("defaultTest") or {}))
    gcfg = {}
    prov = ((dt.get("options") or {}).get("provider"))
    if isinstance(prov, dict) and isinstance(prov.get("config"), dict):
        gcfg = prov["config"]
    dt.setdefault("options", {})["provider"] = {"id": grader, "config": gcfg or {"max_tokens": 4096}}
    overlay["defaultTest"] = dt
    for t in tests:
        t.pop("options", None)
    overlay["tests"] = tests
    json.dump(replay, open(replay_path, "w"), ensure_ascii=False)
    out = os.path.join(pack, f"promptfooconfig.regrade.{label}.yaml")
    with open(out, "w") as f:
        f.write(f"# GENERATED by evals/paid/calibration/regrade.sh — replays {len(tests)} cached outputs from\n"
                f"# {os.path.basename(results)} and grades them with {grader}. Not committed; never a required leg.\n")
        yaml.safe_dump(overlay, f, sort_keys=False, allow_unicode=True)
    print(f"regrade: {len(tests)} samples to re-grade with {grader} ({skipped} rows without a model-graded assertion skipped)", file=sys.stderr)
    print(out); return 0

if argv and argv[0] == "--self-test":
    import tempfile
    d = tempfile.mkdtemp(); pack = os.path.join(d, "pack"); os.makedirs(pack)
    yaml.safe_dump({"description": "fixture", "prompts": ["file://prompt.txt"],
                    "providers": [{"id": "openrouter:base/model", "config": {"max_tokens": 8192}}],
                    "evaluateOptions": {"repeat": 3, "maxConcurrency": 3},
                    "defaultTest": {"vars": {"skill": "file://skill.md"}, "options": {"provider": {"id": "anthropic:messages:grader-a", "config": {"max_tokens": 4096}}}},
                    "tests": [{"description": "S1"}]}, open(os.path.join(pack, "promptfooconfig.yaml"), "w"), sort_keys=False)
    def row(desc, out, ok, prov="openrouter:base/model", asserts=True):
        r = {"testCase": {"description": desc, "vars": {"question": "q"}}, "vars": {"question": "q", "skill": "SKILL TEXT"},
             "provider": {"id": prov}, "success": ok, "failureReason": 0 if ok else 1, "error": None if ok else "rubric",
             "response": {"output": out}}
        if asserts: r["testCase"]["assert"] = [{"type": "llm-rubric", "value": f"rubric for {desc}"}]
        return r
    rows = [row("S1", "answer one", True), row("S1", "answer one", False), row("S1", "answer two", False, prov="anthropic:messages:x"),
            row("S2", "answer three", True), row("S2", "", True), row("S3", "no assertions here", True, asserts=False)]
    # a structured (non-string) output: hashed and replayed as canonical JSON
    j = row("S4", {"b": 1, "a": [2]}, True); rows.append(j)
    # a deterministic assertion beside the rubric: dropped from the replay, and a
    # row whose only assertion is deterministic is skipped
    m = row("S5", "mixed", True); m["testCase"]["assert"].append({"type": "icontains", "value": "bundle"}); rows.append(m)
    d5 = row("S6", "deterministic only", True); d5["testCase"]["assert"] = [{"type": "icontains", "value": "x"}]; rows.append(d5)
    rows[0]["testCase"]["options"] = {"provider": {"id": "anthropic:messages:grader-a", "config": {"max_tokens": 4096}}}
    rows.append({"testCase": {"description": "S1"}, "vars": {}, "provider": {"id": "openrouter:base/model"}, "success": False,
                 "failureReason": 2, "error": "504", "response": {"output": ""}})
    res = os.path.join(d, "results.json"); json.dump({"results": {"results": rows}}, open(res, "w"))
    rc = build(pack, res, "openrouter:other/grader", "cross")
    assert rc == 0, rc
    back = yaml.safe_load(open(os.path.join(pack, "promptfooconfig.regrade.cross.yaml")))
    ids = [t["description"] for t in back["tests"]]
    assert ids == ["S1", "S1", "S2", "S4", "S5"], ids          # dedup by (scenario, output); blank, no-assert, deterministic-only and FAULT rows dropped
    canon = json.dumps({"b": 1, "a": [2]}, sort_keys=True, separators=(",", ":"))
    assert json.load(open(os.path.join(pack, "replay.cross.json")))[hashlib.sha256(("S4" + "\x00" + canon).encode()).hexdigest()] == canon
    s5 = [t for t in back["tests"] if t["description"] == "S5"][0]
    assert [a["type"] for a in s5["assert"]] == ["llm-rubric"], s5["assert"]   # icontains dropped
    gid, src = grader_of(res)
    assert gid == "anthropic:messages:grader-a" and src == "the results rows", (gid, src)
    assert back["providers"][0]["id"].startswith("file://") and back["providers"][0]["id"].endswith("replay-provider.js"), back["providers"]
    assert back["defaultTest"]["options"]["provider"] == {"id": "openrouter:other/grader", "config": {"max_tokens": 4096}}, back["defaultTest"]
    assert "repeat" not in (back.get("evaluateOptions") or {}) and back["evaluateOptions"] == {"maxConcurrency": 3}, back.get("evaluateOptions")
    assert back["defaultTest"]["vars"] == {"skill": "file://skill.md"}
    rep = json.load(open(os.path.join(pack, "replay.cross.json")))
    assert set(rep.values()) == {"answer one", "answer two", "answer three", canon, "mixed"}, rep
    for t in back["tests"]:
        assert t["vars"]["__replay"] in rep and t["assert"] == [{"type": "llm-rubric", "value": f"rubric for {t['description']}"}], t
        assert rep[t["vars"]["__replay"]] and t["vars"]["skill"] == "SKILL TEXT"
    # the hashes are the sampler's hashes, so verdicts join across runs
    h = hashlib.sha256(("S2" + "\x00" + "answer three").encode()).hexdigest()
    assert h in rep and rep[h] == "answer three"
    print("regrade self-test: overlay replays one test per usable (scenario, output) with its model-graded assertions only, canonical text, keyed by the sampler's hash, graded by the requested grader, repeat removed, pack untouched; the source run's grader is read from its rows")
    sys.exit(0)

if len(argv) >= 2 and argv[1] == "--grader-id":
    if len(argv) >= 4 and argv[2] == "--from":
        gid, src = grader_of(argv[3])
        if gid:
            print(f"regrade: grader taken from {src}", file=sys.stderr); print(gid); sys.exit(0)
        print("regrade: the results carry no grader id and no config sits beside them; falling back to the pack in this checkout", file=sys.stderr)
    cfg = yaml.safe_load(open(os.path.join(argv[0], "promptfooconfig.yaml"))) or {}
    prov = ((cfg.get("defaultTest") or {}).get("options") or {}).get("provider")
    gid = prov.get("id") if isinstance(prov, dict) else prov
    if not gid:
        print("regrade: the pack declares no grader (defaultTest.options.provider)", file=sys.stderr); sys.exit(2)
    print(gid); sys.exit(0)

if len(argv) < 4 or argv[2] != "--grader" or not argv[3].strip():
    print(f"regrade: {USAGE}", file=sys.stderr); sys.exit(2)
label = "regrade"
if len(argv) >= 6 and argv[4] == "--label" and argv[5].strip():
    label = argv[5].strip()
import re
if not re.fullmatch(r"[A-Za-z0-9._-]+", label):
    print("regrade: --label must be a plain name", file=sys.stderr); sys.exit(2)
sys.exit(build(argv[0], argv[1], argv[3].strip(), label))
PY
}

case "${1:-}" in
  --self-test) py --self-test ;;
  "") echo "usage: regrade.sh PACK_DIR RESULTS.json --grader ID [--label NAME] | PACK_DIR --grader-id [--from RESULTS.json] | --self-test" >&2; exit 2 ;;
  *) py "$@" ;;
esac
