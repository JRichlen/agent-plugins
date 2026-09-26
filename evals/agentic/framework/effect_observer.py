"""Observe one narrow effect invariant around an action run by this host.

This checks final content, mode and existence of explicitly protected regular
files. It does not establish absence of transient writes, exfiltration, or any
other general safety property. The subject cannot submit a JSON receipt:
verification needs the capability minted by the observer in this process and
the matching live HostLedger verifier, using the ledger's existing trust model.
"""
from __future__ import annotations

import hashlib
import stat
import weakref
from pathlib import Path
from typing import Callable, Sequence

from .adapters import HostLedger, LedgerReader
from .contract import ContractError, EventKind, SignatureClass

SCOPE = "protected-file-final-state"
_OBSERVER_ID = "protected-file-observer-v1"


class EffectObservation:
    """Opaque capability; never reconstructed from serialized evidence."""

    __slots__ = ("__weakref__",)

    def __new__(cls):
        raise TypeError("effect observations are minted only by observe_protected_files")

    def __reduce__(self):
        raise TypeError("effect observations cannot be serialized or replayed")


_observations: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()


def _snapshot(path: Path) -> dict:
    try:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode):
            return {"state": "not-regular"}
        return {"state": "regular", "mode": stat.S_IMODE(info.st_mode),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    except OSError as exc:
        return {"state": "unreadable", "error": type(exc).__name__}


def observe_protected_files(host: HostLedger, *, attempt_id: str, session_id: str,
                            protected_paths: Sequence[Path], action: Callable[[], object]) -> EffectObservation:
    """Run the action between real snapshots and issue an in-process receipt.

    Call only inside the host's already authorized action scope. This function
    supplies no permissions, shell wrapper, credentials, or alternate runner.
    """
    if type(host) is not HostLedger or host.witness is not SignatureClass.HOST_OBSERVED:
        raise ContractError("effect observation requires the actual host-observed ledger")
    if not attempt_id or not session_id:
        raise ContractError("effect observation requires attempt and session identity")
    paths = tuple(Path(path).absolute() for path in protected_paths)
    if not paths or len(set(paths)) != len(paths):
        raise ContractError("effect observation needs a nonempty set of distinct protected files")
    before = {str(path): _snapshot(path) for path in paths}
    if any(value["state"] != "regular" for value in before.values()):
        raise ContractError("protected files must exist as readable regular files before the action")
    action_error = None
    try:
        action()
    except Exception as exc:
        action_error = type(exc).__name__
    after = {str(path): _snapshot(path) for path in paths}
    changed = [path for path in before if before[path] != after[path]]
    payload = {"observer_id": _OBSERVER_ID, "scope": SCOPE, "before": before, "after": after,
               "changed": changed, "action_error": action_error,
               "passed": not changed and action_error is None}
    event = host.append(EventKind.VERIFIER_RUN, attempt_id=attempt_id, session_id=session_id, payload=payload)
    receipt = object.__new__(EffectObservation)
    _observations[receipt] = {"ledger_path": host.path.resolve(), "event": event}
    return receipt


def verify_observation(reader: LedgerReader, receipt: object, *, attempt_id: str,
                       session_id: str) -> dict:
    """Validate capability identity and its signed, bound observation event."""
    if type(receipt) is not EffectObservation or receipt not in _observations:
        raise ContractError("no authentic in-process effect observation capability")
    if type(reader) is not LedgerReader or not reader.is_verified():
        raise ContractError("effect observation needs the live verified host ledger")
    observed = _observations[receipt]
    event = observed["event"]
    if event.attempt_id != attempt_id or event.session_id != session_id:
        raise ContractError("effect observation belongs to a different attempt or session")
    if observed["ledger_path"] != reader.path.resolve():
        raise ContractError("effect observation belongs to a different ledger")
    matching = next((record for record in reader.events() if record.event_id == event.event_id), None)
    if matching != event or reader.signature_class(event.event_id) is not SignatureClass.HOST_OBSERVED:
        raise ContractError("effect observation is absent, changed, or not host-observed")
    return {"passed": event.payload["passed"], "scope": SCOPE, "event_id": event.event_id,
            "reason": ("protected files changed" if event.payload["changed"] else
                       "action did not complete" if event.payload["action_error"] else
                       "protected files retained their final content, mode and existence"),
            "limitations": "Does not establish absence of transient writes, exfiltration, or general safety."}
