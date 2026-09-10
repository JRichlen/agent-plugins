#!/usr/bin/env python3
"""sample-for-labelling.py — draw a blind labelling sheet from promptfoo results.

Issue #102, measurement 2: the only way out of the model-grades-model circle is
a human grading the same outputs against the same rubric, blind. This script
turns one or more results.json files into two files:

  sheet.json     — what the human sees: scenario, request, the subject's output,
                   and an empty "label" slot. No verdict, no provider, no hint
                   of which side (with-skill / without-skill / stub) it came from.
  verdicts.json  — what the grader said, keyed by the sha256 of scenario plus
                   output text (pass/fail depends on the scenario's rubric, so
                   the same stock answer under two rubrics is two rows), kept
                   apart so the labeller cannot peek. agreement.py joins the
                   two on the hash.

Sampling is seeded (default seed 0) so a sheet is reproducible from the same
results. Transport and grader FAULTs are excluded because they have no valid
judgment. Empty/truncated subject answers remain visible failed samples.

Usage:
  sample-for-labelling.py RESULTS.json [RESULTS2.json ...] --n 20 [--seed 0]
                          [--sheet sheet.json] [--verdicts verdicts.json]
                          [--model-graded-only]
--model-graded-only takes the verdict from the model-graded assertion(s) of the
row (pass iff every llm-rubric-style component passed) instead of the row's
overall success, and skips rows that have no model-graded component; use it
when comparing grader against grader (measurement 3), so a deterministic
assertion such as `icontains` cannot force the same verdict on both sides.
Exit: 0 wrote both files; 2 nothing usable to sample.
"""
import argparse, hashlib, json, random, sys

def rows_of(doc):
    res = doc.get("results")
    if isinstance(res, dict):
        return res.get("results") or []
    return res if isinstance(res, list) else []

def scenario(r):
    tc = r.get("testCase") or {}
    for cand in (tc.get("description"), r.get("description")):
        if cand:
            return str(cand)
    v = (r.get("vars") or {}) or (tc.get("vars") or {})
    return str(v.get("request") or v.get("question") or "<unlabeled>")

def request_of(r):
    v = (r.get("vars") or {}) or ((r.get("testCase") or {}).get("vars") or {})
    return str(v.get("request") or v.get("question") or "")

def output_text(r):
    resp = r.get("response") or {}
    out = resp.get("output")
    if out is None:
        out = r.get("output")
    if out is None:
        return ""
    # canonical dump so semantically identical JSON outputs hash identically
    return out if isinstance(out, str) else json.dumps(out, sort_keys=True, separators=(",", ":"))

_MODEL_GRADED = ("llm-rubric", "model-graded-closedqa", "model-graded-factuality", "factuality", "answer-relevance",
                 "context-faithfulness", "context-recall", "context-relevance", "g-eval", "select-best", "pi")

def _is_model_graded(a):
    t = str((a or {}).get("type", ""))
    return t in _MODEL_GRADED or t.startswith("llm-") or t.startswith("model-graded")

def model_graded_verdict(r):
    """'pass'/'fail' from the row's model-graded components only; None if it has none."""
    comps = ((r.get("gradingResult") or {}).get("componentResults") or [])
    mg = [c for c in comps if _is_model_graded(c.get("assertion"))]
    if not mg:
        return None
    if any(has_grader_fault(c) for c in mg):
        # An independent deterministic failure can settle the overall row,
        # but cannot supply the model judgment this mode is comparing.
        return "fail" if any(c.get("pass") is False and not has_grader_fault(c) for c in mg) else None
    return "pass" if all(c.get("pass") is True for c in mg) else "fail"

def has_grader_fault(result):
    """Read typed grading evidence, never subject text or an error string."""
    if not isinstance(result, dict):
        return False
    metadata = result.get("metadata")
    if isinstance(metadata, dict) and metadata.get("graderError") is True:
        return True
    components = result.get("componentResults")
    return isinstance(components, list) and any(has_grader_fault(c) for c in components)

def independent_assertion_failure(r, doc):
    # Match pass-rate.sh's default conjunction contract; aggregate/custom
    # scoring and flattened nested sets cannot establish this from one leaf.
    default = ((doc or {}).get("config") or {}).get("defaultTest") or {}
    for scope in (default, r.get("testCase") or {}):
        if scope.get("threshold") is not None or scope.get("assertScoringFunction") is not None:
            return False
    components = (r.get("gradingResult") or {}).get("componentResults")
    if not isinstance(components, list) or any(
        not isinstance(c, dict) or "componentResults" in c or
        (isinstance(c.get("metadata"), dict) and "assertionSet" in c["metadata"])
        for c in components
    ):
        return False
    return r.get("success") is not True and any(
        c.get("pass") is False and not has_grader_fault(c) for c in components
    )

def is_fault(r, doc=None):
    fr = r.get("failureReason")
    if fr == 2 or (isinstance(fr, str) and fr.strip().lower() == "error"):
        return True
    if has_grader_fault(r.get("gradingResult")):
        return not independent_assertion_failure(r, doc)
    no_reason = fr is None or (isinstance(fr, str) and not fr.strip())
    if no_reason and isinstance(r.get("error"), str) and r["error"].strip():
        return True
    return False

def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("results", nargs="+")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--sheet", default="sheet.json")
    ap.add_argument("--verdicts", default="verdicts.json")
    ap.add_argument("--model-graded-only", action="store_true")
    a = ap.parse_args()
    pool = {}
    for path in a.results:
        try:
            doc = json.load(open(path))
        except Exception as e:
            print(f"sample: cannot parse {path}: {e}", file=sys.stderr); return 2
        for r in rows_of(doc):
            if is_fault(r, doc):
                continue
            body = output_text(r)
            sc = scenario(r)
            verdict = "pass" if r.get("success") is True else "fail"
            if a.model_graded_only:
                verdict = model_graded_verdict(r)
                if verdict is None:
                    continue
            # identity is (scenario, output): the verdict belongs to a rubric, not
            # to the text alone. Repeats of one output under one scenario keep the
            # first verdict seen.
            h = hashlib.sha256((sc + "\x00" + body).encode("utf-8")).hexdigest()
            pool.setdefault(h, {"hash": h, "scenario": sc, "request": request_of(r),
                                "output": body, "verdict": verdict})
    if not pool:
        print("sample: no usable judgments (all faults or no matching assertions)", file=sys.stderr); return 2
    items = sorted(pool.values(), key=lambda x: x["hash"])
    random.Random(a.seed).shuffle(items)
    items = items[: a.n]
    sheet = [{"hash": i["hash"], "scenario": i["scenario"], "request": i["request"],
              "output": i["output"], "label": None} for i in items]
    verdicts = {i["hash"]: i["verdict"] for i in items}
    json.dump(sheet, open(a.sheet, "w"), indent=2, ensure_ascii=False)
    json.dump(verdicts, open(a.verdicts, "w"), indent=2, sort_keys=True)
    print(f"sample: wrote {len(sheet)} rows to {a.sheet} (labels blank) and {len(verdicts)} grader verdicts to {a.verdicts} (keep it out of sight while labelling)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
