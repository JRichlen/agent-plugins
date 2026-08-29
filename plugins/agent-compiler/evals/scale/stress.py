#!/usr/bin/env python3
"""Scale/stress harness for the agent-compiler kernel.

The cheap tier proves the invariant on two golden examples. This suite proves
the SAME invariant holds at scale, on inputs nobody hand-picked: it generates
large randomized registries (seeded — every run is reproducible from its seed)
and asserts, for every generated registry x query pair:

  determinism   compile twice -> byte-identical stdout and exit code, and
                --discovery-order reverse -> byte-identical (order independence)
  metamorphic   adding an unrelated module changes registryRevision but NEVER
                the image hash (the exact bug the golden tier once caught)
  provenance    every emitted unit carries module + source + version
  effects       every image's linked effects fit inside its effectCeiling
  fail-closed   injected faults (dependency cycle, missing dependency,
                conflict, unknown frontmatter key, duplicate id, over-ceiling
                capability, undeclared stance, no ceiling) each fail with the
                EXACT diagnostic code, never a warning, never a pass

Deterministic compiles are also asserted for organically FAILING queries: the
diagnostics themselves must be byte-stable and discovery-order independent.

Stdlib only, offline, isolated: everything happens in a fresh temp directory.
Exit 0 = every assertion held; non-zero = at least one violation (printed).
"""
import argparse
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.abspath(os.path.join(HERE, "..", ".."))
KERNEL = os.path.join(PLUGIN, "scripts", "compile.py")

EFFECTS = ["network", "filesystem:read", "filesystem:write",
           "scm:read", "scm:write", "process:spawn"]
# Capability effects draw from this core, and every generated view's ceiling
# includes all of it — so broad-ceiling queries exercise the success path,
# while narrow QUERY ceilings still produce organic EFFECT_CEILING failures
# (which are themselves determinism-checked).
CORE_EFFECTS = ["network", "scm:read", "filesystem:read"]
DOMAINS = [f"dom-{i}" for i in range(12)]
TASKS = [f"task-{i}" for i in range(6)]
ROLES = [f"role-{i}" for i in range(4)]
TRAITS = [f"trait-{i}" for i in range(8)]
ENVS = ["development", "staging", "production"]
RISKS = ["low", "medium", "high", "critical"]

FAILURES = []
COUNTS = {"compiles": 0, "success_queries": 0, "fail_queries": 0,
          "metamorphic": 0, "injections": 0}
SLOWEST = 0.0


def fail(msg):
    FAILURES.append(msg)
    print(f"  FAIL {msg}")


def write_module(reg, relname, fm, units=()):
    lines = ["---"]
    for k, v in fm.items():
        if isinstance(v, list):
            lines.append(f"{k}: [" + ", ".join(v) + "]")
        else:
            lines.append(f"{k}: {v}")
    lines.append("---")
    lines.append("")
    lines.append(f"# {fm['id']}")
    lines.append("")
    for i, kind in enumerate(units):
        attr = ' strength="must"' if kind == "rule" else ""
        lines.append(f'<{kind} id="u{i}"{attr}>')
        lines.append(f"Stress {kind} u{i} of module {fm['id']}.")
        lines.append(f"</{kind}>")
        lines.append("")
    path = os.path.join(reg, relname)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write("\n".join(lines))


def gen_registry(rng, n_modules, root):
    """Generate a valid registry of ~n_modules modules; return its manifest."""
    reg = os.path.join(root, "registry")
    os.makedirs(reg)
    n_caps = max(2, n_modules // 20)
    n_views = max(2, n_modules // 30)
    n_beh = max(4, n_modules - n_caps - n_views)

    caps = []
    for i in range(n_caps):
        cid = f"cap.stress-{i}"
        effects = rng.sample(CORE_EFFECTS, rng.randint(1, 2))
        write_module(reg, f"capabilities/c{i}.md",
                     {"id": cid, "kind": "capability_interface",
                      "version": "1.0.0", "effects": effects})
        caps.append((cid, effects))

    behs = []
    for i in range(n_beh):
        bid = f"beh.stress-{i}"
        fm = {"id": bid, "kind": "behavior", "version": "1.0.0"}
        if rng.random() < 0.7:
            fm["domains"] = rng.sample(DOMAINS, rng.randint(1, 2))
        if rng.random() < 0.3:
            fm["tasks"] = rng.sample(TASKS, 1)
        if rng.random() < 0.2:
            fm["roles"] = rng.sample(ROLES, 1)
        if i > 0 and rng.random() < 0.4:
            fm["requires"] = [f"beh.stress-{j}" for j in
                              rng.sample(range(i), min(i, rng.randint(1, 2)))]
        if rng.random() < 0.25:
            fm["capabilities"] = [rng.choice(caps)[0]]
        if rng.random() < 0.15:
            fm["environments"] = rng.sample(ENVS, rng.randint(1, 2))
        if rng.random() < 0.15:
            fm["risks"] = rng.sample(RISKS, rng.randint(1, 3))
        units = tuple(rng.choice(["rule", "probe", "antipattern"])
                      for _ in range(rng.randint(1, 3)))
        write_module(reg, f"behaviors/b{i}.md", fm, units)
        behs.append(bid)

    views = []
    for i in range(n_views):
        vid = f"view.stress-{i}"
        traits = rng.sample(TRAITS, rng.randint(2, 3))
        extras = [e for e in EFFECTS if e not in CORE_EFFECTS]
        max_effects = CORE_EFFECTS + rng.sample(extras, rng.randint(0, len(extras)))
        fm = {"id": vid, "kind": "view", "version": "1.0.0",
              "traits": traits, "max_effects": max_effects}
        if rng.random() < 0.6:
            fm["requires"] = rng.sample(behs, rng.randint(1, 2))
        write_module(reg, f"views/v{i}.md", fm)
        views.append((vid, traits, max_effects))
    return reg, views


def gen_query(rng, views, root, i):
    q = {"name": f"stress-agent-{i}", "domains": rng.sample(DOMAINS, rng.randint(1, 3)),
         "environment": rng.choice(ENVS), "risk": rng.choice(RISKS)}
    if rng.random() < 0.8:
        q["task"] = rng.choice(TASKS)
    if rng.random() < 0.6:
        q["role"] = rng.choice(ROLES)
    chosen = rng.sample(views, rng.randint(1, min(2, len(views)))) \
        if rng.random() < 0.85 else []
    q["views"] = [v[0] for v in chosen]
    traits = sorted({t for v in chosen for t in v[1]})
    q["stance"] = rng.sample(traits, min(len(traits), rng.randint(0, 2))) if traits else []
    # Mostly broad ceilings (exercise success); sometimes narrow (organic
    # EFFECT_CEILING failures are a legitimate, determinism-checked outcome).
    q["effectCeiling"] = list(EFFECTS) if rng.random() < 0.75 \
        else rng.sample(EFFECTS, rng.randint(1, 3))
    path = os.path.join(root, f"query-{i}.json")
    with open(path, "w") as f:
        json.dump(q, f)
    return path, q


def compile_once(reg, query, extra=()):
    global SLOWEST
    t0 = time.monotonic()
    r = subprocess.run(
        [sys.executable, KERNEL, "compile", "--registry", reg,
         "--query", query, *extra],
        capture_output=True)
    SLOWEST = max(SLOWEST, time.monotonic() - t0)
    COUNTS["compiles"] += 1
    return r.returncode, r.stdout


def diag_codes(stdout):
    try:
        doc = json.loads(stdout.decode("utf-8", "replace"))
    except Exception:
        return []
    return [d.get("code") for d in doc.get("diagnostics", [])]


def inject(reg, root, name, writer):
    """Copy the registry, apply writer(copy), return the copy path."""
    copy = os.path.join(root, f"inj-{name}")
    shutil.copytree(reg, copy)
    writer(copy)
    return copy


def expect_code(tag, reg, query, code):
    COUNTS["injections"] += 1
    rc, out = compile_once(reg, query)
    if rc == 0:
        fail(f"{tag}: expected {code}, compile SUCCEEDED")
    elif code not in diag_codes(out):
        fail(f"{tag}: expected {code}, got {diag_codes(out)}")


def run_trial(rng, size, seed, root):
    reg, views = gen_registry(rng, size, root)
    first_success_done = False
    for qi in range(ARGS.queries):
        qpath, q = gen_query(rng, views, root, qi)
        tag = f"size={size} seed={seed} q={qi}"

        rc1, out1 = compile_once(reg, qpath)
        rc2, out2 = compile_once(reg, qpath)
        rc3, out3 = compile_once(reg, qpath, ("--discovery-order", "reverse"))
        if (rc1, out1) != (rc2, out2):
            fail(f"{tag}: NOT deterministic across identical runs")
        if (rc1, out1) != (rc3, out3):
            fail(f"{tag}: discovery order changed the output")

        if rc1 != 0:
            COUNTS["fail_queries"] += 1
            if not diag_codes(out1):
                fail(f"{tag}: failed with no structured diagnostics")
            continue
        COUNTS["success_queries"] += 1
        image = json.loads(out1)

        for u in image.get("behavior", []):
            prov = u.get("provenance") or {}
            if not (prov.get("module") and prov.get("source") and prov.get("version")):
                fail(f"{tag}: unit {u.get('id')} missing provenance")
                break
        ceiling = set(image.get("effectCeiling", []))
        linked = set(image.get("effects", []))
        if not linked <= ceiling:
            fail(f"{tag}: effects {sorted(linked - ceiling)} escape the ceiling")

        # Metamorphic: an unrelated module moves registryRevision, never hash.
        meta = inject(reg, root, f"meta-{qi}", lambda c: write_module(
            c, "behaviors/zz-unrelated.md",
            {"id": "beh.stress-unrelated", "kind": "behavior",
             "version": "1.0.0", "domains": ["zzz-unrelated-domain"]},
            ("rule",)))
        rcm, outm = compile_once(meta, qpath)
        COUNTS["metamorphic"] += 1
        if rcm != 0:
            fail(f"{tag}: metamorphic add-module broke the compile")
        else:
            im = json.loads(outm)
            if im.get("hash") != image.get("hash"):
                fail(f"{tag}: unrelated module CHANGED the image hash")
            if im.get("registryRevision") == image.get("registryRevision"):
                fail(f"{tag}: unrelated module was not seen (registryRevision unchanged)")
        shutil.rmtree(meta)

        # Fault injections: full set once per registry, 2 random per later success.
        dom = q["domains"][0]
        injections = {
            "cycle": (lambda c: (
                write_module(c, "behaviors/zz-cyc-a.md",
                             {"id": "beh.stress-cyc-a", "kind": "behavior", "version": "1.0.0",
                              "domains": [dom], "requires": ["beh.stress-cyc-b"]}, ("rule",)),
                write_module(c, "behaviors/zz-cyc-b.md",
                             {"id": "beh.stress-cyc-b", "kind": "behavior", "version": "1.0.0",
                              "requires": ["beh.stress-cyc-a"]}, ("rule",))),
                "DEPENDENCY_CYCLE"),
            "missing-dep": (lambda c: write_module(
                c, "behaviors/zz-missing.md",
                {"id": "beh.stress-missing", "kind": "behavior", "version": "1.0.0",
                 "domains": [dom], "requires": ["beh.stress-does-not-exist"]}, ("rule",)),
                "MISSING_DEPENDENCY"),
            "conflict": (lambda c: (
                write_module(c, "behaviors/zz-conf-a.md",
                             {"id": "beh.stress-conf-a", "kind": "behavior", "version": "1.0.0",
                              "domains": [dom], "conflicts_with": ["beh.stress-conf-b"]}, ("rule",)),
                write_module(c, "behaviors/zz-conf-b.md",
                             {"id": "beh.stress-conf-b", "kind": "behavior", "version": "1.0.0",
                              "domains": [dom]}, ("rule",))),
                "CONFLICT"),
            "bad-key": (lambda c: write_module(
                c, "behaviors/zz-typo.md",
                {"id": "beh.stress-typo", "kind": "behavior", "version": "1.0.0",
                 "task": [TASKS[0]]}, ("rule",)),
                "BAD_MODULE_KEY"),
            "dup-id": (lambda c: write_module(
                c, "behaviors/zz-dup.md",
                {"id": "beh.stress-0", "kind": "behavior", "version": "1.0.0"}, ("rule",)),
                "DUPLICATE_ID"),
            "over-ceiling": (lambda c: (
                write_module(c, "capabilities/zz-evil.md",
                             {"id": "cap.stress-evil", "kind": "capability_interface",
                              "version": "1.0.0", "effects": ["stress:forbidden"]}),
                write_module(c, "behaviors/zz-evil.md",
                             {"id": "beh.stress-evil", "kind": "behavior", "version": "1.0.0",
                              "domains": [dom], "capabilities": ["cap.stress-evil"]}, ("rule",))),
                "EFFECT_CEILING"),
        }
        chosen = list(injections.items()) if not first_success_done \
            else rng.sample(sorted(injections.items()), 2)
        for name, (writer, code) in chosen:
            copy = inject(reg, root, f"{name}-{qi}", writer)
            expect_code(f"{tag} inject={name}", copy, qpath, code)
            shutil.rmtree(copy)

        if not first_success_done:
            # Query-side faults, once per registry, against the intact registry.
            qbad = dict(q)
            qbad["stance"] = list(q.get("stance", [])) + ["stress-undeclared-trait"]
            bad1 = os.path.join(root, f"qbad-stance-{qi}.json")
            json.dump(qbad, open(bad1, "w"))
            expect_code(f"{tag} inject=undeclared-stance", reg, bad1, "UNDECLARED_STANCE")

            qno = {k: v for k, v in q.items() if k != "effectCeiling"}
            qno["views"], qno["stance"] = [], []
            bad2 = os.path.join(root, f"qbad-ceiling-{qi}.json")
            json.dump(qno, open(bad2, "w"))
            expect_code(f"{tag} inject=no-ceiling", reg, bad2, "NO_EFFECT_CEILING")
        first_success_done = True


def main():
    global ARGS
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sizes", default="40,120,300",
                    help="comma-separated registry sizes (modules)")
    ap.add_argument("--seeds", type=int, default=3, help="seeds per size")
    ap.add_argument("--queries", type=int, default=6, help="queries per registry")
    ap.add_argument("--report", default="", help="write a JSON report here")
    ARGS = ap.parse_args()
    sizes = [int(s) for s in ARGS.sizes.split(",") if s]

    t0 = time.monotonic()
    for size in sizes:
        for seed in range(ARGS.seeds):
            rng = random.Random(1000 * size + seed)
            root = tempfile.mkdtemp(prefix=f"ac-stress-{size}-{seed}-")
            try:
                run_trial(rng, size, seed, root)
            finally:
                shutil.rmtree(root, ignore_errors=True)
            print(f"  ok   size={size} seed={seed}")

    total_q = COUNTS["success_queries"] + COUNTS["fail_queries"]
    if total_q and COUNTS["success_queries"] < max(1, total_q // 4):
        fail(f"only {COUNTS['success_queries']}/{total_q} queries compiled — "
             "the generator no longer exercises the success path")

    elapsed = time.monotonic() - t0
    summary = {**COUNTS, "sizes": sizes, "seeds": ARGS.seeds,
               "elapsed_s": round(elapsed, 2),
               "slowest_compile_s": round(SLOWEST, 3),
               "violations": FAILURES}
    print(f"\nagent-compiler scale: {COUNTS['compiles']} kernel invocations, "
          f"{COUNTS['success_queries']} successful queries, "
          f"{COUNTS['fail_queries']} organic failures (all determinism-checked), "
          f"{COUNTS['metamorphic']} metamorphic checks, "
          f"{COUNTS['injections']} fault injections, "
          f"{len(FAILURES)} violations, {elapsed:.1f}s "
          f"(slowest compile {SLOWEST:.2f}s)")
    if ARGS.report:
        json.dump(summary, open(ARGS.report, "w"), indent=2)
        print(f"report: {ARGS.report}")
    sys.exit(1 if FAILURES else 0)


if __name__ == "__main__":
    main()
