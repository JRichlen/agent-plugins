#!/usr/bin/env python3
"""agreement.py — how often do two graders agree, beyond chance?

Issue #102, measurements 2 and 3. Joins two label sets on the sample hash (scenario plus output) and
reports percent agreement, Cohen's kappa, the confusion matrix, and every
disagreement (with scenario when a sheet is given). The same script serves
human-vs-grader (a filled sheet vs verdicts.json), grader-vs-grader (two
verdict files from two grader models), and grader-vs-itself (two verdict files
from repeated grading runs).

Inputs are either a labelling sheet (a list of {hash, label, ...}) or a verdict
map ({hash: "pass"|"fail"}); the script accepts both shapes for either side.
Labels must be "pass" or "fail"; a sheet row whose label is null is skipped and
counted as unlabelled.

Usage:
  agreement.py A.json B.json [--name-a human] [--name-b grader] [--json out.json]
A verdict file with a .b64 suffix is base64-decoded first (the calibration-sheet
workflow seals verdicts that way so they are not read by accident while labelling).
Exit: 0 report printed; 2 fewer than two hashes in common (nothing to compare).

Kappa is (po - pe) / (1 - pe); when pe == 1 (both sides gave one label to
everything) kappa is undefined and reported as null with the reason.
"""
import argparse, json, sys

def load(path):
    if path.endswith(".b64"):
        import base64
        with open(path, "rb") as f:
            doc = json.loads(base64.b64decode(f.read()))
    else:
        with open(path) as f:
            doc = json.load(f)
    if isinstance(doc, dict):
        return {h: str(v).strip().lower() for h, v in doc.items() if v is not None and str(v).strip()}, {}, 0
    labels, meta, unl = {}, {}, 0
    for row in doc:
        h = row.get("hash")
        if not h:
            continue
        meta[h] = row.get("scenario", "")
        if row.get("label") is None or str(row.get("label")).strip() == "":
            unl += 1; continue
        labels[h] = str(row["label"]).strip().lower()
    return labels, meta, unl

def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("a"); ap.add_argument("b")
    ap.add_argument("--name-a", default="A"); ap.add_argument("--name-b", default="B")
    ap.add_argument("--json", default=None, help="also write the report as JSON")
    args = ap.parse_args()
    la, ma, ua = load(args.a); lb, mb, ub = load(args.b)
    for side, labels in ((args.name_a, la), (args.name_b, lb)):
        bad = sorted({v for v in labels.values() if v not in ("pass", "fail")})
        if bad:
            print(f"agreement: {side} has labels outside pass/fail: {bad}", file=sys.stderr); return 2
    common = sorted(set(la) & set(lb))
    if len(common) < 2:
        print(f"agreement: only {len(common)} hash(es) in common — nothing to compare (unlabelled: {args.name_a}={ua}, {args.name_b}={ub})", file=sys.stderr); return 2
    n = len(common)
    cm = {"pass": {"pass": 0, "fail": 0}, "fail": {"pass": 0, "fail": 0}}
    for h in common:
        cm[la[h]][lb[h]] += 1
    agree = cm["pass"]["pass"] + cm["fail"]["fail"]
    po = agree / n
    pa_pass = (cm["pass"]["pass"] + cm["pass"]["fail"]) / n
    pb_pass = (cm["pass"]["pass"] + cm["fail"]["pass"]) / n
    pe = pa_pass * pb_pass + (1 - pa_pass) * (1 - pb_pass)
    kappa = None if abs(1 - pe) < 1e-12 else (po - pe) / (1 - pe)
    dis = [{"hash": h, "scenario": ma.get(h) or mb.get(h) or "", args.name_a: la[h], args.name_b: lb[h]} for h in common if la[h] != lb[h]]
    print(f"agreement: n={n}  agree={agree}  percent={po*100:.1f}%  kappa={'undefined (both sides used one label)' if kappa is None else f'{kappa:.3f}'}")
    print(f"  {args.name_a}\\{args.name_b:>6}   pass  fail")
    print(f"  pass          {cm['pass']['pass']:4d}  {cm['pass']['fail']:4d}")
    print(f"  fail          {cm['fail']['pass']:4d}  {cm['fail']['fail']:4d}")
    if ua or ub:
        print(f"  unlabelled rows skipped: {args.name_a}={ua}, {args.name_b}={ub}")
    for d in dis:
        print(f"  disagree  {args.name_a}={d[args.name_a]:4s} {args.name_b}={d[args.name_b]:4s}  {d['hash'][:12]}  {d['scenario'][:70]}")
    if args.json:
        json.dump({"n": n, "agree": agree, "percent": po * 100, "kappa": kappa, "confusion": cm,
                   "disagreements": dis, "unlabelled": {args.name_a: ua, args.name_b: ub}},
                  open(args.json, "w"), indent=2)
    return 0

if __name__ == "__main__":
    sys.exit(main())
