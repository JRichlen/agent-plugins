"""evals.agentic.framework.pairing -- arm construction and exposure parity
(registry lane, part 2, contract §3.11).

This module builds the ``Arm`` objects the four estimands (benchmark-spec §4)
compare: FULL_PACKAGE (the plugin installed whole), GUIDANCE_ONLY (prose
only), COMPOSITION (two plugins together vs each alone vs neither), and
VERSION (the same plugin at two git revisions) -- plus the single reusable
no-skill BASELINE arm that both FULL_PACKAGE and GUIDANCE_ONLY subtract
(benchmark-spec §4.2: "the SAME baseline B").

Design note carried forward for reviewers: ``build_arm``'s three required
inputs are a ``Card`` (task/verifier identity plus, optionally, an
author-curated ``Capability`` tuple), an ``Estimand``, and a plugin sequence.
Precedence rule used throughout this module: when the card names exactly the
plugin being built AND already carries a non-empty ``capabilities`` tuple
(the case for every committed reference card -- see
``evals/agentic/tasks/graveyard/graveyard-pos-01/card.json``), that
author-curated set is used verbatim, because the author has already scoped
it to what matters for this specific task. Otherwise (a plugin with no
committed card yet, or a composition/version arm spanning plugin(s) the card
does not name) capabilities are discovered structurally from the plugin's
own manifest and filesystem via ``discover_plugin_capabilities`` -- this is
what makes ``manifests/arms/*.json`` derivable for all 25 roster plugins
today, 21 of which have no card yet (contract §8.4's honest partial-corpus
state).

Exposure parity (T16, contract §3.11 clause (c)): the baseline arm never
receives a plugin's own capabilities, only the ``generic_equivalent`` string
declared for each capability whose kind is ``script``/``mcp``/``tool``
(``skill``/``command``/``hook`` capabilities have no baseline substitute --
that omission IS the no-skill baseline, benchmark-spec §4.1). Every
generated ``generic_equivalent`` embeds the capability's own name
(``"plain-bash-filesystem-git::<name>"``, ``"generic-read-only-tool-surface::
<name>"``) specifically so the substitution is always bijective: two
capabilities can never collide on one shared generic string, which would
break the "matched one-for-one" invariant ``exposure_diff`` enforces.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import pathlib
import shutil
import subprocess
import tempfile
import types
from collections.abc import Mapping, Sequence
from typing import Any

from . import io
from .contract import (
    ArmRole,
    Capability,
    Card,
    CardKind,
    ContractError,
    Estimand,
    ExposureParityViolation,
    new_id,
)
from .contract import digest as contract_digest
from .registry import PluginRef, derive_roster

__all__ = [
    "Arm",
    "Divergence",
    "build_arm",
    "materialize",
    "exposure_diff",
    "assert_exposure_parity",
    "guidance_only_tree",
    "assert_guidance_only_tree_is_pure",
    "is_degenerate",
    "composition_arms",
    "version_arms",
    "assign_stratum",
    "holdout_split",
    "discover_plugin_capabilities",
    "SCRIPT_DOMINANT_PLUGINS",
    "survey_version_estimand_targets",
    "estimand_availability",
]

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

# Tools BOTH arms of every card get -- an ordinary agentic tool floor
# neither the treatment nor the baseline is being tested on. Never edited
# per-card; a card's distinguishing surface lives entirely in `capabilities`.
_SHARED_GENERIC_TOOLS: tuple[str, ...] = ("Read", "Write", "Edit", "MultiEdit", "Bash", "Grep", "Glob")

_GENERIC_SCRIPT_PREFIX = "plain-bash-filesystem-git"
_GENERIC_MCP_PREFIX = "generic-read-only-tool-surface"

# Contract §11.4 UNKNOWN 5 / settled-unknowns.md item 6: the curated
# script-dominant set whose guidance-only arm this module's `is_degenerate`
# is expected to find inapplicable. `is_degenerate` re-verifies this
# structurally against each plugin's REAL surface every time it is called
# (see its docstring) rather than trusting the curation blindly.
SCRIPT_DOMINANT_PLUGINS: frozenset[str] = frozenset(
    {"agent-compiler", "graveyard", "redgate", "fleet-playbook-curator"}
)

_STRATUM_FIELDS: tuple[str, ...] = ("provider", "model", "revision", "effort", "harness")


# ---------------------------------------------------------------------------
# Arm / Divergence (contract §3.11)
# ---------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True, slots=True)
class Arm:
    arm_id: str
    estimand: Estimand
    role: ArmRole
    plugins: tuple[str, ...]
    revisions: Mapping[str, str]
    capabilities: tuple[Capability, ...]
    allowed_tools: tuple[str, ...]
    extra_dirs: tuple[str, ...]
    system_prompt_append: str
    realized_tree: Mapping[str, str]

    def config_hash(self) -> str:
        return contract_digest(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "arm_id": self.arm_id,
            "estimand": self.estimand.value,
            "role": self.role.value,
            "plugins": list(self.plugins),
            "revisions": dict(self.revisions),
            "capabilities": [c.to_dict() for c in self.capabilities],
            "allowed_tools": list(self.allowed_tools),
            "extra_dirs": list(self.extra_dirs),
            "system_prompt_append": self.system_prompt_append,
            "realized_tree": dict(self.realized_tree),
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "Arm":
        required = (
            "arm_id", "estimand", "role", "plugins", "revisions", "capabilities",
            "allowed_tools", "extra_dirs", "system_prompt_append", "realized_tree",
        )
        if not isinstance(d, Mapping):
            raise ContractError("Arm.from_dict: expected a mapping")
        missing = [k for k in required if k not in d]
        if missing:
            raise ContractError(f"Arm.from_dict: missing key(s) {missing!r}")
        extra = sorted(set(d) - set(required))
        if extra:
            raise ContractError(f"Arm.from_dict: unknown key(s) {extra!r}")
        try:
            estimand = Estimand(d["estimand"])
        except ValueError as exc:
            raise ContractError(f"Arm.from_dict: bad estimand {d['estimand']!r}") from exc
        try:
            role = ArmRole(d["role"])
        except ValueError as exc:
            raise ContractError(f"Arm.from_dict: bad role {d['role']!r}") from exc
        capabilities = tuple(Capability.from_dict(c) for c in d["capabilities"])
        return cls(
            arm_id=d["arm_id"],
            estimand=estimand,
            role=role,
            plugins=tuple(d["plugins"]),
            revisions=dict(d["revisions"]),
            capabilities=capabilities,
            allowed_tools=tuple(d["allowed_tools"]),
            extra_dirs=tuple(d["extra_dirs"]),
            system_prompt_append=d["system_prompt_append"],
            realized_tree=dict(d["realized_tree"]),
        )


@dataclasses.dataclass(frozen=True, slots=True)
class Divergence:
    field: str
    treatment: str
    baseline: str
    permitted: bool
    reason: str


# ---------------------------------------------------------------------------
# Capability discovery (real surface, not card-authored) -- feeds
# manifests/arms/*.json for every roster plugin, cards or not.
# ---------------------------------------------------------------------------

def _iter_real_scripts(plugin_dir: pathlib.Path) -> list[pathlib.Path]:
    """Mirrors registry._has_scripts's own-surface filter (excludes a
    plugin's `evals/**` test furniture) but returns the actual files.

    Excludes `__pycache__/` (and any other `.gitignore`d, machine-generated
    directory a script's own interpreter drops next to it): a `.pyc` cache
    file is not a committed part of the plugin's surface, is entirely
    absent on a fresh clone, and only exists at all once a machine happens
    to have executed the script -- discovering it would make
    `derived_capabilities` (and the committed `manifests/arms/*.json` that
    materialize it) depend on this machine's local execution history rather
    than the plugin's real, reproducible, committed surface. Caught during
    the registry lane's corpus audit: `plugins/agent-compiler/scripts/` was
    surfacing three spurious `script` capabilities named `*.cpython-312.pyc`
    alongside the three real `.py` scripts before this filter existed."""
    found: list[pathlib.Path] = []
    for scripts_dir in sorted(plugin_dir.rglob("scripts")):
        if not scripts_dir.is_dir():
            continue
        rel_parts = scripts_dir.relative_to(plugin_dir).parts
        if "evals" in rel_parts:
            continue
        for f in sorted(scripts_dir.rglob("*")):
            if not f.is_file():
                continue
            if "__pycache__" in f.relative_to(scripts_dir).parts:
                continue
            found.append(f)
    return found


def discover_plugin_capabilities(ref: PluginRef, repo_root: pathlib.Path) -> tuple[Capability, ...]:
    """The plugin's REAL capability surface, derived from disk -- never a
    curated/hardcoded list. Used for every plugin that has no committed
    card yet, and for composition/version arms spanning plugin(s) beyond
    whichever single plugin a card happens to name."""
    repo_root = pathlib.Path(repo_root)
    plugin_dir = repo_root / ref.directory
    caps: list[Capability] = []

    for skill in ref.skills:
        caps.append(Capability(name=skill, kind="skill", source_plugin=ref.name, generic_equivalent=None))
    for command in ref.commands:
        caps.append(Capability(name=command, kind="command", source_plugin=ref.name, generic_equivalent=None))

    if ref.has_hooks:
        hooks_path = plugin_dir / "hooks" / "hooks.json"
        if hooks_path.is_file():
            hooks_doc = io.load_json(hooks_path)
            for event in sorted((hooks_doc.get("hooks") or {}).keys()):
                caps.append(
                    Capability(name=f"hooks/{event}", kind="hook", source_plugin=ref.name, generic_equivalent=None)
                )

    if ref.has_scripts:
        for script in _iter_real_scripts(plugin_dir):
            name = script.name
            caps.append(
                Capability(
                    name=name, kind="script", source_plugin=ref.name,
                    generic_equivalent=f"{_GENERIC_SCRIPT_PREFIX}::{name}",
                )
            )

    if ref.has_mcp:
        manifest_path = plugin_dir / ".claude-plugin" / "plugin.json"
        manifest = io.load_json(manifest_path)
        servers = manifest.get("mcpServers")
        if isinstance(servers, Mapping):
            for server_name in sorted(servers):
                caps.append(
                    Capability(
                        name=server_name, kind="mcp", source_plugin=ref.name,
                        generic_equivalent=f"{_GENERIC_MCP_PREFIX}::{server_name}",
                    )
                )

    return tuple(caps)


def _capabilities_for(card: Card, ref: PluginRef, repo_root: pathlib.Path) -> tuple[Capability, ...]:
    if card.plugin == ref.name and card.capabilities:
        return card.capabilities
    return discover_plugin_capabilities(ref, repo_root)


def _allowed_tools_for_treatment(caps: Sequence[Capability]) -> tuple[str, ...]:
    tool_names = sorted(c.name for c in caps if c.kind in ("script", "mcp", "tool"))
    return tuple(_SHARED_GENERIC_TOOLS) + tuple(tool_names)


def _substitutes_for(caps: Sequence[Capability]) -> tuple[str, ...]:
    subs = sorted(
        c.generic_equivalent for c in caps if c.kind in ("script", "mcp", "tool") and c.generic_equivalent
    )
    return tuple(subs)


# ---------------------------------------------------------------------------
# Materialization -- writes an Arm's declared surface to real files and
# returns the relpath -> sha256 map. `build_arm` uses this to POPULATE
# realized_tree; the public `materialize()` re-derives it on demand and
# verifies it still agrees with the Arm it was handed (catches a hand-edited
# or stale Arm rather than silently re-writing a different tree under the
# same name).
# ---------------------------------------------------------------------------

def _write_bytes(root: pathlib.Path, relpath: str, data: bytes, written: dict[str, str]) -> None:
    target = root / relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    written[relpath] = hashlib.sha256(data).hexdigest()


def _read_capability_bytes(
    cap: Capability, repo_root: pathlib.Path, candidate: pathlib.Path, *, rev: str | None
) -> bytes | None:
    if rev is None:
        return candidate.read_bytes() if candidate.is_file() else None
    try:
        rel = candidate.relative_to(repo_root).as_posix()
    except ValueError:
        return None
    result = subprocess.run(
        ["git", "show", f"{rev}:{rel}"], cwd=repo_root, capture_output=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def _materialize_capability(
    cap: Capability, repo_root: pathlib.Path, root: pathlib.Path, written: dict[str, str], *, rev: str | None = None
) -> None:
    if cap.source_plugin is None:
        return  # a generic (baseline-side) capability has no source file of its own
    plugin_dir = repo_root / "plugins" / cap.source_plugin

    if cap.kind == "skill":
        skill_dir = plugin_dir / "skills" / cap.name
        if rev is None and skill_dir.is_dir():
            for f in sorted(skill_dir.rglob("*.md")):
                if "scripts" in f.relative_to(skill_dir).parts or "hooks" in f.relative_to(skill_dir).parts:
                    continue
                data = f.read_bytes()
                rel = f"skills/{cap.name}/{f.relative_to(skill_dir).as_posix()}"
                _write_bytes(root, rel, data, written)
        elif rev is not None:
            main = skill_dir / "SKILL.md"
            data = _read_capability_bytes(cap, repo_root, main, rev=rev)
            if data is not None:
                _write_bytes(root, f"skills/{cap.name}/SKILL.md", data, written)
    elif cap.kind == "command":
        src = plugin_dir / "commands" / f"{cap.name}.md"
        data = _read_capability_bytes(cap, repo_root, src, rev=rev)
        if data is not None:
            _write_bytes(root, f"commands/{cap.name}.md", data, written)
    elif cap.kind == "hook":
        hooks_json = plugin_dir / "hooks" / "hooks.json"
        data = _read_capability_bytes(cap, repo_root, hooks_json, rev=rev)
        if data is not None:
            _write_bytes(root, "hooks/hooks.json", data, written)
    # kind in {"script", "mcp", "tool"}: these are TOOLS the agent may invoke,
    # not files the task workspace carries -- a script lives in the plugin's
    # own install directory (not the card's working tree) and an MCP server
    # is a subprocess, not a file either arm's tree exposes. Their exposure
    # is captured entirely by `allowed_tools` (clause c, matched
    # substitution); deliberately no realized_tree footprint here, or a
    # baseline missing the treatment's own script FILE would register as an
    # impermissible tree divergence on top of (and inconsistent with) the
    # allowed_tools substitution that already governs it.


def _materialize_extra_dir(rel: str, repo_root: pathlib.Path, root: pathlib.Path, written: dict[str, str]) -> None:
    src = repo_root / rel
    if src.is_dir():
        for f in sorted(src.rglob("*")):
            if f.is_file():
                data = f.read_bytes()
                _write_bytes(root, f"{rel}/{f.relative_to(src).as_posix()}", data, written)
    elif src.is_file():
        _write_bytes(root, rel, src.read_bytes(), written)


def _materialize_write(arm: Arm, workspace: pathlib.Path, *, rev: str | None = None) -> tuple[pathlib.Path, dict[str, str]]:
    workspace = pathlib.Path(workspace)
    root = workspace / arm.arm_id
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    repo_root = io.repo_root()
    written: dict[str, str] = {}

    # `allowed_tools` is already a first-class Arm field, compared directly
    # by exposure_diff's clause-(c) logic; it is deliberately NOT also
    # mirrored into realized_tree, which represents the on-disk working
    # tree/config, not the tool allowlist.
    for cap in arm.capabilities:
        _materialize_capability(cap, repo_root, root, written, rev=rev)
    for rel_dir in arm.extra_dirs:
        _materialize_extra_dir(rel_dir, repo_root, root, written)
    if arm.system_prompt_append:
        _write_bytes(root, "SYSTEM_PROMPT_APPEND.txt", arm.system_prompt_append.encode("utf-8"), written)

    return root, written


def materialize(arm: Arm, workspace: pathlib.Path) -> pathlib.Path:
    """Writes `arm`'s declared surface to real files under `workspace` and
    returns the directory. Verifies the resulting hashes still agree with
    `arm.realized_tree` -- an Arm built by this module and then hand-edited
    (or re-materialized after its source files changed underneath it) is
    refused rather than silently re-written under the same name."""
    root, written = _materialize_write(arm, workspace)
    if arm.realized_tree and dict(arm.realized_tree) != written:
        raise ContractError(
            f"materialize: {arm.arm_id}: on-disk hashes disagree with arm.realized_tree "
            "-- rebuild the Arm with build_arm/composition_arms/version_arms rather than "
            "editing realized_tree by hand"
        )
    return root


# ---------------------------------------------------------------------------
# Baseline arm (the single reusable Estimand.BASELINE arm, benchmark-spec §4.2)
# ---------------------------------------------------------------------------

def _baseline_arm(subs: Sequence[str], workspace: pathlib.Path) -> Arm:
    allowed = tuple(_SHARED_GENERIC_TOOLS) + tuple(subs)
    shell = Arm(
        arm_id=new_id("arm-baseline"), estimand=Estimand.BASELINE, role=ArmRole.BASELINE,
        plugins=(), revisions=types.MappingProxyType({}), capabilities=(), allowed_tools=allowed,
        extra_dirs=(), system_prompt_append="", realized_tree=types.MappingProxyType({}),
    )
    _root, written = _materialize_write(shell, workspace)
    return dataclasses.replace(shell, realized_tree=types.MappingProxyType(written))


# ---------------------------------------------------------------------------
# Full-package arm
# ---------------------------------------------------------------------------

def _full_package_arm(plugin_names: tuple[str, ...], caps: tuple[Capability, ...], workspace: pathlib.Path) -> Arm:
    allowed = _allowed_tools_for_treatment(caps)
    shell = Arm(
        arm_id=new_id(f"arm-full-{'-'.join(plugin_names) or 'none'}"),
        estimand=Estimand.FULL_PACKAGE, role=ArmRole.TREATMENT,
        plugins=plugin_names, revisions=types.MappingProxyType({}), capabilities=caps,
        allowed_tools=allowed, extra_dirs=(), system_prompt_append="",
        realized_tree=types.MappingProxyType({}),
    )
    _root, written = _materialize_write(shell, workspace)
    return dataclasses.replace(shell, realized_tree=types.MappingProxyType(written))


# ---------------------------------------------------------------------------
# Guidance-only arm and tree (T17's degeneracy rule; benchmark-spec §4.2)
# ---------------------------------------------------------------------------

def _copy_markdown_only(src_dir: pathlib.Path, dst_root: pathlib.Path, rel_prefix: str, written: dict[str, str]) -> None:
    if not src_dir.is_dir():
        return
    for f in sorted(src_dir.rglob("*.md")):
        parts = f.relative_to(src_dir).parts
        if "scripts" in parts or "hooks" in parts:
            continue
        data = f.read_bytes()
        rel = f"{rel_prefix}/{f.relative_to(src_dir).as_posix()}"
        _write_bytes(dst_root, rel, data, written)


def assert_guidance_only_tree_is_pure(root: pathlib.Path) -> None:
    """Raises ExposureParityViolation if `root` (a materialized guidance-only
    tree) carries a hooks/ or scripts/ directory, or any file mentioning
    "mcpServers" -- the three things a guidance-only arm must never load."""
    root = pathlib.Path(root)
    for bad_name in ("scripts", "hooks"):
        for hit in root.rglob(bad_name):
            if hit.is_dir():
                raise ExposureParityViolation(
                    f"guidance-only tree {root} carries a {bad_name}/ directory at {hit}"
                )
    for f in root.rglob("*"):
        if f.is_file():
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if "mcpServers" in text:
                raise ExposureParityViolation(
                    f"guidance-only tree {root} carries a file referencing mcpServers: {f}"
                )


def guidance_only_tree(plugin: PluginRef, workspace: pathlib.Path) -> pathlib.Path:
    repo_root = io.repo_root()
    workspace = pathlib.Path(workspace)
    root = workspace / f"{plugin.name}-guidance-only"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    plugin_dir = repo_root / plugin.directory

    written: dict[str, str] = {}
    for skill in plugin.skills:
        _copy_markdown_only(plugin_dir / "skills" / skill, root, f"skills/{skill}", written)
    for command in plugin.commands:
        src = plugin_dir / "commands" / f"{command}.md"
        if src.is_file():
            _write_bytes(root, f"commands/{command}.md", src.read_bytes(), written)

    assert_guidance_only_tree_is_pure(root)
    return root


def _build_guidance_only_arm(card: Card, ref: PluginRef, workspace: pathlib.Path) -> Arm:
    repo_root = io.repo_root()
    tree_path = guidance_only_tree(ref, workspace)
    full_caps = _capabilities_for(card, ref, repo_root)
    guidance_caps = tuple(c for c in full_caps if c.kind in ("skill", "command"))

    written: dict[str, str] = {}
    for f in sorted(tree_path.rglob("*")):
        if f.is_file():
            rel = f.relative_to(tree_path).as_posix()
            written[rel] = hashlib.sha256(f.read_bytes()).hexdigest()

    return Arm(
        arm_id=new_id(f"arm-guid-{ref.name}"), estimand=Estimand.GUIDANCE_ONLY, role=ArmRole.TREATMENT,
        plugins=(ref.name,), revisions=types.MappingProxyType({}), capabilities=guidance_caps,
        allowed_tools=tuple(_SHARED_GENERIC_TOOLS), extra_dirs=(), system_prompt_append="",
        realized_tree=types.MappingProxyType(written),
    )


def is_degenerate(arm: Arm, card: Card) -> bool:
    """True when a guidance-only arm cannot perform `card`'s task at all
    because the plugin's real value is procedural (a script/hook/mcp
    server), not prose a model could imitate by hand -- contract §11.4
    UNKNOWN 5 / settled-unknowns.md item 6. Offline and without a model
    call, true task-level degeneracy cannot be executed and observed; the
    structural proxy used here is the curated `SCRIPT_DOMINANT_PLUGINS` set,
    but it is not trusted blindly -- every call re-derives the plugin's REAL
    capability surface and raises if the curation no longer matches reality
    (the plugin now has no script/hook/mcp capability to withhold at all),
    so a stale curation fails loudly instead of silently asserting a false
    degeneracy."""
    if arm.estimand is not Estimand.GUIDANCE_ONLY:
        return False
    if card.plugin not in SCRIPT_DOMINANT_PLUGINS:
        return False

    repo_root = io.repo_root()
    roster = derive_roster(repo_root)
    ref = next((r for r in roster if r.name == card.plugin), None)
    if ref is None:
        raise ContractError(f"is_degenerate: {card.plugin!r} is not in the live roster")
    full_caps = discover_plugin_capabilities(ref, repo_root)
    withheld_kinds = {c.kind for c in full_caps} & {"script", "hook", "mcp"}
    if not withheld_kinds:
        raise ContractError(
            f"is_degenerate: {card.plugin!r} is in SCRIPT_DOMINANT_PLUGINS but its real "
            "surface carries no script/hook/mcp capability to withhold -- the curated set "
            "needs updating, this is not a real degeneracy"
        )
    return True


# ---------------------------------------------------------------------------
# build_arm dispatcher (contract §3.11)
# ---------------------------------------------------------------------------

def build_arm(
    card: Card, estimand: Estimand, plugins: Sequence[PluginRef], *, workspace: pathlib.Path
) -> Arm:
    workspace = pathlib.Path(workspace)
    repo_root = io.repo_root()

    if estimand is Estimand.BASELINE:
        if plugins:
            raise ContractError("build_arm: BASELINE estimand takes an empty plugins sequence")
        subs = _substitutes_for(card.capabilities)
        return _baseline_arm(subs, workspace)

    if estimand is Estimand.FULL_PACKAGE:
        if len(plugins) != 1:
            raise ContractError(f"build_arm: full-package needs exactly one plugin; got {len(plugins)}")
        ref = plugins[0]
        caps = _capabilities_for(card, ref, repo_root)
        return _full_package_arm((ref.name,), caps, workspace)

    if estimand is Estimand.GUIDANCE_ONLY:
        if len(plugins) != 1:
            raise ContractError(f"build_arm: guidance-only needs exactly one plugin; got {len(plugins)}")
        return _build_guidance_only_arm(card, plugins[0], workspace)

    raise ContractError(
        f"build_arm: estimand {estimand.value!r} is constructed by a dedicated function "
        "(composition_arms for 'composition', version_arms for 'version'), not build_arm"
    )


# ---------------------------------------------------------------------------
# Composition arms (benchmark-spec §4.3)
# ---------------------------------------------------------------------------

def composition_arms(
    p: PluginRef, q: PluginRef, card: Card, workspace: pathlib.Path
) -> tuple[Arm, Arm, Arm, Arm]:
    workspace = pathlib.Path(workspace)
    repo_root = io.repo_root()

    empty = _baseline_arm((), workspace)
    p_caps = _capabilities_for(card, p, repo_root) if card.plugin == p.name else discover_plugin_capabilities(p, repo_root)
    q_caps = _capabilities_for(card, q, repo_root) if card.plugin == q.name else discover_plugin_capabilities(q, repo_root)
    p_only = _full_package_arm((p.name,), p_caps, workspace)
    q_only = _full_package_arm((q.name,), q_caps, workspace)
    p_and_q = _full_package_arm((p.name, q.name), p_caps + q_caps, workspace)
    return (empty, p_only, q_only, p_and_q)


# ---------------------------------------------------------------------------
# Version arms (benchmark-spec §4.4) and the two-revision survey
# (contract §11.4 UNKNOWN / settled-unknowns.md item 6)
# ---------------------------------------------------------------------------

def _assert_revision_resolves(repo_root: pathlib.Path, rev: str) -> None:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", f"{rev}^{{commit}}"], cwd=repo_root, capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise ContractError(f"version_arms: revision {rev!r} does not resolve in this repo: {result.stderr.strip()}")


def _version_arm(plugin: PluginRef, rev: str, caps: tuple[Capability, ...], workspace: pathlib.Path) -> Arm:
    allowed = _allowed_tools_for_treatment(caps)
    shell = Arm(
        arm_id=new_id(f"arm-ver-{plugin.name}-{rev[:12]}"), estimand=Estimand.VERSION, role=ArmRole.TREATMENT,
        plugins=(plugin.name,), revisions=types.MappingProxyType({plugin.name: rev}), capabilities=caps,
        allowed_tools=allowed, extra_dirs=(), system_prompt_append="",
        realized_tree=types.MappingProxyType({}),
    )
    _root, written = _materialize_write(shell, workspace, rev=rev)
    return dataclasses.replace(shell, realized_tree=types.MappingProxyType(written))


def version_arms(
    plugin: PluginRef, rev_a: str, rev_b: str, card: Card, workspace: pathlib.Path
) -> tuple[Arm, Arm]:
    workspace = pathlib.Path(workspace)
    repo_root = io.repo_root()
    _assert_revision_resolves(repo_root, rev_a)
    _assert_revision_resolves(repo_root, rev_b)
    caps = _capabilities_for(card, plugin, repo_root)
    arm_a = _version_arm(plugin, rev_a, caps, workspace)
    arm_b = _version_arm(plugin, rev_b, caps, workspace)
    return (arm_a, arm_b)


def _diff_touches_behavior(diff_text: str, plugin_dir_rel: str) -> bool:
    changed: set[str] = set()
    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            parts = line.split(" ")
            if len(parts) >= 3 and parts[2].startswith("a/"):
                changed.add(parts[2][2:])
    plugin_json = f"{plugin_dir_rel}/.claude-plugin/plugin.json"
    for path in changed:
        if path == plugin_json:
            continue
        if path.endswith(".md"):
            continue
        # A plugin's own evals/** is test furniture, not shipped behavior --
        # the same exclusion registry.derive_roster applies to has_scripts.
        rel_parts = pathlib.PurePosixPath(path).relative_to(plugin_dir_rel).parts if path.startswith(f"{plugin_dir_rel}/") else ()
        if "evals" in rel_parts:
            continue
        return True
    return False


def _plugin_version_at(root: pathlib.Path, rev: str, rel: str) -> str | None:
    """The plugin.json 'version' string as of `rev`, or None when the file
    does not exist at that revision/path at all (a creation event, not a
    version-to-version comparison)."""
    result = subprocess.run(["git", "show", f"{rev}:{rel}"], cwd=root, capture_output=True)
    if result.returncode != 0:
        return None
    try:
        doc = json.loads(result.stdout.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None
    version = doc.get("version") if isinstance(doc, dict) else None
    return version if isinstance(version, str) else None


def survey_version_estimand_targets(repo_root: pathlib.Path | None = None) -> tuple[Mapping[str, str], ...]:
    """Contract §11.4 / settled-unknowns.md item 6: `git log` over every
    roster plugin's `.claude-plugin/plugin.json`, looking for a consecutive
    pair of revisions that BOTH already carry the file (excluding the
    creation commit, whose "diff" is the whole plugin appearing from
    nothing and is not a version-to-version comparison), whose parsed
    `version` string actually differs (a real bump, not a no-op re-save),
    and whose diff touches a script/hook/mcp file rather than only prose
    (`.md`) or the version bump itself. Offline, reads git only."""
    root = pathlib.Path(repo_root) if repo_root is not None else io.repo_root()
    roster = derive_roster(root)
    findings: list[dict[str, str]] = []
    for ref in roster:
        rel = f"{ref.directory}/.claude-plugin/plugin.json"
        log = subprocess.run(
            ["git", "log", "--follow", "--oneline", "--", rel], cwd=root, capture_output=True, text=True,
        )
        commits = [ln.split(" ", 1)[0] for ln in log.stdout.splitlines() if ln.strip()]
        if len(commits) < 2:
            continue
        for newer, older in zip(commits, commits[1:]):
            version_older = _plugin_version_at(root, older, rel)
            version_newer = _plugin_version_at(root, newer, rel)
            if version_older is None or version_newer is None:
                continue  # one side is the creation event, not a real revision pair
            if version_older == version_newer:
                continue  # no version bump between these two states
            diff = subprocess.run(
                ["git", "diff", older, newer, "--", ref.directory], cwd=root, capture_output=True, text=True,
            )
            if _diff_touches_behavior(diff.stdout, ref.directory):
                findings.append({"plugin": ref.name, "rev_older": older, "rev_newer": newer})
    return tuple(findings)


# ---------------------------------------------------------------------------
# Exposure parity (T16, contract §3.11 clause (c))
# ---------------------------------------------------------------------------

def _is_permitted_tree_path(path: str, treatment: Arm) -> bool:
    for sub in ("skills/", "commands/", "hooks/", "agents/"):
        if path.startswith(sub):
            return True
    if path.startswith("mcp/"):
        return True
    return False


def exposure_diff(treatment: Arm, baseline: Arm) -> tuple[Divergence, ...]:
    divergences: list[Divergence] = []

    # extra_dirs
    t_extra = set(treatment.extra_dirs)
    b_extra = set(baseline.extra_dirs)
    for d in sorted(t_extra - b_extra):
        divergences.append(Divergence(f"extra_dirs:{d}", d, "<absent>", False, "extra_dir present in treatment only"))
    for d in sorted(b_extra - t_extra):
        divergences.append(Divergence(f"extra_dirs:{d}", "<absent>", d, False, "extra_dir present in baseline only"))

    # system_prompt_append: must be byte-identical
    if treatment.system_prompt_append != baseline.system_prompt_append:
        divergences.append(
            Divergence(
                "system_prompt_append", treatment.system_prompt_append, baseline.system_prompt_append,
                False, "system_prompt_append must be byte-identical between arms",
            )
        )

    # realized_tree: same working tree except the treatment's own
    # skills/commands/hooks/agents surface and each arm's own mcp/ config.
    t_tree = dict(treatment.realized_tree)
    b_tree = dict(baseline.realized_tree)
    for path in sorted(set(t_tree) | set(b_tree)):
        t_hash = t_tree.get(path)
        b_hash = b_tree.get(path)
        if t_hash == b_hash:
            continue
        permitted = _is_permitted_tree_path(path, treatment)
        reason = (
            "plugin's own skills/commands/hooks/agents surface or mcp config (clause a/b)"
            if permitted else "realized_tree divergence outside the plugin's own surface"
        )
        divergences.append(Divergence(f"realized_tree:{path}", t_hash or "<absent>", b_hash or "<absent>", permitted, reason))

    # allowed_tools: matched one-for-one substitution only (clause c)
    t_only = [t for t in treatment.allowed_tools if t not in baseline.allowed_tools]
    b_only = [t for t in baseline.allowed_tools if t not in treatment.allowed_tools]
    cap_by_name = {c.name: c for c in treatment.capabilities}
    matched_b: set[str] = set()
    unmatched_t: list[str] = []
    for t_entry in t_only:
        cap = cap_by_name.get(t_entry)
        if cap is not None and cap.generic_equivalent is not None and cap.generic_equivalent in b_only:
            matched_b.add(cap.generic_equivalent)
            divergences.append(
                Divergence(
                    f"allowed_tools:{t_entry}", t_entry, cap.generic_equivalent, True,
                    f"matched one-for-one substitution of capability {cap.name!r} (clause c)",
                )
            )
        else:
            unmatched_t.append(t_entry)
    for t_entry in unmatched_t:
        divergences.append(
            Divergence(f"allowed_tools:{t_entry}", t_entry, "<absent>", False, "treatment-only tool with no matched baseline substitute")
        )
    for b_entry in b_only:
        if b_entry in matched_b:
            continue
        divergences.append(
            Divergence(
                f"allowed_tools:{b_entry}", "<absent>", b_entry, False,
                "baseline-only tool that is not the declared generic_equivalent of any treatment "
                "capability (unmatched widening)",
            )
        )

    return tuple(divergences)


def assert_exposure_parity(treatment: Arm, baseline: Arm) -> None:
    diffs = exposure_diff(treatment, baseline)
    bad = [d for d in diffs if not d.permitted]
    if bad:
        rendered = "; ".join(f"{d.field}: treatment={d.treatment!r} baseline={d.baseline!r} ({d.reason})" for d in bad)
        raise ExposureParityViolation(f"{len(bad)} impermissible divergence(s): {rendered}")


# ---------------------------------------------------------------------------
# Stratum assignment / holdout split
# ---------------------------------------------------------------------------

def assign_stratum(requested: Any, realized: Any) -> tuple[Any, tuple[str, ...]]:
    flags = tuple(f for f in _STRATUM_FIELDS if getattr(requested, f) != getattr(realized, f))
    return realized, flags


def holdout_split(
    cards: Sequence[Card], *, fraction: float, seed: int
) -> tuple[tuple[Card, ...], tuple[Card, ...]]:
    if not (0.0 <= fraction <= 1.0):
        raise ContractError(f"holdout_split: fraction must be within [0, 1], got {fraction!r}")

    import random

    forced_holdout = tuple(c for c in cards if c.holdout)
    rest = sorted((c for c in cards if not c.holdout), key=lambda c: c.card_id)
    rng = random.Random(seed)
    shuffled = list(rest)
    rng.shuffle(shuffled)

    n_extra = round(fraction * len(cards)) - len(forced_holdout)
    n_extra = max(0, min(n_extra, len(shuffled)))
    extra_holdout = shuffled[:n_extra]
    dev = shuffled[n_extra:]

    dev_sorted = tuple(sorted(dev, key=lambda c: c.card_id))
    holdout_sorted = tuple(sorted((*forced_holdout, *extra_holdout), key=lambda c: c.card_id))
    return dev_sorted, holdout_sorted


# ---------------------------------------------------------------------------
# Per-plugin estimand availability summary (this task's acceptance API)
# ---------------------------------------------------------------------------

def estimand_availability(repo_root: pathlib.Path | None = None) -> dict[str, dict[str, str]]:
    """Per-plugin estimand availability across the live 25-plugin roster --
    a structural survey, offline, no model call. For each roster plugin:

      full-package:   always "available" (every plugin can be installed whole).
      guidance-only:  "guidance-only-inapplicable" for the curated
                      script-dominant set (re-verified structurally, see
                      is_degenerate); "available" otherwise.
      composition:    single-plugin summary cannot name a partner; always
                      "n/a (needs a second plugin; see composition_arms)".
      version:        the two-revision survey's finding for this plugin, or
                      "unavailable (no two-revision target identified)".
    """
    root = pathlib.Path(repo_root) if repo_root is not None else io.repo_root()
    roster = derive_roster(root)
    version_hits = {f["plugin"]: f for f in survey_version_estimand_targets(root)}

    result: dict[str, dict[str, str]] = {}
    for ref in roster:
        caps = discover_plugin_capabilities(ref, root)
        survey_card = Card(
            card_id=f"{ref.name}-survey-00", plugin=ref.name, kind=CardKind.POSITIVE,
            task_path="", outcome_verifier="", adoption_verifier="", pass_fixture="",
            fail_fixture="", expected_boundary_verdict="", capabilities=caps,
            mutations=("survey-placeholder",), holdout=False,
        )
        degenerate = False
        if ref.name in SCRIPT_DOMINANT_PLUGINS:
            with tempfile.TemporaryDirectory() as tmp:
                g_arm = _build_guidance_only_arm(survey_card, ref, pathlib.Path(tmp))
                degenerate = is_degenerate(g_arm, survey_card)

        version_status = "unavailable (no two-revision target identified)"
        if ref.name in version_hits:
            hit = version_hits[ref.name]
            version_status = f"available ({hit['rev_older']}..{hit['rev_newer']})"

        result[ref.name] = {
            "full-package": "available",
            "guidance-only": "guidance-only-inapplicable" if degenerate else "available",
            "composition": "n/a (needs a second plugin; see composition_arms)",
            "version": version_status,
        }
    return result
