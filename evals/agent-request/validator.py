#!/usr/bin/env python3
"""Deterministic semantic validator for agent-request/v1.

The request is untrusted. TrustedContext is supplied out of band by an adapter.
No signature or live identity system is implemented by this offline core.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import argparse, json, re, sys

VERSION = "agent-request/v1"
MAX_SERIALIZED_BYTES = 4096
MAX_TTL_SECONDS = 300
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._:-]{2,63}$")
NONCE_RE = re.compile(r"^[A-Za-z0-9_-]{16,64}$")
PHASES = {"plan", "research", "implement", "verify", "review", "publish"}
CONTEXT_LANES = {"triage", "normal", "deep", "exclusive"}
REASONING_LANES = {"low", "medium", "high"}
MODEL_CLASSES = {"local-general", "local-specialist", "hosted-escalation"}
PRIVACY_CLASSES = {"public", "internal", "sensitive"}
CAPABILITIES = {
    "scm:read", "filesystem:workspace-read", "filesystem:workspace-write",
    "sensitive:read", "network:http", "external:publish",
    "deployment:operate", "host:admin",
}
PRIVILEGED = {"filesystem:workspace-write", "sensitive:read", "external:publish", "deployment:operate", "host:admin"}
REQUIRED = {
    "schema_version", "agent_id", "run_id", "task_id", "action_id", "phase",
    "context_lane", "reasoning_lane", "model_class", "privacy_class",
    "capabilities", "approval", "policy_bundle", "issued_at", "expires_at",
    "nonce", "provenance",
}
OPTIONAL = {"parent_run_id"}

class ValidationError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)

@dataclass(frozen=True)
class ApprovalGrant:
    grant_id: str
    issuer_id: str
    agent_id: str
    run_id: str
    task_id: str
    action_id: str
    capabilities: frozenset[str]
    expires_at: datetime

@dataclass
class TrustedContext:
    issuer_id: str
    agent_id: str
    run_id: str
    task_id: str
    action_id: str
    policy_bundles: frozenset[str]
    model_classes: frozenset[str]
    capability_ceiling: frozenset[str]
    now: datetime
    parent_run_ids: frozenset[str] = frozenset()
    approval_grants: dict[str, ApprovalGrant] = field(default_factory=dict)
    seen_nonces: set[str] = field(default_factory=set)
    max_ttl_seconds: int = MAX_TTL_SECONDS


def fail(code: str) -> None:
    raise ValidationError(code)


def _object(value: Any, code: str) -> dict[str, Any]:
    if not isinstance(value, dict): fail(code)
    return value


def _id(value: Any, code: str) -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value): fail(code)
    return value


def _time(value: Any, code: str) -> datetime:
    if not isinstance(value, str) or len(value) > 32 or not value.endswith("Z"): fail(code)
    try: parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError: fail(code)
    if parsed.tzinfo is None: fail(code)
    return parsed.astimezone(timezone.utc)


def _bounded_structure(value: Any) -> None:
    stack = [(value, 0)]; nodes = 0
    while stack:
        current, depth = stack.pop(); nodes += 1
        if nodes > 128: fail("REQUEST_TOO_COMPLEX")
        if depth > 4: fail("REQUEST_STRUCTURE_TOO_DEEP")
        if isinstance(current, dict): stack.extend((item, depth + 1) for pair in current.items() for item in pair)
        elif isinstance(current, list): stack.extend((item, depth + 1) for item in current)
        elif not isinstance(current, (str, int, float, bool, type(None))): fail("REQUEST_NOT_JSON")

def load_bounded_json(path: Path, limit: int) -> Any:
    try:
        if path.stat().st_size > limit: fail("INPUT_TOO_LARGE")
        return json.loads(path.read_text(encoding="utf-8"))
    except ValidationError: raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc: raise ValidationError("INPUT_ERROR") from exc

def validate_request(request: Any, trusted: TrustedContext, *, consume: bool = False) -> dict[str, Any]:
    if not isinstance(trusted, TrustedContext) or not ID_RE.fullmatch(trusted.issuer_id): fail("TRUSTED_CONTEXT_INVALID")
    obj = _object(request, "REQUEST_NOT_OBJECT")
    _bounded_structure(obj)
    try: encoded = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError): fail("REQUEST_NOT_JSON")
    if len(encoded) > MAX_SERIALIZED_BYTES: fail("REQUEST_TOO_LARGE")
    if set(obj) - REQUIRED - OPTIONAL: fail("UNKNOWN_FIELD")
    if REQUIRED - set(obj): fail("MISSING_FIELD")
    if obj["schema_version"] != VERSION: fail("UNKNOWN_VERSION")
    for key in ("agent_id", "run_id", "task_id", "action_id", "policy_bundle"):
        _id(obj[key], "INVALID_ID")
    parent = obj.get("parent_run_id")
    if parent is not None: _id(parent, "INVALID_PARENT_RUN")
    if obj["phase"] not in PHASES: fail("INVALID_PHASE")
    if obj["context_lane"] not in CONTEXT_LANES: fail("INVALID_CONTEXT_LANE")
    if obj["reasoning_lane"] not in REASONING_LANES: fail("INVALID_REASONING_LANE")
    if obj["model_class"] not in MODEL_CLASSES: fail("INVALID_MODEL_CLASS")
    if obj["privacy_class"] not in PRIVACY_CLASSES: fail("INVALID_PRIVACY_CLASS")
    caps = obj["capabilities"]
    if not isinstance(caps, list): fail("CAPABILITIES_NOT_ARRAY")
    if len(caps) > 8: fail("TOO_MANY_CAPABILITIES")
    if any(not isinstance(c, str) or c not in CAPABILITIES for c in caps): fail("UNKNOWN_CAPABILITY")
    if len(caps) != len(set(caps)) or caps != sorted(caps): fail("CAPABILITIES_NOT_CANONICAL")
    capset = frozenset(caps)
    if not capset <= trusted.capability_ceiling: fail("CAPABILITY_EXCEEDS_CEILING")
    if "filesystem:workspace-write" in capset and obj["phase"] != "implement": fail("INVALID_CAPABILITY_COMBINATION")
    if "external:publish" in capset and obj["phase"] != "publish": fail("INVALID_CAPABILITY_COMBINATION")
    if "host:admin" in capset and "deployment:operate" not in capset: fail("INVALID_CAPABILITY_COMBINATION")
    if "sensitive:read" in capset and obj["privacy_class"] != "sensitive": fail("INVALID_CAPABILITY_COMBINATION")
    if obj["agent_id"] != trusted.agent_id: fail("AGENT_MISMATCH")
    if obj["run_id"] != trusted.run_id: fail("RUN_MISMATCH")
    if obj["task_id"] != trusted.task_id: fail("TASK_MISMATCH")
    if obj["action_id"] != trusted.action_id: fail("ACTION_MISMATCH")
    if parent is not None and parent not in trusted.parent_run_ids: fail("PARENT_RUN_UNTRUSTED")
    if obj["policy_bundle"] not in trusted.policy_bundles: fail("POLICY_BUNDLE_UNTRUSTED")
    if obj["model_class"] not in trusted.model_classes: fail("MODEL_CLASS_DENIED")
    issued, expires = _time(obj["issued_at"], "INVALID_ISSUED_AT"), _time(obj["expires_at"], "INVALID_EXPIRES_AT")
    if issued > trusted.now: fail("NOT_YET_VALID")
    if expires <= trusted.now: fail("REQUEST_EXPIRED")
    if expires <= issued or (expires - issued).total_seconds() > min(MAX_TTL_SECONDS, trusted.max_ttl_seconds): fail("TTL_INVALID")
    nonce = obj["nonce"]
    if not isinstance(nonce, str) or not NONCE_RE.fullmatch(nonce): fail("INVALID_NONCE")
    if nonce in trusted.seen_nonces: fail("REPLAYED_NONCE")
    provenance = _object(obj["provenance"], "PROVENANCE_INVALID")
    if set(provenance) != {"dispatcher_run_id", "sequence"}: fail("PROVENANCE_INVALID")
    _id(provenance["dispatcher_run_id"], "PROVENANCE_INVALID")
    if type(provenance["sequence"]) is not int or not 0 <= provenance["sequence"] <= 2_147_483_647: fail("PROVENANCE_INVALID")
    approval = _object(obj["approval"], "APPROVAL_INVALID")
    if set(approval) != {"state", "action_id", "grant_id"}: fail("APPROVAL_INVALID")
    if approval["action_id"] != obj["action_id"]: fail("APPROVAL_ACTION_MISMATCH")
    state, grant_id = approval["state"], approval["grant_id"]
    if state not in {"not-required", "pending", "granted"}: fail("APPROVAL_INVALID")
    if state == "pending": fail("APPROVAL_PENDING")
    if capset & PRIVILEGED:
        if state != "granted" or not isinstance(grant_id, str): fail("CAPABILITY_REQUIRES_APPROVAL")
        grant = trusted.approval_grants.get(grant_id)
        if grant is None: fail("APPROVAL_GRANT_UNKNOWN")
        if grant.issuer_id != trusted.issuer_id: fail("APPROVAL_ISSUER_MISMATCH")
        if (grant.agent_id, grant.run_id, grant.task_id, grant.action_id) != (obj["agent_id"], obj["run_id"], obj["task_id"], obj["action_id"]): fail("APPROVAL_SCOPE_MISMATCH")
        if grant.expires_at <= trusted.now: fail("APPROVAL_EXPIRED")
        if not (capset & PRIVILEGED) <= grant.capabilities: fail("APPROVAL_CAPABILITY_MISMATCH")
    elif state != "not-required" or grant_id is not None:
        fail("UNNEEDED_APPROVAL_ASSERTION")
    if consume: trusted.seen_nonces.add(nonce)
    return {"schema_version": VERSION, "decision": "allow", "issuer_id": trusted.issuer_id, "capabilities": list(caps)}


def context_from_json(raw: Any) -> TrustedContext:
    obj = _object(raw, "TRUSTED_CONTEXT_INVALID")
    grants = {}
    for item in obj.get("approval_grants", []):
        g = _object(item, "TRUSTED_CONTEXT_INVALID"); gid = _id(g.get("grant_id"), "TRUSTED_CONTEXT_INVALID")
        grants[gid] = ApprovalGrant(gid, g["issuer_id"], g["agent_id"], g["run_id"], g["task_id"], g["action_id"], frozenset(g["capabilities"]), _time(g["expires_at"], "TRUSTED_CONTEXT_INVALID"))
    return TrustedContext(obj["issuer_id"], obj["agent_id"], obj["run_id"], obj["task_id"], obj["action_id"], frozenset(obj["policy_bundles"]), frozenset(obj["model_classes"]), frozenset(obj["capability_ceiling"]), _time(obj["now"], "TRUSTED_CONTEXT_INVALID"), frozenset(obj.get("parent_run_ids", [])), grants, set(obj.get("seen_nonces", [])), obj.get("max_ttl_seconds", MAX_TTL_SECONDS))


def self_check() -> None:
    schema = json.loads((Path(__file__).parent / "schema.json").read_text())
    if schema["properties"]["schema_version"]["const"] != VERSION: fail("SCHEMA_DRIFT")
    if set(schema["properties"]["capabilities"]["items"]["enum"]) != CAPABILITIES: fail("SCHEMA_DRIFT")
    print(json.dumps({"schema_version": VERSION, "self_check": "pass"}, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--self-check", action="store_true"); parser.add_argument("--examples", type=Path); parser.add_argument("--request", type=Path); parser.add_argument("--trusted-context", type=Path); parser.add_argument("--consume", action="store_true"); args = parser.parse_args()
    try:
        if args.self_check: self_check(); return 0
        if args.examples:
            paths = sorted(args.examples.glob("*.json"));
            if not paths: fail("NO_EXAMPLES")
            for path in paths:
                wrapper = json.loads(path.read_text()); validate_request(wrapper["request"], context_from_json(wrapper["trusted_context"]))
            print(json.dumps({"examples": len(paths), "valid": True}, sort_keys=True)); return 0
        if args.request and args.trusted_context:
            req = load_bounded_json(args.request, MAX_SERIALIZED_BYTES); trusted = context_from_json(load_bounded_json(args.trusted_context, 16384))
            print(json.dumps(validate_request(req, trusted, consume=args.consume), sort_keys=True)); return 0
        parser.error("use --self-check, --examples, or --request with --trusted-context")
    except (ValidationError, KeyError, json.JSONDecodeError, OSError) as exc:
        code = exc.code if isinstance(exc, ValidationError) else "INPUT_ERROR"
        print(json.dumps({"valid": False, "error_code": code}, sort_keys=True), file=sys.stderr); return 2

if __name__ == "__main__": raise SystemExit(main())
