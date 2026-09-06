"""evals.agentic.framework.registry -- plugin roster + suite catalog (registry
lane, contract §3.9, §7).

``derive_roster`` parses the LIVE ``.claude-plugin/marketplace.json`` and
resolves every ``source`` to a real directory carrying a name-matching
``.claude-plugin/plugin.json``. There is no hardcoded plugin list anywhere in
this module -- a 26th marketplace entry changes the roster on the next call,
with no code edit (T11).

``load_catalog``/``resolve_test``/``run_entry`` implement the suite-catalog
merge and fail-closed execution described in contract §7. Deviation reported
explicitly (per the task brief): ``Catalog.duplicate_ids()`` is specified on a
type (``Mapping[str, CatalogEntry]``) that cannot structurally hold a literal
duplicate key -- ``load_catalog`` already raises ``CatalogUnresolvable`` the
moment two fragments claim the same ID, before any ``Catalog`` is built. The
closest faithful reading that keeps the method non-vacuous is a structural
self-consistency check: IDs whose entry disagrees with the dict key it is
filed under. It is always empty for any ``Catalog`` this module constructs;
it exists so a caller who received a ``Catalog`` by some other path (a future
lane's test harness) still has a real assertion to make.
"""
from __future__ import annotations

import dataclasses
import importlib
import pathlib
import types
import unittest
from collections.abc import Mapping, Sequence
from typing import Any

from . import io
from .contract import (
    ALL_IDS,
    ApprovalGate,
    CatalogUnresolvable,
    ContractError,
    EvidenceClass,
)
from .contract import digest as contract_digest

__all__ = [
    "PluginRef",
    "derive_roster",
    "CatalogEntry",
    "Catalog",
    "CATALOG_DIR",
    "load_catalog",
    "resolve_test",
    "run_entry",
    "EntryRun",
]

CATALOG_DIR: str = "evals/agentic/manifests/catalog"

_CATALOG_ENTRY_FIELDS = (
    "id", "lane", "module", "test_class", "test_name", "evidence_class",
    "approval_gate", "negative_control", "requires_real_marketplace",
    "reentrant_unsafe",
)


# ---------------------------------------------------------------------------
# PluginRef / derive_roster (T11)
# ---------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True, slots=True)
class PluginRef:
    name: str
    source: str
    directory: str
    version: str
    has_hooks: bool
    has_mcp: bool
    has_scripts: bool
    skills: tuple[str, ...]
    commands: tuple[str, ...]


def _load_plugin_manifest(plugin_dir: pathlib.Path) -> Mapping[str, Any]:
    manifest_path = plugin_dir / ".claude-plugin" / "plugin.json"
    if not manifest_path.is_file():
        raise ContractError(f"derive_roster: {manifest_path} does not exist")
    doc = io.load_json(manifest_path)
    if not isinstance(doc, Mapping):
        raise ContractError(f"derive_roster: {manifest_path} is not a JSON object")
    return doc


def _discover_skills(plugin_dir: pathlib.Path, skills_field: Any) -> tuple[str, ...]:
    field = skills_field if isinstance(skills_field, str) and skills_field else "./skills/"
    skills_dir = plugin_dir / field
    if not skills_dir.is_dir():
        return ()
    names = [
        child.name
        for child in skills_dir.iterdir()
        if child.is_dir() and (child / "SKILL.md").is_file()
    ]
    return tuple(sorted(names))


def _discover_commands(plugin_dir: pathlib.Path, commands_field: Any) -> tuple[str, ...]:
    field = commands_field if isinstance(commands_field, str) and commands_field else "./commands/"
    commands_dir = plugin_dir / field
    if not commands_dir.is_dir():
        return ()
    names = [
        child.stem
        for child in commands_dir.iterdir()
        if child.is_file() and child.suffix == ".md"
    ]
    return tuple(sorted(names))


def _has_hooks(plugin_dir: pathlib.Path, manifest: Mapping[str, Any]) -> bool:
    hooks_field = manifest.get("hooks")
    if isinstance(hooks_field, str) and hooks_field:
        candidate = plugin_dir / hooks_field
        if candidate.is_dir():
            return (candidate / "hooks.json").is_file()
        return candidate.is_file()
    return (plugin_dir / "hooks" / "hooks.json").is_file()


def _has_mcp(plugin_dir: pathlib.Path, manifest: Mapping[str, Any]) -> bool:
    servers = manifest.get("mcpServers")
    if isinstance(servers, Mapping) and len(servers) > 0:
        return True
    mcp_field = manifest.get("mcp")
    if isinstance(mcp_field, str) and mcp_field:
        return (plugin_dir / mcp_field).is_file()
    return False


def _has_scripts(plugin_dir: pathlib.Path) -> bool:
    for candidate in plugin_dir.rglob("scripts"):
        if not candidate.is_dir():
            continue
        rel_parts = candidate.relative_to(plugin_dir).parts
        if "evals" in rel_parts:
            # A "scripts" directory nested under a plugin's OWN evals/ tree is
            # test-fixture furniture (see plugins/docs-hygiene/evals/cheap/
            # fixtures/repo-tree/**), not a surface the plugin ships to a user.
            continue
        return True
    return False


def derive_roster(repo_root: pathlib.Path) -> tuple[PluginRef, ...]:
    repo_root = pathlib.Path(repo_root).resolve()
    marketplace_path = repo_root / ".claude-plugin" / "marketplace.json"
    if not marketplace_path.is_file():
        raise ContractError(f"derive_roster: {marketplace_path} does not exist")
    marketplace = io.load_json(marketplace_path)
    entries = marketplace.get("plugins") if isinstance(marketplace, Mapping) else None
    if not isinstance(entries, list) or not entries:
        raise ContractError("derive_roster: marketplace.json has no non-empty 'plugins' list")

    refs: list[PluginRef] = []
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise ContractError(f"derive_roster: plugin entry is not an object: {entry!r}")
        name = entry.get("name")
        source = entry.get("source")
        if not isinstance(name, str) or not name:
            raise ContractError(f"derive_roster: plugin entry missing 'name': {entry!r}")
        if not isinstance(source, str) or not source:
            raise ContractError(f"derive_roster: plugin {name!r} missing 'source'")
        if name in seen:
            raise ContractError(f"derive_roster: duplicate plugin name {name!r} in marketplace.json")
        seen.add(name)

        plugin_dir = (repo_root / source).resolve()
        if not plugin_dir.is_dir():
            raise ContractError(
                f"derive_roster: plugin {name!r} source {source!r} does not resolve to a directory"
            )
        manifest = _load_plugin_manifest(plugin_dir)
        manifest_name = manifest.get("name")
        if manifest_name != name:
            raise ContractError(
                f"derive_roster: marketplace name {name!r} != plugin.json name {manifest_name!r} "
                f"at {plugin_dir}"
            )
        version = manifest.get("version")
        if not isinstance(version, str) or not version:
            raise ContractError(f"derive_roster: {name!r} plugin.json is missing 'version'")

        refs.append(
            PluginRef(
                name=name,
                source=source,
                directory=str(plugin_dir.relative_to(repo_root)),
                version=version,
                has_hooks=_has_hooks(plugin_dir, manifest),
                has_mcp=_has_mcp(plugin_dir, manifest),
                has_scripts=_has_scripts(plugin_dir),
                skills=_discover_skills(plugin_dir, manifest.get("skills")),
                commands=_discover_commands(plugin_dir, manifest.get("commands")),
            )
        )

    return tuple(sorted(refs, key=lambda r: r.name))


# ---------------------------------------------------------------------------
# CatalogEntry / Catalog / load_catalog (T52 / §7)
# ---------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True, slots=True)
class CatalogEntry:
    id: str
    lane: str
    module: str
    test_class: str
    test_name: str
    evidence_class: EvidenceClass
    approval_gate: ApprovalGate
    negative_control: str
    requires_real_marketplace: bool
    reentrant_unsafe: bool


def _catalog_entry_from_dict(d: Mapping[str, Any]) -> CatalogEntry:
    if not isinstance(d, Mapping):
        raise CatalogUnresolvable(f"CatalogEntry: expected an object, got {type(d)!r}")
    missing = [k for k in _CATALOG_ENTRY_FIELDS if k not in d]
    if missing:
        raise CatalogUnresolvable(f"CatalogEntry: missing key(s) {missing!r} in {d!r}")
    extra = sorted(set(d) - set(_CATALOG_ENTRY_FIELDS))
    if extra:
        raise CatalogUnresolvable(f"CatalogEntry: unknown key(s) {extra!r} in {d!r}")
    try:
        evidence_class = EvidenceClass(d["evidence_class"])
    except ValueError as exc:
        raise CatalogUnresolvable(f"CatalogEntry {d.get('id')!r}: bad evidence_class {d['evidence_class']!r}") from exc
    try:
        approval_gate = ApprovalGate(d["approval_gate"])
    except ValueError as exc:
        raise CatalogUnresolvable(f"CatalogEntry {d.get('id')!r}: bad approval_gate {d['approval_gate']!r}") from exc
    return CatalogEntry(
        id=d["id"],
        lane=d["lane"],
        module=d["module"],
        test_class=d["test_class"],
        test_name=d["test_name"],
        evidence_class=evidence_class,
        approval_gate=approval_gate,
        negative_control=d["negative_control"],
        requires_real_marketplace=bool(d["requires_real_marketplace"]),
        reentrant_unsafe=bool(d["reentrant_unsafe"]),
    )


def _catalog_entry_to_wire(entry: CatalogEntry) -> dict[str, Any]:
    return {
        "id": entry.id,
        "lane": entry.lane,
        "module": entry.module,
        "test_class": entry.test_class,
        "test_name": entry.test_name,
        "evidence_class": entry.evidence_class.value,
        "approval_gate": entry.approval_gate.value,
        "negative_control": entry.negative_control,
        "requires_real_marketplace": entry.requires_real_marketplace,
        "reentrant_unsafe": entry.reentrant_unsafe,
    }


@dataclasses.dataclass(frozen=True, slots=True)
class Catalog:
    entries: Mapping[str, CatalogEntry]
    digest: str

    def missing_ids(self) -> tuple[str, ...]:
        return tuple(i for i in ALL_IDS if i not in self.entries)

    def duplicate_ids(self) -> tuple[str, ...]:
        # See the module docstring: entries is a Mapping[str, CatalogEntry], a
        # type that cannot represent a literal duplicate key. load_catalog
        # already raises CatalogUnresolvable before a Catalog with a repeated
        # ID could ever be built. This is the structural-consistency reading:
        # any id whose stored entry disagrees with the key it is filed under.
        return tuple(i for i, e in self.entries.items() if e.id != i)

    def by_lane(self, lane: str) -> tuple[CatalogEntry, ...]:
        return tuple(e for e in self.entries.values() if e.lane == lane)

    def gated(self) -> tuple[CatalogEntry, ...]:
        return tuple(e for e in self.entries.values() if e.approval_gate is not ApprovalGate.NONE)


def load_catalog(repo_root: pathlib.Path) -> Catalog:
    repo_root = pathlib.Path(repo_root)
    catalog_dir = repo_root / CATALOG_DIR
    index_path = catalog_dir / "index.json"
    if not index_path.is_file():
        raise CatalogUnresolvable(f"load_catalog: {index_path} does not exist")
    index_doc = io.load_json(index_path)
    ids_by_lane = index_doc.get("ids") if isinstance(index_doc, Mapping) else None
    if not isinstance(ids_by_lane, Mapping) or not ids_by_lane:
        raise CatalogUnresolvable(f"load_catalog: {index_path} has no non-empty 'ids' mapping")

    allocated_lane_of: dict[str, str] = {}
    for lane, ids in ids_by_lane.items():
        if not isinstance(ids, list):
            raise CatalogUnresolvable(f"load_catalog: index.json ids[{lane!r}] is not a list")
        for entry_id in ids:
            if entry_id in allocated_lane_of:
                raise CatalogUnresolvable(
                    f"load_catalog: {entry_id} allocated to more than one lane in index.json"
                )
            allocated_lane_of[entry_id] = lane

    entries: dict[str, CatalogEntry] = {}
    for lane in sorted(ids_by_lane):
        fragment_path = catalog_dir / f"{lane}.json"
        if not fragment_path.is_file():
            raise CatalogUnresolvable(f"load_catalog: fragment missing for lane {lane!r}: {fragment_path}")
        fragment = io.load_json(fragment_path)
        if not isinstance(fragment, Mapping) or fragment.get("lane") != lane:
            raise CatalogUnresolvable(
                f"load_catalog: {fragment_path} does not declare lane {lane!r}"
            )
        raw_entries = fragment.get("entries")
        if not isinstance(raw_entries, list):
            raise CatalogUnresolvable(f"load_catalog: {fragment_path} has no 'entries' list")
        for raw_entry in raw_entries:
            entry = _catalog_entry_from_dict(raw_entry)
            if entry.lane != lane:
                raise CatalogUnresolvable(
                    f"load_catalog: entry {entry.id} in {fragment_path} declares lane "
                    f"{entry.lane!r}, file is lane {lane!r}"
                )
            expected_lane = allocated_lane_of.get(entry.id)
            if expected_lane is None:
                raise CatalogUnresolvable(
                    f"load_catalog: {entry.id} is not allocated to any lane in index.json"
                )
            if expected_lane != lane:
                raise CatalogUnresolvable(
                    f"load_catalog: {entry.id} not allocated to lane {lane!r} "
                    f"(index.json allocates it to {expected_lane!r})"
                )
            if entry.id in entries:
                raise CatalogUnresolvable(
                    f"load_catalog: duplicate id {entry.id} (already loaded from lane "
                    f"{entries[entry.id].lane!r})"
                )
            entries[entry.id] = entry

    missing = [i for i in ALL_IDS if i not in entries]
    if missing:
        raise CatalogUnresolvable(f"load_catalog: missing id(s) {missing!r}")
    extra_ids = sorted(i for i in entries if i not in ALL_IDS)
    if extra_ids:
        raise CatalogUnresolvable(f"load_catalog: id(s) not in contract.ALL_IDS: {extra_ids!r}")

    merged_sorted = [_catalog_entry_to_wire(entries[i]) for i in sorted(entries)]
    cat_digest = contract_digest({"index": index_doc, "entries": merged_sorted})
    return Catalog(entries=types.MappingProxyType(entries), digest=cat_digest)


# ---------------------------------------------------------------------------
# resolve_test / run_entry (§7.4)
# ---------------------------------------------------------------------------

def resolve_test(entry: CatalogEntry) -> tuple[type[unittest.TestCase], str]:
    try:
        module = importlib.import_module(entry.module)
    except Exception as exc:  # noqa: BLE001 -- any import failure is a resolution failure
        raise CatalogUnresolvable(f"{entry.id}: import failed: {exc}") from exc
    cls = getattr(module, entry.test_class, None)
    if not (isinstance(cls, type) and issubclass(cls, unittest.TestCase)):
        raise CatalogUnresolvable(
            f"{entry.id}: {entry.module}.{entry.test_class} is not a unittest.TestCase class"
        )
    if getattr(cls, "__unittest_skip__", False):
        raise CatalogUnresolvable(f"{entry.id}: {entry.test_class} is marked @unittest.skip")
    method = getattr(cls, entry.test_name, None)
    if method is None or not callable(method):
        raise CatalogUnresolvable(
            f"{entry.id}: {entry.test_class}.{entry.test_name} does not exist"
        )
    if getattr(method, "__unittest_skip__", False):
        raise CatalogUnresolvable(f"{entry.id}: {entry.test_class}.{entry.test_name} is marked skip")
    if getattr(method, "__unittest_expecting_failure__", False):
        raise CatalogUnresolvable(
            f"{entry.id}: {entry.test_class}.{entry.test_name} is marked @unittest.expectedFailure"
        )
    return cls, entry.test_name


@dataclasses.dataclass(frozen=True, slots=True)
class EntryRun:
    entry: CatalogEntry
    executed: bool
    assertions: int
    outcome: str
    detail: str


def _count_assertions(cls: type[unittest.TestCase], method_name: str) -> tuple[unittest.TestResult, int]:
    """Runs one test method, counting calls to any bound ``assert*`` method.

    Contract §3.9 describes this as "a sys.settrace-free counter by
    monkeypatching ... TestCase.failureException accounting". This is the
    concrete instrumentation that satisfies it: every callable attribute of
    the class whose name starts with "assert" (assertEqual, assertTrue,
    assertRaises, the lot -- including subclass-defined custom assertions) is
    wrapped, for the duration of exactly one test run, in a counting shim.
    """
    originals: dict[str, Any] = {
        name: getattr(cls, name)
        for name in dir(cls)
        if name.startswith("assert") and callable(getattr(cls, name, None))
    }
    counter = {"n": 0}

    def _wrap(fn: Any) -> Any:
        def _wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            counter["n"] += 1
            return fn(self, *args, **kwargs)

        return _wrapper

    for name, fn in originals.items():
        try:
            setattr(cls, name, _wrap(fn))
        except (AttributeError, TypeError):
            pass

    try:
        suite = unittest.TestSuite()
        suite.addTest(cls(method_name))
        result = unittest.TestResult()
        suite.run(result)
    finally:
        for name, fn in originals.items():
            try:
                setattr(cls, name, fn)
            except (AttributeError, TypeError):
                pass

    return result, counter["n"]


def run_entry(entry: CatalogEntry) -> EntryRun:
    try:
        cls, method_name = resolve_test(entry)
    except CatalogUnresolvable as exc:
        return EntryRun(entry=entry, executed=False, assertions=0, outcome="error", detail=str(exc))

    result, assertions = _count_assertions(cls, method_name)

    if result.errors:
        _, tb = result.errors[0]
        return EntryRun(entry=entry, executed=True, assertions=assertions, outcome="error", detail=tb)
    if result.failures:
        _, tb = result.failures[0]
        return EntryRun(entry=entry, executed=True, assertions=assertions, outcome="fail", detail=tb)
    if assertions < 1:
        return EntryRun(
            entry=entry, executed=True, assertions=0, outcome="fail",
            detail=f"{entry.id} executed 0 assertions",
        )
    return EntryRun(entry=entry, executed=True, assertions=assertions, outcome="pass", detail="")


# ---------------------------------------------------------------------------
# Coverage document (contract §8.4) -- the single call surface integration's
# future `run.py coverage --json` subcommand is expected to invoke. The
# per-card/per-plugin arithmetic (Coverage, coverage_report, the
# measured_plugins >= min_clusters floor) is owned by validate.py, which
# already imports `derive_roster` from this module at module scope; importing
# validate.py back here at module scope would be a cycle, so the import is
# deferred to call time (same convention pairing.py documents for
# Arm.from_dict / validate.validate_arm_manifest).
# ---------------------------------------------------------------------------

def coverage_document(repo_root: pathlib.Path) -> dict[str, Any]:
    """Build the coverage-schema JSON document: roster_size, total_cards,
    per_plugin, missing, complete, and measured_plugins (roster plugins
    carrying >= min_clusters cards -- contract §8.4's second, stricter
    floor). Raises ContractError if a card names a plugin outside the
    derived roster."""
    from . import validate as _validate  # deferred: avoids registry<->validate cycle

    return _validate._build_coverage_document(repo_root)


def print_coverage(repo_root: pathlib.Path, *, as_json: bool) -> int:
    """Validate and print the coverage document; return the process exit
    code. This is the body `run.py coverage [--json]` is expected to call --
    run.py itself is integration-owned (contract §6 SHARED files) and had
    not landed in this worktree as of registry lane part 3, so this
    function is exercised directly (and via
    `python3 -m evals.agentic.framework.validate --corpus --json`, which
    already emits the identical document) rather than through that CLI."""
    from . import validate as _validate  # deferred: see coverage_document

    doc = coverage_document(repo_root)
    io.load_schema("coverage").validate(doc)
    if as_json:
        import json as _json

        print(_json.dumps(doc, indent=2, sort_keys=True))
    else:
        print(
            f"registry coverage: roster_size={doc['roster_size']} "
            f"total_cards={doc['total_cards']} complete={doc['complete']} "
            f"measured_plugins={doc['measured_plugins']} "
            f"(min_clusters={_validate._MIN_CLUSTERS_FLOOR})"
        )
    return 0
