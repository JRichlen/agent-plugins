#!/usr/bin/env python3
"""agent-compiler kernel: deterministic AgentQuery -> AgentImage compilation.

Everything on this side of the deterministic boundary lives here. Python 3
stdlib only — the same toolchain the marketplace cheap tier already requires —
so the kernel runs offline, with no package manager, on any harness.

Subcommands:
  compile --registry DIR --query FILE [--out FILE] [--discovery-order reverse]
  inspect --registry DIR [--id ID] [--kind KIND] [--tag TAG]
  explain --image FILE --unit UNIT_ID

Exit codes: 0 success; 1 compile error (structured diagnostics on stdout as
JSON); 2 usage/input error.

The invariant this file defends (see the plugin AGENTS.md): identical
(registry, query, compiler version) inputs produce byte-identical canonical
output and an identical hash; every emitted unit carries provenance; unresolved
conflicts, missing dependencies, dependency cycles, and effects above the
query's ceiling FAIL compilation — they are never downgraded to warnings.
"""

import argparse
import hashlib
import json
import os
import re
import sys

COMPILER_VERSION = "0.1.0"
SCHEMA_VERSION = "0.1"

MODULE_KINDS = {"behavior", "view", "capability_interface"}
BLOCK_KINDS = ("rule", "probe", "example", "antipattern")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
BLOCK_RE = re.compile(
    r"<(" + "|".join(BLOCK_KINDS) + r")\b([^>]*)>(.*?)</\1>", re.DOTALL
)
ATTR_RE = re.compile(r'([a-zA-Z_][a-zA-Z0-9_-]*)="([^"]*)"')

LIST_KEYS = {
    "roles", "tasks", "domains", "requires", "conflicts_with",
    "supersedes", "capabilities", "effects", "max_effects", "traits",
    "environments", "risks",
}
# Unknown frontmatter keys fail closed (BAD_MODULE_KEY). Without this, a
# typo'd key ('task:' for 'tasks:') compiled cleanly and silently deselected
# the module — found by running the first demonstration, now a diagnostic.
KNOWN_KEYS = LIST_KEYS | {"id", "kind", "version"}


class CompileError(Exception):
    """Carries structured diagnostics; raised only for error-severity ones."""

    def __init__(self, diagnostics):
        self.diagnostics = diagnostics
        super().__init__(json.dumps(diagnostics))


def diag(code, message, node_ids=None):
    d = {"code": code, "severity": "error", "message": message}
    if node_ids:
        d["nodeIds"] = sorted(node_ids)
    return d


# --- frontmatter (restricted subset, parsed deterministically) ---------------
# Full YAML would drag in a dependency the cheap tier treats as optional. The
# module format therefore restricts frontmatter to: `key: scalar`,
# `key: [a, b]` inline lists, and one-level dash lists. Documented in
# references/language.md; anything else is a parse error, not a guess.

def _scalar(raw):
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
        return raw[1:-1]
    return raw


def parse_frontmatter(text, source):
    if not text.startswith("---"):
        raise CompileError([diag("BAD_MODULE", f"{source}: no frontmatter")])
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise CompileError([diag("BAD_MODULE", f"{source}: unterminated frontmatter")])
    meta, body = {}, parts[2]
    body_offset = text[: len(parts[0]) + len(parts[1]) + 6].count("\n")
    current_list_key = None
    for lineno, line in enumerate(parts[1].splitlines(), start=2):
        if not line.strip() or line.strip().startswith("#"):
            continue
        m = re.match(r"^\s*-\s+(.*)$", line)
        if m:
            if current_list_key is None:
                raise CompileError([diag(
                    "BAD_MODULE", f"{source}:{lineno}: dash item outside a list key")])
            meta[current_list_key].append(_scalar(m.group(1)))
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", line)
        if not m:
            raise CompileError([diag(
                "BAD_MODULE",
                f"{source}:{lineno}: unsupported frontmatter syntax: {line.strip()!r}")])
        key, raw = m.group(1), m.group(2).strip()
        if key not in KNOWN_KEYS:
            raise CompileError([diag(
                "BAD_MODULE_KEY",
                f"{source}:{lineno}: unknown frontmatter key '{key}' "
                f"(known: {', '.join(sorted(KNOWN_KEYS))})")])
        current_list_key = None
        if raw == "":
            if key in LIST_KEYS:
                meta[key] = []
                current_list_key = key
            else:
                meta[key] = ""
        elif raw.startswith("[") and raw.endswith("]"):
            inner = raw[1:-1].strip()
            meta[key] = [_scalar(x) for x in inner.split(",")] if inner else []
        else:
            meta[key] = _scalar(raw)
    for key in LIST_KEYS:
        if key in meta and not isinstance(meta[key], list):
            raise CompileError([diag(
                "BAD_MODULE", f"{source}: '{key}' must be a list")])
    return meta, body, body_offset


def parse_blocks(body, body_offset, module_id, source, diagnostics):
    units, seen = [], set()
    for m in BLOCK_RE.finditer(body):
        kind, rawattrs, content = m.group(1), m.group(2), m.group(3)
        attrs = dict(ATTR_RE.findall(rawattrs))
        bid = attrs.get("id", "")
        start = body_offset + body[: m.start()].count("\n") + 1
        end = body_offset + body[: m.end()].count("\n") + 1
        if not bid or not ID_RE.match(bid):
            diagnostics.append(diag(
                "BAD_UNIT_ID",
                f"{source}:{start}: <{kind}> block needs a valid id attribute"))
            continue
        if bid in seen:
            diagnostics.append(diag(
                "DUPLICATE_UNIT_ID", f"{source}: duplicate block id '{bid}'"))
            continue
        seen.add(bid)
        unit = {
            "id": f"{module_id}#{bid}",
            "kind": kind,
            "content": " ".join(content.split()),
        }
        if kind == "rule":
            unit["strength"] = attrs.get("strength", "should")
        unit["_lines"] = [start, end]
        units.append(unit)
    return units


# --- registry ----------------------------------------------------------------

def load_registry(registry_dir, discovery_order="sorted"):
    """Load every .md module. Discovery order is canonicalized internally, so
    `discovery_order="reverse"` exists purely to PROVE order-independence in
    evals — same inputs must yield byte-identical output either way."""
    if not os.path.isdir(registry_dir):
        raise CompileError([diag("BAD_REGISTRY", f"not a directory: {registry_dir}")])
    files = []
    for base, dirs, names in os.walk(registry_dir):
        dirs.sort()
        for n in sorted(names):
            if n.endswith(".md"):
                files.append(os.path.join(base, n))
    if discovery_order == "reverse":
        files = list(reversed(files))
    diagnostics, modules = [], {}
    rev_parts = []
    for path in files:
        rel = os.path.relpath(path, registry_dir).replace(os.sep, "/")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        rev_parts.append((rel, hashlib.sha256(text.encode()).hexdigest()))
        meta, body, body_offset = parse_frontmatter(text, rel)
        mid, kind, version = meta.get("id", ""), meta.get("kind", ""), meta.get("version", "")
        if not mid or not ID_RE.match(mid):
            diagnostics.append(diag("BAD_MODULE_ID", f"{rel}: missing or invalid 'id'"))
            continue
        if kind not in MODULE_KINDS:
            diagnostics.append(diag(
                "BAD_MODULE_KIND", f"{rel}: 'kind' must be one of {sorted(MODULE_KINDS)}"))
            continue
        if not version:
            diagnostics.append(diag("BAD_MODULE_VERSION", f"{rel}: missing 'version'"))
            continue
        if mid in modules:
            diagnostics.append(diag(
                "DUPLICATE_ID",
                f"{rel}: id '{mid}' already defined in {modules[mid]['source']}",
                [mid]))
            continue
        units = parse_blocks(body, body_offset, mid, rel, diagnostics) \
            if kind == "behavior" else []
        modules[mid] = {"id": mid, "kind": kind, "version": version,
                        "meta": meta, "source": rel, "units": units}
    if diagnostics:
        raise CompileError(diagnostics)
    # Revision is content-addressed over sorted (path, hash) pairs — stable
    # across discovery order by construction.
    rev = hashlib.sha256(json.dumps(sorted(rev_parts)).encode()).hexdigest()
    return modules, f"sha256:{rev}"


# --- resolution --------------------------------------------------------------

def applicable(meta, query):
    """Applicability conditions (handoff pipeline stage 8): a module that
    declares `environments`/`risks` matches only when the query's value is in
    the list. Gates SELECTOR-based inclusion only — an explicit `requires`
    edge or a view named in query.views is an exact ask and ignores it."""
    envs = meta.get("environments")
    if envs and query.get("environment", "") not in envs:
        return False
    risks = meta.get("risks")
    if risks and query.get("risk", "") not in risks:
        return False
    return True


def resolve_selection(query, modules):
    """Exact, documented selection: views come only from query.views; a
    behavior module is selected when its tasks contain query.task, its roles
    contain query.role, or its domains intersect query.domains — and its
    applicability conditions (environments/risks) accept the query."""
    diagnostics, selected = [], set()
    for vid in query.get("views", []):
        v = modules.get(vid)
        if v is None or v["kind"] != "view":
            diagnostics.append(diag("MISSING_VIEW", f"query names unknown view '{vid}'", [vid]))
        else:
            selected.add(vid)
    task, role = query.get("task", ""), query.get("role", "")
    domains = set(query.get("domains", []))
    for mid, mod in modules.items():
        if mod["kind"] != "behavior":
            continue
        meta = mod["meta"]
        if not applicable(meta, query):
            continue
        if task and task in meta.get("tasks", []):
            selected.add(mid)
        elif role and role in meta.get("roles", []):
            selected.add(mid)
        elif domains & set(meta.get("domains", [])):
            selected.add(mid)
    if diagnostics:
        raise CompileError(diagnostics)
    return selected


def validate_stance(query, selected, modules):
    """Every stance entry must be a trait some selected view declares —
    otherwise the stance would render as if it meant something while
    selecting nothing (fail closed, per the house style)."""
    stance = query.get("stance", [])
    if not stance:
        return
    declared = set()
    for mid in selected:
        if modules[mid]["kind"] == "view":
            declared.update(modules[mid]["meta"].get("traits", []))
    missing = sorted(set(stance) - declared)
    if missing:
        raise CompileError([diag(
            "UNDECLARED_STANCE",
            f"stance {missing} is declared by no selected view "
            f"(declared traits: {sorted(declared)}); add the trait to a view "
            "or drop it from the query", missing)])


def expand_dependencies(selected, modules):
    diagnostics = []
    order, visiting, done = [], [], set()

    def visit(mid, needed_by):
        if mid in done:
            return
        if mid in visiting:
            cycle = visiting[visiting.index(mid):] + [mid]
            diagnostics.append(diag(
                "DEPENDENCY_CYCLE", "requires cycle: " + " -> ".join(cycle), cycle))
            return
        mod = modules.get(mid)
        if mod is None:
            diagnostics.append(diag(
                "MISSING_DEPENDENCY",
                f"'{needed_by}' requires '{mid}' which is not in the registry",
                [mid, needed_by]))
            return
        visiting.append(mid)
        for dep in mod["meta"].get("requires", []):
            visit(dep, mid)
        visiting.pop()
        done.add(mid)
        order.append(mid)

    for mid in sorted(selected):
        visit(mid, "query")
    if diagnostics:
        raise CompileError(diagnostics)
    return set(order)


def detect_conflicts(selected, modules):
    """A conflicts_with edge between two selected modules is fatal unless one
    supersedes the other, in which case the superseded module is dropped.
    Unknown conflicts fail compilation — never silently resolved."""
    diagnostics, dropped = [], set()
    sel = sorted(selected)
    for mid in sel:
        for other in modules[mid]["meta"].get("supersedes", []):
            if other in selected:
                dropped.add(other)
    for mid in sel:
        for other in modules[mid]["meta"].get("conflicts_with", []):
            if other not in selected or mid in dropped or other in dropped:
                continue
            a_sup = other in modules[mid]["meta"].get("supersedes", [])
            b_sup = mid in modules.get(other, {}).get("meta", {}).get("supersedes", [])
            if not a_sup and not b_sup:
                diagnostics.append(diag(
                    "CONFLICT",
                    f"'{mid}' conflicts with '{other}' and no supersedes edge resolves it",
                    [mid, other]))
    if diagnostics:
        raise CompileError(diagnostics)
    return selected - dropped


def link_and_validate_effects(query, selected, modules):
    """Effect ceiling = query.effectCeiling intersected with every selected
    view's max_effects. A compile with NO ceiling from either source fails
    closed (NO_EFFECT_CEILING) — an unconstrained agent must be asked for
    explicitly by listing its effects, never implied by omission."""
    diagnostics = []
    ceilings = []
    if query.get("effectCeiling"):
        ceilings.append(set(query["effectCeiling"]))
    for mid in sorted(selected):
        if modules[mid]["kind"] == "view" and modules[mid]["meta"].get("max_effects"):
            ceilings.append(set(modules[mid]["meta"]["max_effects"]))
    if not ceilings:
        raise CompileError([diag(
            "NO_EFFECT_CEILING",
            "neither the query nor any selected view declares an effect ceiling; "
            "declare effectCeiling in the query or max_effects in a view")])
    ceiling = set.intersection(*ceilings)
    capabilities, effects = set(), set()
    for mid in sorted(selected):
        for cap in modules[mid]["meta"].get("capabilities", []):
            iface = modules.get(cap)
            if iface is None or iface["kind"] != "capability_interface":
                diagnostics.append(diag(
                    "MISSING_CAPABILITY",
                    f"'{mid}' requires capability interface '{cap}' which is not in the registry",
                    [cap, mid]))
                continue
            capabilities.add(cap)
            for eff in iface["meta"].get("effects", []):
                effects.add(eff)
                if eff not in ceiling:
                    diagnostics.append(diag(
                        "EFFECT_CEILING",
                        f"capability '{cap}' (required by '{mid}') needs effect "
                        f"'{eff}' above the ceiling {sorted(ceiling)}",
                        [cap, mid]))
    if diagnostics:
        raise CompileError(diagnostics)
    return sorted(capabilities), sorted(effects), sorted(ceiling)


# --- canonical render --------------------------------------------------------

def canonical_query(query):
    out = {}
    for k in ("name", "role", "task", "environment", "risk"):
        if query.get(k):
            out[k] = query[k]
    for k in ("domains", "views", "stance", "effectCeiling"):
        if query.get(k):
            out[k] = sorted(query[k])
    if query.get("facts"):
        out["facts"] = query["facts"]
    return out


def canonical_json(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def compile_image(registry_dir, query, discovery_order="sorted"):
    modules, revision = load_registry(registry_dir, discovery_order)
    selected = resolve_selection(query, modules)
    selected = expand_dependencies(selected, modules)
    selected = detect_conflicts(selected, modules)
    validate_stance(query, selected, modules)
    capabilities, effects, ceiling = link_and_validate_effects(query, selected, modules)

    behavior = []
    for mid in sorted(selected):
        mod = modules[mid]
        if mod["kind"] != "behavior":
            continue
        for u in mod["units"]:
            unit = {k: v for k, v in u.items() if k != "_lines"}
            unit["provenance"] = {
                "module": mid,
                "version": mod["version"],
                "source": mod["source"],
                "lines": u["_lines"],
            }
            behavior.append(unit)
    behavior.sort(key=lambda u: u["id"])
    views = sorted(m for m in selected if modules[m]["kind"] == "view")

    image = {
        "schemaVersion": SCHEMA_VERSION,
        "compilerVersion": COMPILER_VERSION,
        "query": canonical_query(query),
        "behavior": behavior,
        "views": views,
        "capabilities": capabilities,
        "effects": effects,
        "effectCeiling": ceiling,
        "diagnostics": [],
    }
    # The hash covers the CONTENT-BEARING fields above — what the agent is —
    # per the handoff's content-addressing model (hash of selected modules +
    # query + compiler version). registryRevision is build metadata recorded
    # OUTSIDE the hash: hashing the whole-registry revision would let an
    # unrelated module change an existing image's identity, breaking the
    # metamorphic invariance the evals pin. (Found by running the kernel, not
    # by reviewing it.)
    digest = hashlib.sha256(canonical_json(image).encode()).hexdigest()
    image["hash"] = f"sha256:{digest}"
    image["registryRevision"] = revision
    return image


# --- CLI ---------------------------------------------------------------------

def cmd_compile(args):
    with open(args.query, encoding="utf-8") as f:
        query = json.load(f)
    image = compile_image(args.registry, query, args.discovery_order)
    rendered = canonical_json(image) + "\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(rendered)
    sys.stdout.write(rendered if not args.out else image["hash"] + "\n")
    return 0


def cmd_inspect(args):
    modules, revision = load_registry(args.registry)
    rows = []
    for mid in sorted(modules):
        mod = modules[mid]
        tags = sorted(set(mod["meta"].get("tasks", []))
                      | set(mod["meta"].get("domains", []))
                      | set(mod["meta"].get("roles", [])))
        if args.id and mid != args.id:
            continue
        if args.kind and mod["kind"] != args.kind:
            continue
        if args.tag and args.tag not in tags:
            continue
        rows.append({
            "id": mid, "kind": mod["kind"], "version": mod["version"],
            "source": mod["source"], "tags": tags,
            "requires": sorted(mod["meta"].get("requires", [])),
            "capabilities": sorted(mod["meta"].get("capabilities", [])),
            "effects": sorted(mod["meta"].get("effects", [])),
            "units": [u["id"] for u in mod["units"]],
        })
    sys.stdout.write(canonical_json(
        {"registryRevision": revision, "modules": rows}) + "\n")
    return 0


def cmd_explain(args):
    with open(args.image, encoding="utf-8") as f:
        image = json.load(f)
    for unit in image.get("behavior", []):
        if unit["id"] == args.unit:
            sys.stdout.write(canonical_json(unit) + "\n")
            return 0
    sys.stderr.write(f"unit '{args.unit}' not in image {image.get('hash', '?')}\n")
    return 2


def main(argv=None):
    parser = argparse.ArgumentParser(prog="compile.py", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("compile")
    c.add_argument("--registry", required=True)
    c.add_argument("--query", required=True)
    c.add_argument("--out")
    c.add_argument("--discovery-order", choices=("sorted", "reverse"),
                   default="sorted")
    c.set_defaults(fn=cmd_compile)

    i = sub.add_parser("inspect")
    i.add_argument("--registry", required=True)
    i.add_argument("--id")
    i.add_argument("--kind")
    i.add_argument("--tag")
    i.set_defaults(fn=cmd_inspect)

    e = sub.add_parser("explain")
    e.add_argument("--image", required=True)
    e.add_argument("--unit", required=True)
    e.set_defaults(fn=cmd_explain)

    args = parser.parse_args(argv)
    try:
        return args.fn(args)
    except CompileError as err:
        sys.stdout.write(canonical_json({"diagnostics": err.diagnostics}) + "\n")
        return 1
    except (OSError, json.JSONDecodeError) as err:
        sys.stderr.write(f"compile.py: {err}\n")
        return 2


if __name__ == "__main__":
    sys.exit(main())
