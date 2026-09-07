"""evals.agentic.framework.adapters — native harness drivers and the host ledger.

Adapter lane. Implements implementation-contract §3.12 and §10, and it is the
trust boundary of the whole framework: this is the only module in the codebase
that may *produce* :data:`~evals.agentic.framework.contract.EvidenceClass.NATIVE_PROVEN`,
and it produces it from exactly one function, :func:`evidence_class_for`, whose
mapping takes no argument that a caller could use to promote a simulated run.

Three structural properties carry that boundary; none of them is a convention a
future edit can quietly drop without a test going red:

1. **The witness is sealed at construction.** :class:`HostLedger` derives every
   entry's ``host_signature.value_class`` from a closure created in ``__init__``
   (:func:`_sealed_signer`), and ``__slots__`` plus ``__setattr__`` refuse to
   rebind the witness or the key afterwards. There is no per-``append``
   override and no attribute left to flip, so a holder of a replay ledger cannot
   mint a host-observed entry. A ``HOST_OBSERVED`` ledger mints its own HMAC key
   with ``secrets.token_bytes(32)``; both witnesses *refuse* a caller-supplied
   one (:class:`~evals.agentic.framework.contract.EvidencePromotionRefused`).
2. **Replay and worker paths cannot hold a host-observed ledger.**
   :class:`ReplaySession` and :func:`attach_session` reject one outright.
3. **Spawning a real harness needs an approval token that is in the run
   manifest.** :meth:`CliDriver.spawn` raises
   :class:`~evals.agentic.framework.contract.ApprovalRequired` *before* it
   constructs any argv or touches :mod:`subprocess`.
4. **Verification authority is a capability, not a parameter.**
   :class:`LedgerReader` refuses raw key bytes; the only thing that can bless a
   ledger is the :class:`_RunKey` :meth:`HostLedger.verifier` wraps, which is
   bound to that ledger's own path and exists only in the minting process. A
   ledger in which the host witnessed nothing is never "verified", whatever key
   it is shown.
5. **Bypass-permissions mode is banned by value, not by spelling.**
   :data:`BANNED_ARGV_VALUES` and :data:`SAFE_ARGV_VALUES` are enforced over the
   shipped configs (:func:`assert_flags_supported`) *and* over rendered argv
   (:meth:`CliDriver.build_argv`), because ``--permission-mode`` and
   ``--sandbox`` take their dangerous settings as ordinary values that no
   flag-name scan can see.

§10.2's UNKNOWN is honoured rather than guessed: no capture of either installed
CLI's event stream exists, so ``fixtures/native/streams/`` holds no grammar and
:func:`load_grammar` raises. Guessed field names would be indistinguishable from
real ones once written down, which is exactly the failure this lane exists to
prevent.
"""
from __future__ import annotations

import dataclasses
import hmac
import json
import os
import pathlib
import re
import secrets
import shutil
import signal
import subprocess
import time
import uuid
from collections.abc import Mapping, Sequence
from hashlib import sha256
from typing import Any, Iterator

from evals.agentic.framework import classify as _classify
from evals.agentic.framework import io as _io
from evals.agentic.framework import protocols as _protocols
from evals.agentic.framework.contract import (
    UNKNOWN,
    AdapterClass,
    ApprovalRequired,
    ArmRole,
    Attempt,
    ContractError,
    ControlKind,
    EvidenceClass,
    EvidencePromotionRefused,
    Event,
    EventKind,
    FlagNotSupported,
    ForgedProvenance,
    HostSignature,
    LedgerTampered,
    Manifest,
    SignatureClass,
    Stratum,
    Usage,
    Verdict,
    assert_native_backed,
    canonical_json,
    new_id,
    now_rfc3339,
)

__all__ = [
    # §3.12 driver config and grammar
    "DriverConfig", "StreamGrammar", "JsonPathSpec",
    "DRIVERS_DIR", "NATIVE_FIXTURES_DIR", "STREAMS_DIR",
    "load_driver_config", "load_grammar",
    "installed_help", "declared_flags", "assert_flags_supported",
    "BANNED_FLAG_PATTERNS", "BANNED_ARGV_VALUES", "SAFE_ARGV_VALUES",
    "FlagNotSupported", "FlagNotSupportedError",
    # §3.12 driver
    "CliDriver", "PlannedInvocation", "dry_run",
    # §3.12 sessions
    "HarnessSession", "TurnRecord", "ReplaySession", "attach_session",
    "IsolationReport", "check_fresh_isolation",
    # REPAIR S-12: the production session -> Attempt constructor
    "attempt_from_session",
    # §3.12 ledger
    "HostLedger", "LedgerReader", "ChainVerification", "SpawnAccounting",
    # §3.12 evidence and telemetry
    "evidence_class_for", "worker_evidence_class", "parse_usage",
    # re-exported per contract §2.5
    "ApprovalRequired", "EvidencePromotionRefused", "ForgedProvenance",
    "LedgerTampered", "ContractError",
]


# ---------------------------------------------------------------------------
# Fixture locations. repo_root() walks to .claude-plugin/marketplace.json from
# this file (io.py §3.2), never from the cwd, so a framework staged into the
# counterfeit synthetic root reads that root's fixtures and not the real repo's.
# ---------------------------------------------------------------------------

def NATIVE_FIXTURES_DIR() -> pathlib.Path:
    """`<repo>/evals/agentic/fixtures/native`."""
    return _io.repo_root() / "evals" / "agentic" / "fixtures" / "native"


def DRIVERS_DIR() -> pathlib.Path:
    """Where the two shipped `DriverConfig` documents live (§10.1)."""
    return NATIVE_FIXTURES_DIR() / "drivers"


def STREAMS_DIR() -> pathlib.Path:
    """Where a real captured harness stream would live. Deliberately empty (§10.2)."""
    return NATIVE_FIXTURES_DIR() / "streams"


# ---------------------------------------------------------------------------
# §3.12 — DriverConfig
# ---------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True, slots=True)
class DriverConfig:
    name: str
    binary: str
    help_argv: tuple[str, ...]
    argv_template: tuple[str, ...]
    optional_argv: Mapping[str, tuple[str, ...]]
    env: Mapping[str, str]
    cwd: str
    timeout_s: float
    stream_format: str
    grammar: str
    adapter_class: AdapterClass

    def modes(self) -> tuple[str, ...]:
        return tuple(sorted(self.optional_argv))


_DRIVER_KEYS = frozenset({
    "name", "binary", "help_argv", "argv_template", "optional_argv",
    "env", "cwd", "timeout_s", "stream_format", "grammar", "adapter_class",
})


def load_driver_config(name: str) -> DriverConfig:
    """Load `fixtures/native/drivers/<name>.json` into a :class:`DriverConfig`.

    The config is data, not code: §10.1 requires the two shipped drivers to be
    "loaded, not compiled in", so nothing in this module hardcodes a flag.

    ``binary`` is resolved to an absolute path **once, here**, and
    :meth:`CliDriver.build_argv` never re-searches ``PATH`` afterwards. The
    committed document records the absolute path observed on this host; if that
    path is gone (a different machine, a reinstall) the loader falls back to a
    single ``shutil.which(name)`` and raises if that also fails. A relative or
    missing ``binary`` is an error, never a bare command name handed to a shell.
    """
    path = DRIVERS_DIR() / f"{name}.json"
    if not path.is_file():
        raise ContractError(f"load_driver_config: no driver config at {path}")
    raw = _io.load_json(path)
    if not isinstance(raw, Mapping):
        raise ContractError(f"load_driver_config: {path} is not a JSON object")
    extra = set(raw) - _DRIVER_KEYS
    missing = _DRIVER_KEYS - set(raw)
    if extra or missing:
        raise ContractError(
            f"load_driver_config: {path} key mismatch; unknown={sorted(extra)!r} "
            f"missing={sorted(missing)!r}"
        )
    if raw["name"] != name:
        raise ContractError(
            f"load_driver_config: {path} declares name {raw['name']!r}, expected {name!r}"
        )

    declared_binary = raw["binary"]
    if not isinstance(declared_binary, str) or not declared_binary:
        raise ContractError(f"load_driver_config: {path} binary must be a non-empty string")
    binary = declared_binary
    if not os.path.isabs(binary) or not os.path.isfile(binary):
        # Fall back by the DECLARED binary's basename (claude / codex), never by
        # the config's name: control configs such as ``invented-flag`` and
        # ``dangerous-flag`` declare the real claude binary under a different
        # config name, and on a host where the committed absolute path is gone
        # (CI, a reinstall) they must still resolve to the same installed CLI.
        wanted = os.path.basename(declared_binary)
        found = shutil.which(wanted)
        if found is None:
            raise ContractError(
                f"load_driver_config: {name!r} binary {declared_binary!r} does not exist "
                f"and shutil.which({wanted!r}) found nothing"
            )
        binary = os.path.abspath(found)

    optional_raw = raw["optional_argv"]
    if not isinstance(optional_raw, Mapping):
        raise ContractError(f"load_driver_config: {path} optional_argv must be an object")
    optional = {str(k): tuple(str(t) for t in v) for k, v in optional_raw.items()}
    if "fresh" not in optional:
        raise ContractError(f"load_driver_config: {path} optional_argv must declare 'fresh'")

    env_raw = raw["env"]
    if not isinstance(env_raw, Mapping):
        raise ContractError(f"load_driver_config: {path} env must be an object")

    return DriverConfig(
        name=str(raw["name"]),
        binary=binary,
        help_argv=tuple(str(t) for t in raw["help_argv"]),
        argv_template=tuple(str(t) for t in raw["argv_template"]),
        optional_argv=optional,
        env={str(k): str(v) for k, v in env_raw.items()},
        cwd=str(raw["cwd"]),
        timeout_s=float(raw["timeout_s"]),
        stream_format=str(raw["stream_format"]),
        grammar=str(raw["grammar"]),
        adapter_class=AdapterClass(raw["adapter_class"]),
    )


# ---------------------------------------------------------------------------
# §3.12 — StreamGrammar. §10.2 UNKNOWN: no capture exists, so load_grammar raises.
# ---------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True, slots=True)
class JsonPathSpec:
    match: Mapping[str, Any]
    extract: Mapping[str, str]

    def matches(self, record: Mapping[str, Any]) -> bool:
        for key, want in self.match.items():
            got = _dig(record, key)
            if got is _MISSING or got != want:
                return False
        return True

    def extracted(self, record: Mapping[str, Any]) -> dict[str, Any]:
        """Only the names whose dotted path is actually present. Absent stays absent."""
        out: dict[str, Any] = {}
        for name, path in self.extract.items():
            value = _dig(record, path)
            if value is not _MISSING:
                out[name] = value
        return out


@dataclasses.dataclass(frozen=True, slots=True)
class StreamGrammar:
    name: str
    session_ack: JsonPathSpec
    turn_ack: JsonPathSpec
    usage: JsonPathSpec
    session_id_field: str
    turn_index_field: str | None


def load_grammar(name: str) -> StreamGrammar:
    """Load a `StreamGrammar` from `fixtures/native/streams/<name>.grammar.json`.

    **This raises today, by design (contract §10.2, §11.1).** The exact JSON
    field names emitted by ``claude --print --output-format stream-json`` and by
    ``codex exec --json`` are not established: no transcript of either exists in
    this repository, and producing one drives a real model, which is the
    approval-gated action of §10.6.

    Shipping guessed field names would be strictly worse than shipping nothing.
    A guessed grammar parses a real stream into silence — every ``session_ack``
    misses, every attempt's ``session_id`` stays ``None``, every usage field
    reads ``UNKNOWN`` — and the resulting run looks like a *harness that reported
    nothing* rather than like *a driver that was wrong*. The one signal that
    distinguishes the two is the absence of this file.

    *What removes this:* one approved capture per CLI on a trivial prompt,
    committed as ``fixtures/native/streams/{claude,codex}-<date>.jsonl``, with
    the grammar written **from** the capture.
    """
    raise ContractError(
        f"load_grammar({name!r}): no captured harness stream exists, so no grammar is "
        f"shipped (contract §10.2 / §11.1). {STREAMS_DIR()} deliberately contains no "
        "*.grammar.json. Settle by committing one approved capture per CLI and writing "
        "the grammar from it; a guessed grammar would be indistinguishable from a real "
        "one and would silently degrade every native run to 'harness reported nothing'."
    )


def live_group_members(pgid: int) -> frozenset[int]:
    """Live (non-zombie) pids whose process GROUP is ``pgid``.

    Distinct from :func:`protocols._live_descendant_pids`, which walks the
    parent chain: a cancel is specified against the process *group* (§10.3), and
    group membership is the relation that has to be empty. Zombies are excluded
    -- a killed-but-unreaped child is dead, and counting it would make a correct
    cancel look like a leak.

    Linux-only, like the rest of this environment. An unreadable ``/proc``
    yields an empty set; this is a witness, not a gate, and the pid-set diff in
    the tests is the independent check.
    """
    members: set[int] = set()
    try:
        entries = [name for name in os.listdir("/proc") if name.isdigit()]
    except OSError:
        return frozenset()
    for name in entries:
        try:
            stat = pathlib.Path("/proc", name, "stat").read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        tail = stat.rpartition(")")[2].split()   # comm can contain spaces and parens
        if len(tail) < 3:
            continue
        state = tail[0]
        if state == "Z":
            continue
        try:
            if int(tail[2]) == pgid:
                members.add(int(name))
        except ValueError:
            continue
    return frozenset(members)


_MISSING = object()


def _dig(record: Any, dotted: str) -> Any:
    """Walk a dotted path. Returns the ``_MISSING`` sentinel when absent.

    Deliberately never defaults an absent key to zero (no zero-default get, no or-zero): an absent telemetry
    field must stay distinguishable from a reported zero (§10.4, T30).
    """
    node: Any = record
    for part in dotted.split("."):
        if not isinstance(node, Mapping) or part not in node:
            return _MISSING
        node = node[part]
    return node


# ---------------------------------------------------------------------------
# §10.1 — flag conformance against the installed binary's own help (T25)
# ---------------------------------------------------------------------------

#: Flags that are refused whatever the installed help says. The handoff bans
#: bypass-permissions mode outright, so "the CLI supports it" is not a defence.
BANNED_FLAG_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^--dangerously-"),
    re.compile(r"^--allow-dangerously-"),
)

#: Argv **values** that select a bypass-permissions mode. The handoff bans the
#: *mode*, and neither installed CLI spells that mode as a flag: the real
#: surfaces are ``claude --permission-mode bypassPermissions`` and
#: ``codex exec --sandbox danger-full-access``. Both are ordinary values in a
#: free-text ``{slot}``, so a scan over tokens that start with ``-`` sees
#: nothing at all -- which is exactly what this table exists to fix. Compared
#: after :func:`_normalised_value`, so ``danger_full_access`` and
#: ``BypassPermissions`` are the same refusal.
BANNED_ARGV_VALUES: frozenset[str] = frozenset({
    "bypasspermissions",
    "dangerfullaccess",
})

#: What each dangerous slot IS allowed to hold. An **allowlist**, because a ban
#: list only knows the bypass names that existed when it was written: a CLI
#: upgrade that renames or adds one has to red this check rather than sail
#: through it. Values are compared literally, because the CLIs match their own
#: choices literally. An unresolved ``{placeholder}`` is not yet a value and is
#: checked where it becomes one, in :meth:`CliDriver.build_argv`.
SAFE_ARGV_VALUES: Mapping[str, frozenset[str]] = {
    "--permission-mode": frozenset({"plan", "manual", "acceptEdits"}),
    "--sandbox": frozenset({"read-only", "workspace-write"}),
}

_PLACEHOLDER_IN_TOKEN = re.compile(r"\{[a-zA-Z_][a-zA-Z0-9_]*\}")


def _normalised_value(value: str) -> str:
    """Fold case and the ``-``/``_``/space spellings of one value together."""
    return re.sub(r"[-_\s]", "", value).lower()


def _flag_value_pairs(tokens: Sequence[str]) -> Iterator[tuple[str | None, str]]:
    """Walk argv yielding ``(flag or None, value)`` for every non-flag token.

    Handles both ``--sandbox danger-full-access`` and
    ``--sandbox=danger-full-access``; a bare positional yields ``(None, value)``
    so the banned-value check still sees it.
    """
    previous: str | None = None
    for token in tokens:
        if token.startswith("-"):
            head, sep, tail = token.partition("=")
            if sep:
                yield head, tail
                previous = None
            else:
                previous = token
            continue
        yield previous, token
        previous = None


def _assert_value_allowed(flag: str | None, value: str, *, driver: str, where: str) -> None:
    """Refuse a bypass-permissions **value**, then enforce :data:`SAFE_ARGV_VALUES`.

    ``where`` names the surface, because both matter and they fail at different
    times: the shipped driver document is what a future edit touches, and the
    rendered argv is what a caller reaches at run time through a free-text slot.
    """
    if _normalised_value(value) in BANNED_ARGV_VALUES:
        subject = flag if flag is not None else "a positional argument"
        raise FlagNotSupportedError(
            f"{driver}: value {value!r} for {subject} selects bypass-permissions mode and is "
            "banned outright (no bypass-permissions mode; handoff 'Authority'), regardless "
            f"of whether the CLI supports it [{where}]",
            flag=flag if flag is not None else value, driver=driver,
        )
    if flag is None or flag not in SAFE_ARGV_VALUES:
        return
    if _PLACEHOLDER_IN_TOKEN.search(value):
        return  # not a value yet -- build_argv checks what it renders to
    allowed = SAFE_ARGV_VALUES[flag]
    if value not in allowed:
        raise FlagNotSupportedError(
            f"{driver}: {flag} value {value!r} is not on this framework's allowlist "
            f"{sorted(allowed)!r}. {flag} is a bypass surface, so it takes an allowlist and "
            "not a ban list: a CLI that renames or adds a bypass mode must red this check "
            f"instead of passing it [{where}]",
            flag=flag, driver=driver,
        )


def _assert_argv_values_allowed(tokens: Sequence[str], *, driver: str, where: str) -> None:
    for flag, value in _flag_value_pairs(tokens):
        _assert_value_allowed(flag, value, driver=driver, where=where)



def _resolve_env(config: DriverConfig, slots: Mapping[str, str]) -> dict[str, str]:
    """Resolve `config.env`'s `{slot}` placeholders. `os.environ` is never inherited."""
    resolved: dict[str, str] = {}
    for key, template in config.env.items():
        value = template
        for match in re.findall(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", template):
            if match not in slots:
                raise ContractError(
                    f"{config.name}: env[{key!r}] needs slot {match!r}, which was not supplied"
                )
            value = value.replace("{" + match + "}", str(slots[match]))
        # A resolved env value is a third way into the same mode (an exported
        # CLAUDE_PERMISSION_MODE, say), so it takes the same ban.
        _assert_value_allowed(
            None, value, driver=config.name, where=f"resolved env[{key!r}]",
        )
        resolved[key] = value
    return resolved


class FlagNotSupportedError(FlagNotSupported):
    """`contract.FlagNotSupported` carrying `flag=`/`driver=` as §10.1 requires.

    ``contract.FlagNotSupported`` is a bare ``ContractError`` subclass with no
    attributes, and §10.1 specifies ``FlagNotSupported(flag=..., driver=...)``.
    ``contract.py`` is core-owned and frozen, so this lane cannot add the
    attributes there. This subclass carries them, and ``except FlagNotSupported``
    (or ``except ContractError``) still catches it.
    """

    def __init__(self, message: str, *, flag: str, driver: str) -> None:
        self.flag = flag
        self.driver = driver
        super().__init__(message)


def installed_help(config: DriverConfig) -> str:
    """Run ``binary + help_argv`` and return stdout+stderr. No model call.

    The environment is the driver's own allowlist with every placeholder pointed
    at a throwaway directory, so printing help cannot read or write the real
    ``$HOME``. This is a real subprocess of an installed CLI, which the offline
    rules explicitly allow.
    """
    import tempfile

    with tempfile.TemporaryDirectory(prefix="agentic-help-") as scratch:
        slots = {
            "home": scratch, "workspace": scratch, "plugin_root": scratch,
            "extra_dir": scratch, "codex_home": scratch,
        }
        env = _resolve_env(config, slots)
        try:
            proc = subprocess.run(
                [config.binary, *config.help_argv],
                cwd=scratch, env=env, capture_output=True, text=True, timeout=120,
                stdin=subprocess.DEVNULL,
            )
        except FileNotFoundError as exc:
            raise ContractError(
                f"installed_help: {config.binary!r} is not executable on this host"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise ContractError(f"installed_help: {config.binary!r} --help timed out") from exc
    return (proc.stdout or "") + "\n" + (proc.stderr or "")


def declared_flags(config: DriverConfig) -> tuple[str, ...]:
    """Every token the driver could emit that starts with ``-``, in first-seen order.

    Covers ``argv_template`` **and every value of** ``optional_argv`` (§10.1):
    a flag that only appears on the resume or fork path is exactly as capable of
    being silently ignored by the CLI as one on the fresh path.
    """
    seen: dict[str, None] = {}
    streams: list[Sequence[str]] = [config.argv_template]
    streams.extend(config.optional_argv[mode] for mode in sorted(config.optional_argv))
    for tokens in streams:
        for token in tokens:
            if token.startswith("-") and token not in seen:
                seen[token] = None
    return tuple(seen)


def _whole_word_present(flag: str, help_text: str) -> bool:
    return re.search(rf"(?<![\w-]){re.escape(flag)}(?![\w-])", help_text) is not None


def assert_flags_supported(config: DriverConfig) -> None:
    """T25. Refuse any flag the installed binary's own help does not list.

    Three refusals, in this order:

    * a ``--dangerously-*`` / ``--allow-dangerously-*`` flag is refused
      unconditionally, *before* the help is even consulted — the handoff bans
      bypass-permissions mode, and the CLI supporting it is not a defence;
    * a banned **value** is refused on the same terms. The ban is on the mode,
      not on a spelling, and neither installed CLI spells the mode as a flag:
      ``claude --permission-mode bypassPermissions`` and ``codex exec --sandbox
      danger-full-access`` are both ordinary values, invisible to any scan that
      only looks at tokens beginning with ``-``. Where a slot is a known bypass
      surface, :data:`SAFE_ARGV_VALUES` allowlists it instead;
    * every remaining ``-``-leading token must appear as a whole word in
      ``binary + help_argv`` output. The list is derived from the installed
      binary on every call; there is no table of known flags in this source, so
      a CLI upgrade that drops a flag reds this check instead of producing argv
      the CLI silently ignores.

    The value refusal covers what the *config document* hardcodes. A value that
    arrives through a ``{slot}`` at call time is covered by the identical check
    in :meth:`CliDriver.build_argv`, so neither surface can be reached without
    passing one of them.
    """
    for flag in declared_flags(config):
        for pattern in BANNED_FLAG_PATTERNS:
            if pattern.search(flag):
                raise FlagNotSupportedError(
                    f"{config.name}: flag {flag!r} is banned outright (no bypass-permissions "
                    "mode; handoff 'Authority'), regardless of whether the CLI supports it",
                    flag=flag, driver=config.name,
                )
    for mode_tokens in (
        config.argv_template,
        *(config.optional_argv[mode] for mode in sorted(config.optional_argv)),
    ):
        _assert_argv_values_allowed(
            mode_tokens, driver=config.name, where=f"{config.name}.json",
        )
    for key, value in config.env.items():
        _assert_value_allowed(
            None, value, driver=config.name, where=f"{config.name}.json env[{key!r}]",
        )
    help_text = installed_help(config)
    for flag in declared_flags(config):
        if not _whole_word_present(flag, help_text):
            raise FlagNotSupportedError(
                f"{config.name}: flag {flag!r} does not appear in the installed "
                f"{config.binary} {' '.join(config.help_argv)} output",
                flag=flag, driver=config.name,
            )


# ---------------------------------------------------------------------------
# §3.12 — CliDriver
# ---------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True, slots=True)
class PlannedInvocation:
    argv: tuple[str, ...]
    env: Mapping[str, str]
    cwd: str
    timeout_s: float
    adapter_class: AdapterClass


_PLACEHOLDER = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


class CliDriver:
    """Builds real argv for an installed CLI. Spawns nothing without approval."""

    def __init__(self, config: DriverConfig, *, manifest: Manifest | None = None) -> None:
        """`manifest` is the run manifest whose `approvals` gate :meth:`spawn` (§10.6).

        Keyword-only and defaulted, so the §3.12 signature ``CliDriver(config)``
        still constructs. Without a manifest there are no approvals, so
        :meth:`spawn` can only raise — which is the correct offline default.
        """
        self._config = config
        self._manifest = manifest

    @property
    def config(self) -> DriverConfig:
        return self._config

    @property
    def manifest(self) -> Manifest | None:
        return self._manifest

    def build_argv(self, *, mode: str = "fresh", **slots: str | None) -> list[str]:
        """Pure. Never spawns.

        ``mode`` selects one entry of ``config.optional_argv`` and appends its
        tokens. A ``{slot}`` whose value is ``None`` drops its token *and* the
        immediately preceding token when that token starts with ``-`` — that is
        how an inapplicable flag is omitted rather than handed the literal
        string ``"n/a"`` (benchmark-spec §2 defines effort as "n/a where the
        harness has none", which is a *report* value, not a CLI argument).

        The **rendered** argv is checked against :data:`BANNED_ARGV_VALUES` and
        :data:`SAFE_ARGV_VALUES` before it is returned. ``assert_flags_supported``
        can only see what the config document hardcodes; ``permission_mode`` and
        ``sandbox`` are free-text slots, so ``bypassPermissions`` and
        ``danger-full-access`` reach argv without passing through the config at
        all. This is the check that sees them, and it is on the path every
        caller uses -- :meth:`dry_run` and :meth:`spawn` both build argv here.
        """
        if mode not in self._config.optional_argv:
            raise ContractError(
                f"{self._config.name}: unknown mode {mode!r}; "
                f"declared modes are {self._config.modes()!r}"
            )
        tokens = [*self._config.argv_template, *self._config.optional_argv[mode]]

        needed: set[str] = set()
        for token in tokens:
            needed.update(_PLACEHOLDER.findall(token))
        # `env` and `cwd` are part of the same invocation and take the same
        # slots, so a slot only they consume is used, not ignored.
        elsewhere: set[str] = set(_PLACEHOLDER.findall(self._config.cwd))
        for value in self._config.env.values():
            elsewhere.update(_PLACEHOLDER.findall(value))
        unknown = set(slots) - needed - elsewhere
        if unknown:
            raise ContractError(
                f"{self._config.name}: slot(s) {sorted(unknown)!r} are used by neither the "
                f"argv of mode {mode!r} nor env/cwd; refusing to silently ignore them"
            )
        absent = needed - set(slots)
        if absent:
            raise ContractError(
                f"{self._config.name}: mode {mode!r} needs slot(s) {sorted(absent)!r}"
            )

        out: list[str] = [self._config.binary]
        for token in tokens:
            names = _PLACEHOLDER.findall(token)
            if names and any(slots[n] is None for n in names):
                # Drop this token, and the flag it belongs to.
                if len(out) > 1 and out[-1].startswith("-"):
                    out.pop()
                continue
            rendered = token
            for name in names:
                rendered = rendered.replace("{" + name + "}", str(slots[name]))
            out.append(rendered)
        _assert_argv_values_allowed(
            out[1:], driver=self._config.name, where=f"rendered argv (mode {mode!r})",
        )
        return out

    def dry_run(self, *, mode: str = "fresh", **slots: str | None) -> PlannedInvocation:
        """Plan the invocation without spawning anything."""
        argv = self.build_argv(mode=mode, **slots)
        env_slots = {k: str(v) for k, v in slots.items() if v is not None}
        cwd = self._config.cwd
        for name in _PLACEHOLDER.findall(cwd):
            if name not in env_slots:
                raise ContractError(f"{self._config.name}: cwd needs slot {name!r}")
            cwd = cwd.replace("{" + name + "}", env_slots[name])
        return PlannedInvocation(
            argv=tuple(argv),
            env=_resolve_env(self._config, env_slots),
            cwd=cwd,
            timeout_s=self._config.timeout_s,
            adapter_class=self._config.adapter_class,
        )

    def spawn(
        self,
        *,
        approval_token: str | None = None,
        mode: str = "fresh",
        ledger: "HostLedger | None" = None,
        **slots: str | None,
    ) -> "HarnessSession":
        """Drive a real harness. §10.6: refuses without an approved token.

        The approval check runs **first**, before argv is built and before
        anything in :mod:`subprocess` is touched, so an unapproved call cannot
        leave a process behind even transiently. There is no default token, no
        environment-variable fallback and no ``--yes``.
        """
        token = approval_token
        if not isinstance(token, str) or not token:
            raise ApprovalRequired(
                f"{self._config.name}: spawn() needs a non-empty approval_token; driving a "
                "real harness is an approval-gated action (contract §10.6). Use dry_run() "
                "for the offline path."
            )
        approvals = tuple(self._manifest.approvals) if self._manifest is not None else ()
        if token not in approvals:
            raise ApprovalRequired(
                f"{self._config.name}: approval token id {token!r} is not in "
                f"Manifest.approvals ({list(approvals)!r}); obtaining one is a human action "
                "outside this codebase (contract §10.6)"
            )
        if ledger is None or ledger.witness is not SignatureClass.HOST_OBSERVED:
            raise EvidencePromotionRefused(
                f"{self._config.name}: a native spawn must write to a HostLedger constructed "
                "witness=HOST_OBSERVED; nothing else can produce native provenance "
                "(contract §10.5)"
            )
        raise ApprovalRequired(  # pragma: no cover - unreachable without an approved run
            f"{self._config.name}: an approved native spawn path is not wired in this "
            "change. §10.2's stream grammar is UNKNOWN, so a spawned session could not be "
            "parsed into acks and would produce an attempt with session_id=None that can "
            "never be NATIVE_PROVEN anyway. Land one approved capture first."
        )


def dry_run(name: str, *, mode: str = "fresh", **slots: str | None) -> str:
    """Render the planned invocation for driver ``name`` as text. Spawns nothing.

    This is what ``run.py driver --dry-run --name <n>`` (integration lane, §8.5)
    prints. It is exposed here as a function so the adapter lane's acceptance is
    provable without the integration lane's CLI existing yet.

    REPAIR N-11: :func:`assert_flags_supported` runs **before** a single argv
    token is rendered, against the *installed* binary's own help. Without it
    this function printed a plausible, copy-pasteable command line for a CLI
    that may have dropped or renamed one of the flags in it -- a plausible
    argv is exactly the artifact a reader trusts, and only T25's unit test
    would have noticed the drift. There is no flag, environment variable or
    keyword that skips the check: an unvalidatable driver (binary absent,
    ``--help`` timing out) is a *refusal*, not a dry run rendered anyway,
    because "we could not check" and "we checked and it is fine" must not
    print the same thing.
    """
    config = load_driver_config(name)
    assert_flags_supported(config)
    driver = CliDriver(config)
    planned = driver.dry_run(mode=mode, **(slots or _DEFAULT_SLOTS[name][mode]))
    lines = [
        f"flags: validated against the installed "
        f"{config.binary} {' '.join(config.help_argv)} output",
        f"driver={config.name} mode={mode}",
        f"argv: {' '.join(planned.argv)}",
        f"cwd={planned.cwd} timeout_s={planned.timeout_s}",
        f"adapter_class={planned.adapter_class.value} (NOT SPAWNED — no approval token)",
    ]
    return "\n".join(lines)


#: Placeholder values used only to render a dry run. They are obviously-fake
#: paths, never a real workspace, and nothing consumes them. The two bypass
#: surfaces are the exception and are deliberately REAL, safe values
#: (``sandbox: "read-only"``, ``permission_mode: "plan"``): they are checked
#: against SAFE_ARGV_VALUES like any other rendered value, and a dry run that
#: had to be exempted from that check would be a dry run of a different argv
#: than the one a real spawn builds.
_DEFAULT_SLOTS: Mapping[str, Mapping[str, dict[str, str | None]]] = {
    "claude": {
        "fresh": {
            "model": "<model-id>", "effort": "<effort>",
            "session_id": "00000000-0000-4000-8000-000000000000",
            "permission_mode": "plan", "allowed_tools": "<allowed-tools>",
            "workspace": "<workspace>", "system_append": "<system-append>",
            "mcp_config": "<mcp-config.json>", "home": "<home>",
            "plugin_root": "<plugin-root>",
        },
        "resume": {
            "model": "<model-id>", "effort": "<effort>",
            "session_id": "00000000-0000-4000-8000-000000000000",
            "permission_mode": "plan", "allowed_tools": "<allowed-tools>",
            "workspace": "<workspace>", "system_append": "<system-append>",
            "mcp_config": "<mcp-config.json>", "home": "<home>",
            "plugin_root": "<plugin-root>",
        },
        "fork": {
            "model": "<model-id>", "effort": "<effort>",
            "session_id": "00000000-0000-4000-8000-000000000000",
            "permission_mode": "plan", "allowed_tools": "<allowed-tools>",
            "workspace": "<workspace>", "system_append": "<system-append>",
            "mcp_config": "<mcp-config.json>", "home": "<home>",
            "plugin_root": "<plugin-root>",
        },
    },
    "codex": {
        "fresh": {
            "sandbox": "read-only", "workspace": "<workspace>", "extra_dir": "<extra-dir>",
            "model": "<model-id>", "last_message_path": "<last-message.txt>",
            "home": "<home>",
        },
        "resume": {
            "sandbox": "read-only", "workspace": "<workspace>", "extra_dir": "<extra-dir>",
            "model": "<model-id>", "last_message_path": "<last-message.txt>",
            "home": "<home>",
        },
        "fork": {
            "sandbox": "read-only", "workspace": "<workspace>", "extra_dir": "<extra-dir>",
            "model": "<model-id>", "last_message_path": "<last-message.txt>",
            "home": "<home>",
            "session_id": "00000000-0000-4000-8000-000000000000",
        },
    },
}


# ---------------------------------------------------------------------------
# §5 — the host ledger
# ---------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True, slots=True)
class ChainVerification:
    ok: bool
    first_bad_index: int | None
    reason: str | None
    host_observed: int
    caller_asserted: int
    events: int


def _body_of(record: Mapping[str, Any]) -> dict[str, Any]:
    """§5.2: the event dict with ``sha256`` and ``host_signature.value`` removed."""
    body = {k: v for k, v in record.items() if k != "sha256"}
    sig = body.get("host_signature")
    if isinstance(sig, Mapping):
        body["host_signature"] = {k: v for k, v in sig.items() if k != "value"}
    return body


def _chain_message(prev_hash: str, body: Mapping[str, Any]) -> bytes:
    return prev_hash.encode("ascii") + b"\n" + canonical_json(body)


class _RunKey:
    """A *capability* to verify one ledger — not a key anyone may supply.

    Minted only inside :meth:`HostLedger.__init__`, for a ``HOST_OBSERVED``
    ledger, and reachable only through :attr:`HostLedger.key` and
    :meth:`HostLedger.verifier`. There is no public constructor, no accessor for
    the bytes, and ``repr`` redacts.

    It binds three things together, and the binding is the point:

    * the run's HMAC key,
    * the run id,
    * the **resolved path of the ledger the key was minted for**.

    The path binding is what makes "mint a throwaway host ledger, take its key,
    and verify a hand-typed file with it" fail as well: a capability over run
    A's ledger is not a capability over any other file.

    Before this existed, ``LedgerReader(path, key=<bytes>)`` took the key as an
    ordinary argument, so whoever chose the key *was* the host: a hand-typed
    ledger signed under an attacker-chosen key satisfied ``verify_chain()``,
    ``is_verified()``, ``host_observed_session_ids()`` and therefore
    ``contract.assert_native_backed``, with no source edit and no access to the
    real run key. §5.3's "a verifier without the key cannot forge, and cannot
    bless" only holds when the key cannot be supplied from outside.
    """

    __slots__ = ("__key", "__run_id", "__ledger_path")

    def __init__(self, key: bytes, run_id: str, ledger_path: pathlib.Path) -> None:
        self.__key = bytes(key)
        self.__run_id = str(run_id)
        self.__ledger_path = pathlib.Path(ledger_path).resolve()

    @property
    def run_id(self) -> str:
        return self.__run_id

    @property
    def ledger_path(self) -> pathlib.Path:
        return self.__ledger_path

    def mac(self, message: bytes) -> str:
        """The only use of the key bytes anywhere outside :class:`HostLedger`."""
        return hmac.new(self.__key, message, sha256).hexdigest()

    def covers(self, path: pathlib.Path) -> bool:
        return pathlib.Path(path).resolve() == self.__ledger_path

    def __repr__(self) -> str:
        return (
            f"<_RunKey run_id={self.__run_id!r} "
            f"ledger={self.__ledger_path.name!r} key=REDACTED>"
        )


def _run_key_bytes(run_key: _RunKey) -> bytes:
    """The raw key behind a capability. Deliberately module-private.

    Exists for exactly one assertion — that the key bytes never appear in the
    ledger file — and for nothing else. Reaching for it is reaching into this
    module's private state, which is the access class §5.3 already concedes.
    """
    return getattr(run_key, "_RunKey__key")


def _sealed_signer(
    witness: SignatureClass, key: bytes | None, key_id: str
) -> tuple[Any, Any]:
    """Close over the witness and the key so no attribute holds either one.

    Returns ``(stamp, witness_of)``. ``stamp(None)`` is the signature block as it
    appears in the hashed *body*; ``stamp(message)`` is the block as it appears in
    the written record. Neither reads ``self``, so :meth:`HostLedger.append` has
    nothing left to re-read per call — which is what makes "the witness is fixed
    at construction" a property of the object graph rather than of a docstring.
    """
    if witness is SignatureClass.HOST_OBSERVED:
        assert key is not None
        base: dict[str, Any] = {
            "value_class": witness.value, "algo": "hmac-sha256", "key_id": key_id,
        }

        def stamp(message: bytes | None = None) -> dict[str, Any]:
            if message is None:
                return dict(base)
            return dict(base) | {"value": hmac.new(key, message, sha256).hexdigest()}
    else:
        base = {"value_class": witness.value, "algo": "none", "key_id": None}

        def stamp(message: bytes | None = None) -> dict[str, Any]:
            if message is None:
                return dict(base)
            return dict(base) | {"value": None}

    def witness_of() -> SignatureClass:
        return witness

    return stamp, witness_of


#: The only attributes a sealed :class:`HostLedger` may still rebind: its write
#: cursor. Everything that decides *what an entry means* is sealed.
_MUTABLE_LEDGER_ATTRS: frozenset[str] = frozenset(
    {"_index", "_last_hash", "_fd", "_closed"}
)


class HostLedger:
    """Append-only, hash-chained event ledger (§5.1, §5.2).

    ``witness`` is the ledger's identity and is **sealed** at construction:

    * ``HOST_OBSERVED`` — the host itself witnessed the facts. It mints a
      32-byte run-scoped HMAC key with :func:`secrets.token_bytes` and **refuses
      a caller-supplied key**. The key lives in memory only; ``key_id`` names it,
      the ledger never contains it, and the only way to hand it to a verifier is
      :meth:`verifier` (or the :attr:`key` capability it wraps).
    * ``CALLER_ASSERTED`` — the fact was reported by the thing under test. Every
      entry is ``algo: "none"``, ``value: null``. Recorded, zero provenance
      weight. It refuses a key too: a ledger that signs nothing has no use for
      one, and a key it accepted could only ever be used to launder it.

    ``value_class`` is *derived* from ``witness`` on every append. It is not a
    parameter and there is no per-call override; that is the mechanism, not the
    convention, behind ground rule 3 (§10.5 item 3).

    "Sealed" is literal, and it is two independent mechanisms:

    1. The witness and the key live in a **closure** (:func:`_sealed_signer`),
       not in an attribute. :meth:`append` calls that closure and re-reads
       nothing per call, so there is no ``self._witness`` for a later assignment
       to change.
    2. ``__slots__`` plus :meth:`__setattr__` refuse to rebind anything but the
       write cursor once ``__init__`` returns, raising
       :class:`~evals.agentic.framework.contract.EvidencePromotionRefused`.

    Both exist because either alone is thin: before them,
    ``ledger._witness = SignatureClass.HOST_OBSERVED; ledger._key = <bytes>``
    turned a legally-constructed replay ledger into a host-observed one on the
    next ``append()``, with no source edit at all — strictly cheaper than the
    ``adapters.py`` patch counterfeit fixture 23(b) models.
    """

    __slots__ = (
        "_path", "_run_id", "_key_id", "_run_key", "_stamp", "_witness_of",
        "_index", "_last_hash", "_fd", "_closed", "_sealed",
    )

    def __init__(
        self,
        path: pathlib.Path,
        *,
        run_id: str,
        witness: SignatureClass,
        key: bytes | None = None,
    ) -> None:
        object.__setattr__(self, "_sealed", False)
        if not isinstance(witness, SignatureClass):
            raise ContractError(f"HostLedger: witness must be a SignatureClass, got {witness!r}")
        self._path = pathlib.Path(path)
        self._run_id = run_id
        self._key_id = f"run-{run_id}"

        minted: bytes | None
        if witness is SignatureClass.HOST_OBSERVED:
            if key is not None:
                raise EvidencePromotionRefused(
                    "HostLedger(witness=HOST_OBSERVED): a caller-supplied key is refused. "
                    "The signing key is the whole difference between 'the host saw it' and "
                    "'someone with the key said so'; a host-observed ledger mints its own "
                    "(contract §3.12, §10.5)."
                )
            minted = secrets.token_bytes(32)
            self._run_key: _RunKey | None = _RunKey(minted, run_id, self._path)
        else:
            if key is not None:
                raise EvidencePromotionRefused(
                    "HostLedger(witness=CALLER_ASSERTED): a key is refused. A caller-asserted "
                    "ledger signs nothing (algo 'none', value null), so the only thing a key "
                    "it accepted could ever do is launder it into a host-observed one "
                    "(contract §3.12, §10.5)."
                )
            minted = None
            self._run_key = None

        stamp, witness_of = _sealed_signer(witness, minted, self._key_id)
        self._stamp = stamp
        self._witness_of = witness_of
        del minted  # from here on the bytes exist only in the closure and the _RunKey

        self._path.parent.mkdir(parents=True, exist_ok=True)
        existing = list(_io.read_jsonl(self._path)) if self._path.exists() else []
        self._index = len(existing)
        self._last_hash = existing[-1]["sha256"] if existing else "0" * 64
        # §5.1: the host holds the only writer handle for the run's lifetime.
        self._fd: int | None = os.open(
            self._path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600
        )
        self._closed = False
        object.__setattr__(self, "_sealed", True)

    # -- the seal -----------------------------------------------------------
    def __setattr__(self, name: str, value: Any) -> None:
        if self._sealed and name not in _MUTABLE_LEDGER_ATTRS:
            raise EvidencePromotionRefused(
                f"HostLedger.{name}: the witness and the signing key are sealed at "
                "construction and cannot be rebound. Flipping them on a live ledger would "
                "launder a caller-asserted replay into host-observed entries with no source "
                "edit at all, which is the cheapest forgery there is (contract §10.5 item 3). "
                "A ledger with a different witness is a different ledger: construct one."
            )
        object.__setattr__(self, name, value)

    def __delattr__(self, name: str) -> None:
        raise EvidencePromotionRefused(
            f"HostLedger.{name}: sealed at construction; deleting it is the same forgery as "
            "rebinding it (contract §10.5 item 3)."
        )

    # -- identity -----------------------------------------------------------
    @property
    def witness(self) -> SignatureClass:
        """Read out of the sealed closure, never out of an attribute."""
        return self._witness_of()

    @property
    def path(self) -> pathlib.Path:
        return self._path

    @property
    def run_id(self) -> str:
        return self._run_id

    @property
    def last_hash(self) -> str:
        return self._last_hash

    @property
    def key(self) -> "_RunKey | None":
        """The run's verification **capability**, or ``None`` when nothing was signed.

        Not part of §3.12's listed surface but unavoidable: §5.3 says a verifier
        without the key "cannot forge, and cannot bless", so the host must be
        able to pass verification authority to its own reader without it ever
        reaching disk. What it hands over is a :class:`_RunKey` bound to *this*
        ledger's path — not raw bytes, which anyone could have chosen.
        """
        return self._run_key

    def verifier(self) -> "LedgerReader":
        """The only reader that can bless this ledger. Blesses nothing else.

        ``HostLedger(...).verifier()`` is the whole cross-process story too: a
        later process cannot obtain one, so it reads the chain and reports
        ``LedgerReader.UNVERIFIABLE_IN_THIS_PROCESS`` rather than a verdict it
        has no standing to give.
        """
        return LedgerReader(self._path, key=self._run_key)

    # -- write --------------------------------------------------------------
    def append(
        self,
        kind: EventKind,
        *,
        attempt_id: str | None,
        session_id: str | None,
        payload: Mapping[str, Any],
    ) -> Event:
        if self._closed or self._fd is None:
            raise ContractError("HostLedger.append: the ledger is closed")
        if not isinstance(kind, EventKind):
            raise ContractError(f"HostLedger.append: kind must be an EventKind, got {kind!r}")

        prev_hash = self._last_hash
        body: dict[str, Any] = {
            "index": self._index,
            "event_id": str(uuid.uuid4()),
            "run_id": self._run_id,
            "attempt_id": attempt_id,
            "session_id": session_id,
            "kind": kind.value,
            "at": now_rfc3339(),
            "payload": dict(payload),
            "prev_hash": prev_hash,
            # The sealed closure decides value_class. There is no self._witness.
            "host_signature": self._stamp(None),
        }
        message = _chain_message(prev_hash, body)
        record = dict(body)
        record["sha256"] = sha256(message).hexdigest()
        record["host_signature"] = self._stamp(message)

        line = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        os.write(self._fd, (line + "\n").encode("utf-8"))
        self._index += 1
        self._last_hash = record["sha256"]
        return Event.from_dict(record)

    def close(self) -> None:
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None
        self._closed = True

    def __enter__(self) -> "HostLedger":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


@dataclasses.dataclass(frozen=True, slots=True)
class SpawnAccounting:
    """REPAIR S-10: what :meth:`LedgerReader.spawn_exit_accounting` found.

    ``spawned``/``exited`` are attempt ids in ledger order, deduplicated.
    ``unattributed`` counts SPAWN/EXIT entries with no ``attempt_id`` -- they
    are reported, never silently dropped.
    """

    spawned: tuple[str, ...]
    exited: tuple[str, ...]
    spawned_without_exit: tuple[str, ...]
    exited_without_spawn: tuple[str, ...]
    unattributed: int

    def missing_from(self, recorded_attempt_ids: "frozenset[str] | set[str]") -> tuple[str, ...]:
        """Spawned attempt ids that the attempt ledger never recorded."""
        return tuple(a for a in self.spawned if a not in recorded_attempt_ids)

    def to_dict(self) -> dict[str, Any]:
        return {
            "spawned": list(self.spawned),
            "exited": list(self.exited),
            "spawned_without_exit": list(self.spawned_without_exit),
            "exited_without_spawn": list(self.exited_without_spawn),
            "unattributed": self.unattributed,
        }


class LedgerReader:
    """Reads and verifies a ledger. Implements `contract.LedgerView`.

    ``key`` is a :class:`_RunKey` **capability** or ``None``. It is not bytes,
    and raw bytes are refused: whoever picks the key is the host, so a key taken
    as an ordinary argument let a hand-typed ledger verify against itself. The
    only ways to obtain a capability are :meth:`HostLedger.verifier` and
    :attr:`HostLedger.key`, both of which exist only inside the process that
    minted the run key.

    A reader without one is not broken — it is the honest state of every reader
    outside that process. It re-walks the hash chain, reports every tamper class,
    and refuses to bless, naming :data:`UNVERIFIABLE_IN_THIS_PROCESS` as the
    reason.
    """

    #: The reason a reader with no capability gives. §5.3's "cannot forge, and
    #: cannot bless", and the sentence a cross-process report must print.
    UNVERIFIABLE_IN_THIS_PROCESS = "unverifiable in this process (no run key)"

    def __init__(self, path: pathlib.Path, *, key: "_RunKey | None") -> None:
        self._path = pathlib.Path(path)
        if key is None:
            self._run_key: _RunKey | None = None
        elif isinstance(key, _RunKey):
            if not key.covers(self._path):
                raise EvidencePromotionRefused(
                    f"LedgerReader: this run key was minted for {key.ledger_path}, so it "
                    f"cannot verify {pathlib.Path(self._path).resolve()}. A capability over "
                    "one run's ledger is not a capability over another file -- otherwise "
                    "'mint a throwaway host ledger and reuse its key' would be a forgery "
                    "path (contract §5.3)."
                )
            self._run_key = key
        else:
            raise EvidencePromotionRefused(
                "LedgerReader: a raw key is refused. Whoever chooses the key IS the host, so "
                "a caller-supplied one lets a hand-typed ledger verify against itself: an "
                "intact chain, a passing HMAC, host_observed_session_ids() populated, and "
                "contract.assert_native_backed waved through, with no source edit and no "
                "access to any real run key. Verification authority comes from "
                "HostLedger.verifier() (or LedgerReader(path, key=host_ledger.key)), which "
                "only the process that minted the run key can produce (contract §5.3, §10.5)."
            )
        self._records: tuple[dict[str, Any], ...] = tuple(_io.read_jsonl(self._path))

    @property
    def path(self) -> pathlib.Path:
        return self._path

    def records(self) -> tuple[dict[str, Any], ...]:
        return self._records

    def events(self) -> tuple[Event, ...]:
        return tuple(Event.from_dict(r) for r in self._records)

    # -- §5.2 chain ---------------------------------------------------------
    def verify_chain(self) -> ChainVerification:
        """Re-walk from index 0; return the FIRST bad index and its tamper class."""
        host_observed = 0
        caller_asserted = 0
        prev = "0" * 64
        first_bad: int | None = None
        reason: str | None = None

        for position, record in enumerate(self._records):
            sig = record.get("host_signature")
            value_class = sig.get("value_class") if isinstance(sig, Mapping) else None
            if value_class == SignatureClass.HOST_OBSERVED.value:
                host_observed += 1
            elif value_class == SignatureClass.CALLER_ASSERTED.value:
                caller_asserted += 1

            if first_bad is not None:
                continue

            body = _body_of(record)
            recomputed = sha256(_chain_message(record.get("prev_hash", ""), body)).hexdigest()
            if recomputed != record.get("sha256"):
                first_bad, reason = position, "edited-field"
                continue
            if record.get("prev_hash") != prev:
                first_bad, reason = position, self._link_break_class(position)
                continue
            if record.get("index") != position:
                first_bad, reason = position, "deleted-entry"
                continue
            prev = record["sha256"]

        return ChainVerification(
            ok=first_bad is None,
            first_bad_index=first_bad,
            reason=reason,
            host_observed=host_observed,
            caller_asserted=caller_asserted,
            events=len(self._records),
        )

    def _link_break_class(self, position: int) -> str:
        """Name the tamper class for a broken ``prev_hash`` link at ``position``.

        The three shapes are told apart by the *declared* indices around the
        break, because all three leave a valid own-hash:

        * ``swapped-pair`` — this entry declares ``position+1`` and the next
          declares ``position``. Checked first: a swap also looks like a gap if
          only this entry is examined.
        * ``deleted-entry`` — this entry declares an index beyond ``position``
          with no matching entry behind it: the chain skipped one.
        * ``inserted-entry`` — indices are consistent, so nothing was removed;
          something was spliced in whose own hash was recomputed but whose
          ``prev_hash`` does not match the real predecessor.
        """
        declared = self._records[position].get("index")
        following = (
            self._records[position + 1].get("index")
            if position + 1 < len(self._records) else None
        )
        if declared == position + 1 and following == position:
            return "swapped-pair"
        if isinstance(declared, int) and declared > position:
            return "deleted-entry"
        return "inserted-entry"

    # -- §5.3 signatures ----------------------------------------------------
    def _signature_ok(self, record: Mapping[str, Any]) -> bool:
        sig = record.get("host_signature")
        if not isinstance(sig, Mapping):
            return False
        if sig.get("value_class") != SignatureClass.HOST_OBSERVED.value:
            return True  # caller-asserted entries carry no signature to check
        if self._run_key is None:
            return False
        expected = self._run_key.mac(
            _chain_message(record.get("prev_hash", ""), _body_of(record))
        )
        got = sig.get("value")
        return isinstance(got, str) and hmac.compare_digest(expected, got)

    def verification_reason(self) -> str | None:
        """Why this ledger cannot bless a native claim, or ``None`` when it can.

        Four refusals, and the third is the one a chain-plus-key check misses:

        1. the chain is broken;
        2. this reader holds no run-key capability
           (:data:`UNVERIFIABLE_IN_THIS_PROCESS`);
        3. **the host witnessed nothing**. Every entry is caller-asserted, so
           ``_signature_ok`` short-circuits ``True`` for all of them and the key
           is never actually used. "Verified" would then mean no more than "this
           replay's chain is intact", which is precisely the sentence §5.4 exists
           to keep out of a report;
        4. a host-observed entry's HMAC does not check out.
        """
        chain = self.verify_chain()
        if not chain.ok:
            return f"chain broken at index {chain.first_bad_index} ({chain.reason})"
        if self._run_key is None:
            return self.UNVERIFIABLE_IN_THIS_PROCESS
        if chain.host_observed == 0:
            return (
                "no host-observed entries: the host witnessed nothing in this ledger, so "
                "there is nothing here to bless"
            )
        if not all(self._signature_ok(r) for r in self._records):
            return "a host-observed entry's HMAC does not check out"
        return None

    def is_verified(self) -> bool:
        """True only when :meth:`verification_reason` finds nothing to refuse.

        A reader without the capability can verify the hash chain but can never
        *bless* a native claim (§5.3) — and neither can a reader whose ledger
        holds no host-observed entry at all.
        """
        return self.verification_reason() is None

    # -- contract.LedgerView ------------------------------------------------
    def has_event(self, event_id: str) -> bool:
        return any(r.get("event_id") == event_id for r in self._records)

    def session_ids(self) -> frozenset[str]:
        """Every session id in the ledger. A header statistic, never the gate."""
        return frozenset(
            r["session_id"] for r in self._records
            if isinstance(r.get("session_id"), str)
        )

    def host_observed_session_ids(self) -> frozenset[str]:
        """Ids carried by a SESSION_ACK whose signature is host-observed (§5.4 clause 4)."""
        out: set[str] = set()
        for record in self._records:
            if record.get("kind") != EventKind.SESSION_ACK.value:
                continue
            sig = record.get("host_signature")
            if not isinstance(sig, Mapping):
                continue
            if sig.get("value_class") != SignatureClass.HOST_OBSERVED.value:
                continue
            if not self._signature_ok(record):
                continue
            sid = record.get("session_id")
            if isinstance(sid, str):
                out.add(sid)
        return frozenset(out)

    def signature_class(self, event_id: str) -> SignatureClass | None:
        for record in self._records:
            if record.get("event_id") != event_id:
                continue
            sig = record.get("host_signature")
            if not isinstance(sig, Mapping):
                return None
            raw = sig.get("value_class")
            if raw is None:
                return None
            klass = SignatureClass(raw)
            if klass is SignatureClass.HOST_OBSERVED and not self._signature_ok(record):
                # A host-observed claim whose HMAC does not check out is not
                # host-observed. Downgrading rather than raising keeps
                # assert_native_backed's refusal the single decision point.
                return SignatureClass.CALLER_ASSERTED
            return klass
        return None

    # -- REPAIR S-10: SPAWN/EXIT enumeration ---------------------------------
    def events_of_kind(self, kind: EventKind) -> tuple[dict[str, Any], ...]:
        """Every raw record whose ``kind`` is ``kind``, in ledger order.

        An ADDITIVE reader capability (contract §2.4 already documents
        ``records()`` as an optional sixth ``LedgerView`` method probed with
        ``getattr``; this follows the same pattern and changes no existing
        signature). ``records()`` alone forces every consumer to re-implement
        the kind filter and the ``EventKind`` value mapping.
        """
        if not isinstance(kind, EventKind):
            raise ContractError(f"events_of_kind: kind must be an EventKind, got {kind!r}")
        return tuple(r for r in self._records if r.get("kind") == kind.value)

    def spawn_exit_accounting(self) -> "SpawnAccounting":
        """REPAIR S-10: what the event ledger says was *spawned*, so a caller
        can reconcile it against what the attempt ledger *recorded*.

        ``AttemptLedger.conserve()`` and ``Denominators.assert_reconciles()``
        are tautological against a ledger built by dropping rows before it
        ever sees them -- both re-derive their comparison from the very list
        they check, and the measurement lane's own T32 negative control
        concedes it ("the leak is invisible locally"). The event ledger is the
        one *external* witness in the framework: a SPAWN entry is written when
        an attempt starts, by the host, hash-chained, before any attempt row
        exists. An attempt that was spawned and then never recorded is
        precisely the "retries collapsed into their parent" leak
        (benchmark-spec §1.2), and it is invisible to every check that only
        reads the attempt list.

        Attribution is by ``attempt_id``; a SPAWN/EXIT entry carrying
        ``attempt_id: null`` is counted in ``unattributed`` rather than
        dropped, because an unattributable spawn is missing evidence, not
        absent evidence.
        """
        spawned: list[str] = []
        exited: list[str] = []
        unattributed = 0
        for record in self._records:
            kind = record.get("kind")
            if kind not in (EventKind.SPAWN.value, EventKind.EXIT.value):
                continue
            attempt_id = record.get("attempt_id")
            if not isinstance(attempt_id, str) or not attempt_id:
                unattributed += 1
                continue
            bucket = spawned if kind == EventKind.SPAWN.value else exited
            if attempt_id not in bucket:
                bucket.append(attempt_id)
        spawned_set, exited_set = set(spawned), set(exited)
        return SpawnAccounting(
            spawned=tuple(spawned),
            exited=tuple(exited),
            spawned_without_exit=tuple(a for a in spawned if a not in exited_set),
            exited_without_spawn=tuple(a for a in exited if a not in spawned_set),
            unattributed=unattributed,
        )

    def assert_chain(self) -> None:
        """Raise :class:`LedgerTampered` naming the first bad index."""
        chain = self.verify_chain()
        if not chain.ok:
            raise LedgerTampered(
                f"{self._path}: chain broken at index {chain.first_bad_index} ({chain.reason})"
            )


# ---------------------------------------------------------------------------
# §3.12 — evidence class derivation. THE ONLY PRODUCER OF NATIVE_PROVEN.
# ---------------------------------------------------------------------------

def evidence_class_for(adapter_class: AdapterClass, chain: ChainVerification) -> EvidenceClass:
    """Derive an attempt's evidence class. There is no other branch.

    * ``NATIVE`` + ``chain.ok`` + ``host_observed > 0`` + ``caller_asserted == 0``
      -> ``NATIVE_PROVEN``
    * ``NATIVE`` + anything else                                 -> ``SIMULATED``
    * ``REPLAY``                                                 -> ``SIMULATED``
    * ``STUB``                                                   -> ``FRAMEWORK``

    No argument changes this mapping, and no caller may pass an evidence class
    in. ``caller_asserted == 0`` is the right whole-ledger test *here* (a native
    driver's own ledger, which contains only what the host witnessed); §5.4
    clause 2 is deliberately the per-attempt test instead, because a run-wide
    ledger that also holds replays can never reach zero.

    ``host_observed > 0`` is the vacuity guard on the same clause: an *empty*
    chain satisfies "ok and no caller-asserted entries" without the host having
    witnessed anything, and a ledger nobody wrote to must not be the strongest
    evidence class in the framework.
    """
    if adapter_class is AdapterClass.NATIVE:
        if chain.ok and chain.host_observed > 0 and chain.caller_asserted == 0:
            return EvidenceClass.NATIVE_PROVEN
        return EvidenceClass.SIMULATED
    if adapter_class is AdapterClass.REPLAY:
        return EvidenceClass.SIMULATED
    if adapter_class is AdapterClass.STUB:
        return EvidenceClass.FRAMEWORK
    raise ContractError(f"evidence_class_for: unhandled adapter_class {adapter_class!r}")


def worker_evidence_class(*, real_process: bool) -> EvidenceClass:
    """A spawned ``python3`` worker is a real subprocess, not a harness (§10.5).

    ``REAL_FIXTURE`` when a real process ran, ``FRAMEWORK`` when the outcome came
    from pure code. The distinction the contract draws is "did a model-driven
    agent harness run", not "did a process run", so neither branch can reach
    ``NATIVE_PROVEN`` and neither takes an argument that could.
    """
    return EvidenceClass.REAL_FIXTURE if real_process else EvidenceClass.FRAMEWORK


# ---------------------------------------------------------------------------
# §10.4 — telemetry
# ---------------------------------------------------------------------------

def parse_usage(
    record: Mapping[str, Any],
    grammar: StreamGrammar,
    model_id: str,
    reported_by: str,
) -> Usage:
    """Read only the usage fields the record actually has. Absent -> ``UNKNOWN``.

    Every field name comes from ``grammar.usage.extract``; nothing is inferred
    from another model's schema and nothing is reconstructed by local
    tokenization. ``.get(name, 0)`` does not appear in this file and a source
    scan in ``test_adapters_and_protocols.py`` asserts it.
    """
    present = grammar.usage.extracted(record)
    return Usage.from_stream(present, model_id=model_id, reported_by=reported_by)


# ---------------------------------------------------------------------------
# §3.12 / §10.2, §10.3 — sessions
# ---------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True, slots=True)
class TurnRecord:
    index: int
    acked: bool
    ack_event_id: str | None
    usage: Usage
    text: str
    late: bool


_NO_USAGE = Usage(
    model_id="unknown", reported_by="unknown",
    input_tokens=UNKNOWN, output_tokens=UNKNOWN,
    cache_read_input_tokens=UNKNOWN, cache_creation_input_tokens=UNKNOWN,
    reasoning_tokens=UNKNOWN, total_tokens=UNKNOWN, wall_clock_ms=UNKNOWN,
    cost_usd=None,
)


class HarnessSession:
    """A driven session. Base class; :class:`ReplaySession` is the offline form.

    ``session_id`` stays ``None`` until a record on the harness's own stream is
    matched by ``grammar.session_ack`` (§10.2). A uuid the caller minted and
    passed to ``--session-id`` is never an ack, and an attempt whose
    ``session_id`` is ``None`` can never be ``NATIVE_PROVEN``.
    """

    def __init__(
        self,
        *,
        ledger: HostLedger,
        adapter_class: AdapterClass,
        run_id: str | None = None,
        attempt_id: str | None = None,
        grammar: StreamGrammar | None = None,
        pool: "_protocols.WorkerPool | None" = None,
        worker_id: str | None = None,
        worker_pid: int | None = None,
    ) -> None:
        self.session_id: str | None = None
        self.turns: int = 0
        self.arrived_after_terminal: bool = False
        self.cancelled: bool = False
        self._ledger = ledger
        self._adapter_class = adapter_class
        self._run_id = run_id if run_id is not None else ledger.run_id
        self._attempt_id = attempt_id
        self._grammar = grammar
        self._pool = pool
        self._worker_id = worker_id
        self._worker_pid = worker_pid
        self._turn_records: list[TurnRecord] = []
        self._closed = False

    # -- identity -----------------------------------------------------------
    @property
    def adapter_class(self) -> AdapterClass:
        return self._adapter_class

    @property
    def ledger(self) -> HostLedger:
        return self._ledger

    @property
    def backed_by_real_process(self) -> bool:
        """True iff this session is attached to a real spawned worker pool.

        The distinction :func:`worker_evidence_class` draws (§10.5): a real
        ``python3`` subprocess earns ``REAL_FIXTURE``; pure code earns
        ``FRAMEWORK``. Neither is a harness, so neither can reach
        ``NATIVE_PROVEN`` -- this property is read by
        :func:`attempt_from_session` and can only ever move an attempt
        *between the two weakest* evidence classes.
        """
        return self._pool is not None

    def turn_records(self) -> tuple[TurnRecord, ...]:
        return tuple(self._turn_records)

    # -- turns --------------------------------------------------------------
    def send(self, text: str) -> TurnRecord:
        raise NotImplementedError("HarnessSession.send is implemented by a concrete session")

    # -- §10.3 cancel -------------------------------------------------------
    def cancel(self, *, grace_s: float = 2.0) -> None:
        """Signal the process GROUP: SIGTERM, wait ``grace_s``, then SIGKILL.

        ``CANCEL_ISSUED`` is appended *before* the signal and ``CANCEL_OBSERVED``
        after the group is reaped, so the ledger records the ordering rather
        than a single after-the-fact assertion. Output that arrives after the
        cancel is appended as ``LATE_OUTPUT`` and flips
        ``arrived_after_terminal``; it never changes the terminal state and is
        never credited as delivered.
        """
        self._ledger.append(
            EventKind.CANCEL_ISSUED,
            attempt_id=self._attempt_id, session_id=self.session_id,
            payload={"signal": "SIGTERM", "grace_s": grace_s, "turns_so_far": self.turns},
        )
        self.cancelled = True

        late_text = ""
        survivors: int | None = None
        if self._pool is not None and self._worker_id is not None:
            pgid: int | None = None
            if self._worker_pid is not None:
                try:
                    pgid = os.getpgid(self._worker_pid)
                except OSError:
                    pgid = None
            # protocols.WorkerPool.cancel signals the process GROUP with SIGTERM.
            self._pool.cancel(self._worker_id)
            time.sleep(max(0.0, min(grace_s, 30.0)))
            # Escalate to SIGKILL on the same group. A worker that installs a
            # SIGTERM handler and keeps running (fixtures/native/workers/
            # worker_ignores_sigterm.py) is exactly what this second signal is
            # for; killing the group, not the pid, is what stops it leaving a
            # grandchild behind.
            if pgid is not None:
                try:
                    os.killpg(pgid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError, OSError):
                    pass
                # Witness the outcome BEFORE collect(). protocols.WorkerPool's
                # own collect() escalates on a 30s timeout, which would rescue a
                # pid-only cancel and hide the leak behind a long pause; the
                # survivor count taken here is what makes "the GROUP was
                # signalled" a checkable fact rather than a claim in a comment.
                deadline = time.monotonic() + 2.0
                survivors = len(live_group_members(pgid))
                while survivors and time.monotonic() < deadline:
                    time.sleep(0.02)
                    survivors = len(live_group_members(pgid))
            results = self._pool.collect()
            late_text = "".join(r.stdout for r in results)
        else:
            late_text = self._drain_after_cancel()

        self._ledger.append(
            EventKind.CANCEL_OBSERVED,
            attempt_id=self._attempt_id, session_id=self.session_id,
            payload={
                "reaped": True,
                "late_bytes": len(late_text.encode("utf-8")),
                "group_survivors": survivors,
            },
        )
        if late_text:
            self.arrived_after_terminal = True
            self._ledger.append(
                EventKind.LATE_OUTPUT,
                attempt_id=self._attempt_id, session_id=self.session_id,
                payload={"bytes": len(late_text.encode("utf-8")), "credited": False},
            )

    def _drain_after_cancel(self) -> str:
        """Whatever the concrete session still holds once the cancel is issued."""
        return ""

    # -- lifecycle ----------------------------------------------------------
    def pids(self) -> frozenset[int]:
        if self._pool is None or self._closed:
            return frozenset()
        return self._pool.pids()

    def close(self) -> None:
        if self._closed:
            return
        if self._pool is not None:
            self._pool.close()
        self._closed = True

    def __enter__(self) -> "HarnessSession":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def attach_session(
    *,
    ledger: HostLedger,
    adapter_class: AdapterClass,
    pool: "_protocols.WorkerPool",
    worker_id: str,
    worker_pid: int | None = None,
    run_id: str | None = None,
    attempt_id: str | None = None,
) -> HarnessSession:
    """Wrap an already-spawned real subprocess as a session, for the offline forms.

    Refuses ``AdapterClass.NATIVE`` and refuses a host-observed ledger. A real
    ``python3`` worker is a real subprocess but it is **not a harness** (§10.5),
    and the only path that may claim ``NATIVE`` is :meth:`CliDriver.spawn`, which
    is approval-gated.
    """
    if adapter_class is AdapterClass.NATIVE:
        raise EvidencePromotionRefused(
            "attach_session: a worker subprocess is not a harness; adapter_class=NATIVE is "
            "reachable only through CliDriver.spawn with an approved token (contract §10.5)"
        )
    if ledger.witness is SignatureClass.HOST_OBSERVED:
        raise EvidencePromotionRefused(
            "attach_session: a fixture/worker path must be handed a ledger constructed "
            "witness=CALLER_ASSERTED (contract §10.5 item 3)"
        )
    return HarnessSession(
        ledger=ledger, adapter_class=adapter_class, pool=pool, worker_id=worker_id,
        worker_pid=worker_pid, run_id=run_id, attempt_id=attempt_id,
    )


class ReplaySession(HarnessSession):
    """Replays a recorded JSONL stream. ``adapter_class`` is ``REPLAY``, always.

    The constructor refuses a host-observed ledger: the host did not witness a
    harness here, it witnessed a file. Every entry this session writes is
    therefore caller-asserted, which is what keeps
    :func:`evidence_class_for` from ever reaching ``NATIVE_PROVEN`` for a replay
    and what makes §5.4 clause 2 refuse the claim downstream.
    """

    def __init__(
        self,
        stream_path: str,
        grammar: StreamGrammar,
        ledger: HostLedger,
        *,
        parent_session_id: str | None = None,
        caller_minted_session_id: str | None = None,
        attempt_id: str | None = None,
    ) -> None:
        if ledger.witness is SignatureClass.HOST_OBSERVED:
            raise EvidencePromotionRefused(
                "ReplaySession: refuses a HostLedger constructed witness=HOST_OBSERVED. A "
                "replay is a file being read, not a harness being witnessed (contract "
                "§10.5 item 3); a host-observed replay ledger would mint correctly-HMAC'd "
                "entries that verify_chain() blesses."
            )
        super().__init__(
            ledger=ledger, adapter_class=AdapterClass.REPLAY, grammar=grammar,
            attempt_id=attempt_id,
        )
        self._stream_path = pathlib.Path(stream_path)
        self._records: list[dict[str, Any]] = list(_io.read_jsonl(self._stream_path))
        self._cursor = 0
        self._parent_session_id = parent_session_id
        self._caller_minted_session_id = caller_minted_session_id
        self._open_session()

    @property
    def stream_path(self) -> pathlib.Path:
        return self._stream_path

    @property
    def remaining(self) -> int:
        return max(0, len(self._records) - self._cursor)

    def _open_session(self) -> None:
        """Consume records up to and including the session ack, if there is one."""
        assert self._grammar is not None
        payload: dict[str, Any] = {"stream": str(self._stream_path)}
        if self._parent_session_id is not None:
            # §10.3 fork: the SESSION_OPEN payload carries the parent id.
            payload["parent_session_id"] = self._parent_session_id
        if self._caller_minted_session_id is not None:
            payload["caller_minted_session_id"] = self._caller_minted_session_id
        self._ledger.append(
            EventKind.SESSION_OPEN,
            attempt_id=self._attempt_id, session_id=None, payload=payload,
        )
        while self._cursor < len(self._records):
            record = self._records[self._cursor]
            if self._grammar.session_ack.matches(record):
                extracted = self._grammar.session_ack.extracted(record)
                sid = extracted.get(self._grammar.session_id_field)
                self._cursor += 1
                if isinstance(sid, str) and sid:
                    self.session_id = sid
                    self._ledger.append(
                        EventKind.SESSION_ACK,
                        attempt_id=self._attempt_id, session_id=sid,
                        payload={"source": "replayed-stream", "record_index": self._cursor - 1},
                    )
                return
            if self._grammar.turn_ack.matches(record):
                return  # a turn started before any session ack: there is no ack
            self._cursor += 1
        # No ack anywhere in the stream: session_id stays None (§10.2 item 2).

    def send(self, text: str) -> TurnRecord:
        assert self._grammar is not None
        index = self.turns
        self._ledger.append(
            EventKind.TURN_START,
            attempt_id=self._attempt_id, session_id=self.session_id,
            payload={"index": index, "chars": len(text)},
        )
        acked = False
        ack_event_id: str | None = None
        usage = _NO_USAGE
        body: list[str] = []

        while self._cursor < len(self._records):
            record = self._records[self._cursor]
            self._cursor += 1
            if self._grammar.turn_ack.matches(record):
                acked = True
                event = self._ledger.append(
                    EventKind.TURN_ACK,
                    attempt_id=self._attempt_id, session_id=self.session_id,
                    payload={"index": index, "source": "replayed-stream"},
                )
                ack_event_id = event.event_id
                continue
            if self._grammar.usage.matches(record):
                usage = parse_usage(
                    record, self._grammar,
                    model_id=str(_first_present(record, ("model", "model_id"), "unknown")),
                    reported_by=f"replay/{self._grammar.name}",
                )
                self._ledger.append(
                    EventKind.USAGE,
                    attempt_id=self._attempt_id, session_id=self.session_id,
                    payload={"index": index, "unknown_fields": list(usage.unknown_fields())},
                )
                break
            text_part = _dig(record, "text")
            if isinstance(text_part, str):
                body.append(text_part)

        self.turns += 1
        self._ledger.append(
            EventKind.TURN_END,
            attempt_id=self._attempt_id, session_id=self.session_id,
            payload={"index": index, "acked": acked},
        )
        turn = TurnRecord(
            index=index, acked=acked, ack_event_id=ack_event_id,
            usage=usage, text="".join(body), late=self.cancelled,
        )
        self._turn_records.append(turn)
        return turn

    def _drain_after_cancel(self) -> str:
        """Unconsumed stream records are this session's post-cancel output."""
        rest = self._records[self._cursor:]
        self._cursor = len(self._records)
        parts = [str(_dig(r, "text")) for r in rest if isinstance(_dig(r, "text"), str)]
        return "".join(parts)


def _first_present(record: Mapping[str, Any], names: Sequence[str], fallback: str) -> Any:
    for name in names:
        value = _dig(record, name)
        if value is not _MISSING:
            return value
    return fallback


# ---------------------------------------------------------------------------
# REPAIR S-12 — the production constructor: a live session -> a real Attempt
# ---------------------------------------------------------------------------

def _unknown_usage(model_id: str, reported_by: str) -> Usage:
    return Usage(
        model_id=model_id, reported_by=reported_by,
        input_tokens=UNKNOWN, output_tokens=UNKNOWN,
        cache_read_input_tokens=UNKNOWN, cache_creation_input_tokens=UNKNOWN,
        reasoning_tokens=UNKNOWN, total_tokens=UNKNOWN, wall_clock_ms=UNKNOWN,
        cost_usd=None,
    )


def _unevaluated_verdict(verifier_id: str) -> Verdict:
    return Verdict(
        passed=None, verifier_id=verifier_id,
        reason="not evaluated: no verifier was run for this attempt",
        hack_class=None, evidence_digest=None,
    )


def attempt_from_session(
    session: HarnessSession,
    *,
    card_id: str,
    arm_id: str,
    role: ArmRole,
    facts: "_classify.RunFacts",
    requested: Stratum,
    realized: Stratum,
    run_id: str | None = None,
    attempt_id: str | None = None,
    control_kind: ControlKind | None = None,
    parent_attempt_id: str | None = None,
    fallback_flags: Sequence[str] = (),
    usage: Usage | None = None,
    outcome: Verdict | None = None,
    adoption: Verdict | None = None,
    started_at: str | None = None,
    ended_at: str | None = None,
    notes: str = "",
) -> Attempt:
    """REPAIR S-12: build a real :class:`~...contract.Attempt` from a live session.

    This is the missing production seam. Before it, every ``Attempt`` in the
    tree was hand-built by a test or a fixture builder, so nothing a driver
    actually produced could reach ``accounting.AttemptLedger`` /
    ``reporting.build_report`` -- the report layer had no input path at all,
    and the classifier had no production caller.

    What is *derived* here, and therefore cannot be handed in:

    * ``terminal_state`` -- :func:`evals.agentic.framework.classify.classify`
      over the observed ``facts``. There is no ``terminal_state=`` parameter;
      an unclassifiable fact pattern raises ``UnclassifiableRun`` rather than
      defaulting to anything.
    * ``adapter_class`` -- the session's own, sealed at construction.
    * ``evidence_class`` -- :func:`evidence_class_for` over
      ``(session.adapter_class, chain)`` for harness-backed sessions, or
      :func:`worker_evidence_class` for a session attached to a real worker
      subprocess. Both are the lane's only producers and neither takes an
      argument a caller could use to promote. **There is no
      ``evidence_class=`` parameter**, so no call site can spell
      ``NATIVE_PROVEN``.

    Why ``session_id`` and ``event_ids`` are withheld unless the derived
    evidence class is ``NATIVE_PROVEN``: ``Attempt.claims_native`` is true for
    *any* non-``None`` session id or non-empty event id tuple, and
    ``contract.assert_native_backed`` then demands a verified, host-observed
    ledger. A replayed ``session-ack`` is a string read out of a *file*; a
    caller-asserted TURN_ACK is the subject's own word. Copying either onto
    the attempt would make a simulated row *claim* native provenance and be
    refused downstream -- so the honest record is ``session_id=None``,
    ``event_ids=()``, with the observed-but-unblessed values written into
    ``notes`` where they are visible and weightless. A genuinely
    host-observed native session (``CliDriver.spawn``, approval-gated) takes
    the other branch and cites its real ids.

    The last line of the function re-runs ``assert_native_backed`` against the
    session's own ledger, so this constructor structurally cannot emit an
    attempt that the native gate would reject.
    """
    if not isinstance(session, HarnessSession):
        raise ContractError(
            f"attempt_from_session: expected a HarnessSession, got {type(session)!r}"
        )
    ledger = session.ledger
    reader = ledger.verifier()
    chain = reader.verify_chain()

    if session.backed_by_real_process and session.adapter_class is not AdapterClass.NATIVE:
        evidence_class = worker_evidence_class(real_process=True)
    else:
        evidence_class = evidence_class_for(session.adapter_class, chain)

    terminal_state = _classify.classify(facts)

    observed_session_id = session.session_id
    blessed = evidence_class is EvidenceClass.NATIVE_PROVEN
    if blessed:
        attempt_session_id = observed_session_id
        cited_event_ids = tuple(
            record["event_id"]
            for record in reader.records()
            if record.get("attempt_id") == attempt_id
            and isinstance(record.get("event_id"), str)
            and reader.signature_class(record["event_id"]) is SignatureClass.HOST_OBSERVED
        )
    else:
        attempt_session_id = None
        cited_event_ids = ()

    provenance_note = (
        f"adapter={session.adapter_class.value} evidence={evidence_class.value} "
        f"ledger_witness={ledger.witness.value} chain_ok={chain.ok} "
        f"host_observed={chain.host_observed} caller_asserted={chain.caller_asserted} "
        f"observed_session_id={observed_session_id!r}"
    )
    if not blessed and (observed_session_id is not None or chain.events):
        provenance_note += " (not cited on this attempt: unblessed provenance carries no weight)"
    full_notes = f"{notes} | {provenance_note}".strip(" |") if notes else provenance_note

    if usage is None:
        turns = session.turn_records()
        reported = [t.usage for t in turns if t.usage.model_id != "unknown"]
        usage = reported[-1] if reported else _unknown_usage(
            realized.model, f"{session.adapter_class.value}-session"
        )

    attempt = Attempt(
        attempt_id=attempt_id if attempt_id is not None else new_id(),
        run_id=run_id if run_id is not None else ledger.run_id,
        card_id=card_id,
        arm_id=arm_id,
        role=role,
        control_kind=control_kind,
        parent_attempt_id=parent_attempt_id,
        terminal_state=terminal_state,
        evidence_class=evidence_class,
        adapter_class=session.adapter_class,
        requested=requested,
        realized=realized,
        fallback_flags=tuple(fallback_flags),
        usage=usage,
        outcome=outcome if outcome is not None else _unevaluated_verdict("none"),
        adoption=adoption if adoption is not None else _unevaluated_verdict("none"),
        started_at=started_at if started_at is not None else now_rfc3339(),
        ended_at=ended_at if ended_at is not None else now_rfc3339(),
        session_id=attempt_session_id,
        event_ids=cited_event_ids,
        arrived_after_terminal=session.arrived_after_terminal,
        notes=full_notes,
    )
    # Self-check: whatever this constructor produced must survive the native
    # gate against the very ledger it was built from. If it does not, the bug
    # is here, and it must surface as ForgedProvenance now rather than as a
    # trusted-looking row in a report later.
    assert_native_backed(attempt, reader)
    return attempt


# ---------------------------------------------------------------------------
# §10.3 — fresh isolation
# ---------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True, slots=True)
class IsolationReport:
    distinct_session_id: bool
    carried_over_paths: tuple[str, ...]
    prior_context_leaked: bool

    @property
    def isolated(self) -> bool:
        return (
            self.distinct_session_id
            and not self.carried_over_paths
            and not self.prior_context_leaked
        )

    def why_not(self) -> tuple[str, ...]:
        reasons: list[str] = []
        if not self.distinct_session_id:
            reasons.append("the fresh session reused the prior session id")
        if self.carried_over_paths:
            reasons.append(
                "workspace artifacts carried over: " + ", ".join(self.carried_over_paths)
            )
        if self.prior_context_leaked:
            reasons.append("a probe about the prior conversation was answered, not disclaimed")
        return tuple(reasons)


def check_fresh_isolation(
    *,
    prior_session_id: str | None,
    fresh_session_id: str | None,
    before: Mapping[str, str],
    after: Mapping[str, str],
    probe_answered_as_unknown: bool,
) -> IsolationReport:
    """§10.3. All three clauses, because the id alone proves nothing.

    Checking only that the ids differ is explicitly insufficient: the
    contaminating state is on disk (``.claude/``, ``.redgate/``, scratch dirs),
    and two genuinely fresh ids can sit on top of a fully contaminated
    workspace. ``before``/``after`` come from
    :func:`evals.agentic.framework.protocols.snapshot_tree`; the diff is
    :func:`~evals.agentic.framework.protocols.diff_tree`.
    """
    return IsolationReport(
        distinct_session_id=(
            prior_session_id is not None
            and fresh_session_id is not None
            and prior_session_id != fresh_session_id
        ),
        carried_over_paths=_protocols.diff_tree(before, after),
        prior_context_leaked=not probe_answered_as_unknown,
    )


def iter_ledger_lines(path: pathlib.Path) -> Iterator[dict[str, Any]]:
    """Convenience reader used by the tamper fixtures' generator and tests."""
    yield from _io.read_jsonl(path)
