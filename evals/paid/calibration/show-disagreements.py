#!/usr/bin/env python3
"""Print every disagreement in an agreement.py report as the text a person needs to adjudicate it.

agreement.py names a disagreement by its sample hash (sha256 of scenario plus
output) and the first 70 characters of the scenario. That says two graders
split; it does not say who was right, because the output and both graders'
reasons are not in the report. This joins the report back to the two results
files it was computed from, hashing rows with sample-for-labelling.py's own
functions so the identity cannot drift, and prints for each disagreement: the
scenario, both verdicts, each grader's reason from its model-graded components,
and the output.

Usage: show-disagreements.py <report.json> <results A> <results B> [--name-a A] [--name-b B] [--tail N]
Exit: 0 printed (including "no disagreements"); 2 a disagreement hash found in
neither results file (the report and the results do not belong together).
"""
import argparse, hashlib, importlib.util, json, os, sys

_here = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("sampler", os.path.join(_here, "sample-for-labelling.py"))
S = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(S)

def index(path):
    """hash -> (row, model-graded reasons) for every usable row, first seen wins (as the sampler does)."""
    out = {}
    for r in S.rows_of(json.load(open(path))):
        if S.is_fault(r):
            continue
        body = S.output_text(r)
        if not body.strip():
            continue
        h = hashlib.sha256((S.scenario(r) + "\x00" + body).encode("utf-8")).hexdigest()
        if h in out:
            continue
        comps = ((r.get("gradingResult") or {}).get("componentResults") or [])
        reasons = [str(c.get("reason") or "") for c in comps if S._is_model_graded(c.get("assertion"))]
        out[h] = (r, reasons)
    return out

def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("report"); ap.add_argument("a"); ap.add_argument("b")
    ap.add_argument("--name-a", default="A"); ap.add_argument("--name-b", default="B")
    ap.add_argument("--tail", type=int, default=2000, help="characters of output to print (from the end)")
    a = ap.parse_args()
    rep = json.load(open(a.report))
    dis = rep.get("disagreements") or []
    if not dis:
        print("no disagreements"); return 0
    ia, ib = index(a.a), index(a.b)
    missing = 0
    for d in dis:
        h = d["hash"]
        ra, rb = ia.get(h), ib.get(h)
        if ra is None and rb is None:
            print(f"### {h[:12]} — not found in either results file", file=sys.stderr); missing += 1; continue
        row = (ra or rb)[0]
        print(f"### {S.scenario(row)}  [{h[:12]}]")
        print(f"- {a.name_a}: {d.get(a.name_a, '?').upper()} — {' | '.join((ra or (None, []))[1]) or '(no reason recorded)'}")
        print(f"- {a.name_b}: {d.get(a.name_b, '?').upper()} — {' | '.join((rb or (None, []))[1]) or '(no reason recorded)'}")
        body = S.output_text(row)
        cut = "" if len(body) <= a.tail else f"(last {a.tail} of {len(body)} chars)\n"
        print("- output:\n\n```\n" + cut + body[-a.tail:] + "\n```\n")
    return 2 if missing else 0

if __name__ == "__main__":
    sys.exit(main())
