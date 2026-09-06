#!/usr/bin/env python3
"""sample-for-labelling.py — draw a blind labelling sheet from promptfoo results.

Issue #102, measurement 2: the only way out of the model-grades-model circle is
a human grading the same outputs against the same rubric, blind. This script
turns one or more results.json files into two files:

  sheet.json     — what the human sees: scenario, request, the subject's output,
                   and an empty "label" slot. No verdict, no provider, no hint
                   of which side (with-skill / without-skill / stub) it came from.
  verdicts.json  — what the grader said, keyed by the sha256 of the output text,
                   kept apart so the labeller cannot peek. agreement.py joins
                   the two on the hash.

Sampling is seeded (default seed 0) so a sheet is reproducible from the same
results. Rows the scorer treats as transport FAULTs are excluded — nobody
should label a 504.

Usage:
  sample-for-labelling.py RESULTS.json [RESULTS2.json ...] --n 20 [--seed 0]
                          [--sheet sheet.json] [--verdicts verdicts.json]
Exit: 0 wrote both files; 2 nothing usable to sample.
"""
import argparse, hashlib, json, random, re, sys

_DEGEN = re.compile(r'^(?:\s*</?think>\s*)+$', re.IGNORECASE)

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

def is_fault(r):
    fr = r.get("failureReason")
    if fr == 2 or (isinstance(fr, str) and fr.strip().lower() == "error"):
        return True
    no_reason = fr is None or (isinstance(fr, str) and not fr.strip())
    if no_reason and isinstance(r.get("error"), str) and r["error"].strip():
        return True
    body = output_text(r).strip()
    return (r.get("success") is not True) and bool(body) and bool(_DEGEN.match(body))

def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("results", nargs="+")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--sheet", default="sheet.json")
    ap.add_argument("--verdicts", default="verdicts.json")
    a = ap.parse_args()
    pool = {}
    for path in a.results:
        try:
            doc = json.load(open(path))
        except Exception as e:
            print(f"sample: cannot parse {path}: {e}", file=sys.stderr); return 2
        for r in rows_of(doc):
            if is_fault(r):
                continue
            body = output_text(r)
            if not body.strip():
                continue
            h = hashlib.sha256(body.encode("utf-8")).hexdigest()
            # the same output text graded twice keeps the first verdict seen
            pool.setdefault(h, {"hash": h, "scenario": scenario(r), "request": request_of(r),
                                "output": body, "verdict": "pass" if r.get("success") is True else "fail"})
    if not pool:
        print("sample: no usable rows (all faults or empty)", file=sys.stderr); return 2
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
