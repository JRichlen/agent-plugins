#!/usr/bin/env python3
"""aggregate.py — turn per-attempt results into ONE honest verdict on cost.

  aggregate.py --results <dir> --out <dir>   # writes report.json + summary.md
  aggregate.py --self-test                    # synthetic data; exit 0 iff verdict logic is right

Rules (mirroring the repo's benchmark discipline):
  * every attempt counts in the denominator, including errors, over-budget stops and
    verifier failures; an attempt whose cost is UNKNOWN is COUNTED but EXCLUDED from cost
    means, and the exclusion is printed (unknown usage is never zero);
  * cost is compared only within a matched stratum: if the realized models differ
    between arms, or any attempt's realized model is UNKNOWN, the verdict is
    'not comparable' — never a number;
  * the verdict is on the bootstrap CI of (mean cost jori - mean cost baseline):
    'jori cheaper' iff the CI upper bound < 0, 'jori more expensive' iff the lower
    bound > 0, otherwise 'inconclusive'. n < 2 known-cost attempts per arm is
    'inconclusive (insufficient n)';
  * cost-to-accepted-outcome = total known cost / successes, 'unavailable' when the
    arm has zero successes (zero denominator never renders as a number);
  * a lower mean cost with a lower success rate is reported as such, never as a win.
Standard library only.
"""
import argparse, glob, json, os, random, statistics, sys

UNKNOWN = "UNKNOWN"


def load(results_dir):
    rows = []
    for p in sorted(glob.glob(os.path.join(results_dir, "*.json"))):
        if p.endswith("report.json"):
            continue
        with open(p) as f:
            d = json.load(f)
        if d.get("schema") == "jori-benchmark/attempt/v1":
            rows.append(d)
    return rows


def known_cost(r):
    c = r.get("total_cost_usd")
    return isinstance(c, (int, float)) and not isinstance(c, bool)


def arm_stats(rows):
    n = len(rows)
    succ = sum(1 for r in rows if r["outcome"]["success"])
    costs = [float(r["total_cost_usd"]) for r in rows if known_cost(r)]
    unknown_cost = n - len(costs)
    total = sum(costs)
    models = set()
    for r in rows:
        m = r.get("model_realized")
        if isinstance(m, list):
            models.update(m)
        else:
            models.add(UNKNOWN)
    def mean_or_unavail(vals):
        return statistics.fmean(vals) if vals else "unavailable"
    turns = [r["num_turns"] for r in rows if isinstance(r.get("num_turns"), int)]
    walls = [r["wall_clock_ms"] for r in rows if isinstance(r.get("wall_clock_ms"), int)]
    return {
        "attempts": n, "successes": succ,
        "success_rate": (succ / n) if n else "unavailable",
        "known_cost_attempts": len(costs), "unknown_cost_attempts": unknown_cost,
        "total_cost_usd": total if costs else "unavailable",
        "mean_cost_usd": mean_or_unavail(costs),
        "cost_per_success_usd": (total / succ) if (costs and succ) else "unavailable",
        "mean_turns": mean_or_unavail(turns),
        "mean_wall_clock_ms": mean_or_unavail(walls),
        "delegated_rate": (sum(1 for r in rows if r["adoption"]["delegated"]) / n) if n else "unavailable",
        "realized_models": sorted(models),
        "costs": costs,
    }


def bootstrap_diff(a, b, iters=10000, seed=7):
    rng = random.Random(seed)
    diffs = []
    for _ in range(iters):
        sa = [rng.choice(a) for _ in a]
        sb = [rng.choice(b) for _ in b]
        diffs.append(statistics.fmean(sa) - statistics.fmean(sb))
    diffs.sort()
    return diffs[int(0.025 * iters)], diffs[int(0.975 * iters)]


def verdict(jori, base):
    if jori["attempts"] == 0 or base["attempts"] == 0:
        return "inconclusive (an arm has no attempts)", None
    if UNKNOWN in jori["realized_models"] or UNKNOWN in base["realized_models"]:
        return "not comparable (realized model UNKNOWN in at least one attempt)", None
    if set(jori["realized_models"]) != set(base["realized_models"]):
        return "not comparable (arms ran on different realized models: %s vs %s)" % (jori["realized_models"], base["realized_models"]), None
    if len(jori["costs"]) < 2 or len(base["costs"]) < 2:
        return "inconclusive (insufficient n: need >= 2 known-cost attempts per arm)", None
    lo, hi = bootstrap_diff(jori["costs"], base["costs"])
    if hi < 0:
        v = "jori cheaper"
    elif lo > 0:
        v = "jori more expensive"
    else:
        v = "inconclusive (95% bootstrap CI of the cost difference spans 0)"
    return v, (lo, hi)


def build(rows):
    arms = {a: arm_stats([r for r in rows if r["arm"] == a]) for a in ("jori", "baseline")}
    v, ci = verdict(arms["jori"], arms["baseline"])
    caveats = []
    j, b = arms["jori"], arms["baseline"]
    if isinstance(j["success_rate"], float) and isinstance(b["success_rate"], float) and j["success_rate"] < b["success_rate"] and v == "jori cheaper":
        caveats.append("jori's lower cost comes with a LOWER success rate; cheaper failure is not a saving")
    if j["unknown_cost_attempts"] or b["unknown_cost_attempts"]:
        caveats.append("%d jori / %d baseline attempts had UNKNOWN cost and were excluded from cost means but counted as attempts" % (j["unknown_cost_attempts"], b["unknown_cost_attempts"]))
    if isinstance(j["delegated_rate"], float) and j["delegated_rate"] < 1.0:
        caveats.append("jori arm delegated to subagents in only %.0f%% of attempts — the coordination ritual was not always adopted" % (100 * j["delegated_rate"]))
    tasks = sorted({r["task"] for r in rows})
    modes = sorted({r["mode"] for r in rows})
    if "dry-run" in modes:
        caveats.append("dry-run attempts present: no model was called; cost fields are UNKNOWN by construction")
    for a in arms.values():
        a.pop("costs")
    return {"schema": "jori-benchmark/report/v1", "tasks": tasks, "modes": modes, "arms": arms,
            "cost_difference_ci95": ci, "verdict": v, "caveats": caveats,
            "note": "Cost is Claude Code's reported total_cost_usd per attempt (subagent spend included when the harness includes it in the session total). Textual outcome verification only; this measures cost to a verified outcome for ONE activity, not general savings."}


def fmt(x):
    if isinstance(x, float):
        return "%.4f" % x
    return str(x)


def summary_md(rep):
    j, b = rep["arms"]["jori"], rep["arms"]["baseline"]
    lines = ["# Jori benchmark — %s" % ", ".join(rep["tasks"]), "",
             "**Verdict on cost:** %s" % rep["verdict"], ""]
    if rep["cost_difference_ci95"]:
        lo, hi = rep["cost_difference_ci95"]
        lines += ["95%% bootstrap CI of (jori − baseline) mean cost: [%.4f, %.4f] USD" % (lo, hi), ""]
    lines += ["| metric | jori | baseline |", "|---|---|---|"]
    for k in ("attempts", "successes", "success_rate", "known_cost_attempts", "unknown_cost_attempts",
              "total_cost_usd", "mean_cost_usd", "cost_per_success_usd", "mean_turns", "mean_wall_clock_ms",
              "delegated_rate", "realized_models"):
        lines.append("| %s | %s | %s |" % (k, fmt(j[k]), fmt(b[k])))
    if rep["caveats"]:
        lines += ["", "Caveats:"] + ["- %s" % c for c in rep["caveats"]]
    lines += ["", rep["note"]]
    return "\n".join(lines) + "\n"


def self_test():
    def row(arm, cost, ok, model="m1", delegated=True):
        return {"schema": "jori-benchmark/attempt/v1", "arm": arm, "task": "t", "mode": "live",
                "total_cost_usd": cost, "model_realized": [model] if model else UNKNOWN,
                "num_turns": 3, "wall_clock_ms": 10, "outcome": {"success": ok},
                "adoption": {"delegated": delegated}}
    checks = []
    r = build([row("jori", 0.10, True), row("jori", 0.11, True), row("baseline", 0.50, True), row("baseline", 0.55, True)])
    checks.append(("cheaper", r["verdict"] == "jori cheaper"))
    r = build([row("jori", 0.90, True), row("jori", 0.95, True), row("baseline", 0.10, True), row("baseline", 0.12, True)])
    checks.append(("more expensive", r["verdict"] == "jori more expensive"))
    r = build([row("jori", 0.10, True), row("jori", 0.90, True), row("baseline", 0.50, True), row("baseline", 0.55, True)])
    checks.append(("inconclusive spans 0", r["verdict"].startswith("inconclusive (95%")))
    r = build([row("jori", 0.10, True), row("baseline", 0.50, True), row("baseline", 0.55, True)])
    checks.append(("insufficient n", "insufficient n" in r["verdict"]))
    r = build([row("jori", 0.10, True, model="m2"), row("jori", 0.11, True, model="m2"), row("baseline", 0.50, True), row("baseline", 0.55, True)])
    checks.append(("different models -> not comparable", r["verdict"].startswith("not comparable")))
    r = build([row("jori", 0.10, True, model=None), row("jori", 0.11, True), row("baseline", 0.50, True), row("baseline", 0.55, True)])
    checks.append(("unknown model -> not comparable", r["verdict"].startswith("not comparable")))
    r = build([row("jori", 0.10, False), row("jori", 0.11, False), row("baseline", 0.50, True), row("baseline", 0.55, True)])
    checks.append(("zero successes -> cost_per_success unavailable", r["arms"]["jori"]["cost_per_success_usd"] == "unavailable"))
    checks.append(("cheaper-but-worse caveat", any("LOWER success rate" in c for c in r["caveats"]) and r["verdict"] == "jori cheaper"))
    r = build([row("jori", UNKNOWN, True), row("jori", 0.11, True), row("jori", 0.12, True), row("baseline", 0.50, True), row("baseline", 0.55, True)])
    checks.append(("unknown cost counted but excluded", r["arms"]["jori"]["attempts"] == 3 and r["arms"]["jori"]["known_cost_attempts"] == 2 and any("UNKNOWN cost" in c for c in r["caveats"])))
    r = build([row("jori", 0.10, True, delegated=False), row("jori", 0.11, True), row("baseline", 0.50, True), row("baseline", 0.55, True)])
    checks.append(("non-adoption caveat", any("not always adopted" in c for c in r["caveats"])))
    md = summary_md(r)
    checks.append(("summary renders", "| attempts |" in md and "0%" not in md.split("cost_per_success_usd")[0][-40:]))
    bad = [n for n, ok in checks if not ok]
    for n, ok in checks:
        print(("PASS " if ok else "FAIL ") + n)
    return 0 if not bad else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results"); ap.add_argument("--out"); ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())
    if not (a.results and a.out):
        ap.error("--results and --out are required (or --self-test)")
    rows = load(a.results)
    rep = build(rows)
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "report.json"), "w") as f:
        json.dump(rep, f, indent=1, sort_keys=True)
    md = summary_md(rep)
    with open(os.path.join(a.out, "summary.md"), "w") as f:
        f.write(md)
    print(md)
    sys.exit(0)


if __name__ == "__main__":
    main()
