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
    phase: str
    context_lane: str
    reasoning_lane: str
    privacy_class: str
    dispatcher_run_id: str
    sequence: int
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

def _enum(value: Any, allowed: set[str], code: str) -> str:
    if not isinstance(value, str) or value not in allowed: fail(code)
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

def canonical_request_bytes(request: Any) -> bytes:
    """Validate the closed, context-free envelope shape and return canonical bytes."""
    obj = _object(request, "REQUEST_NOT_OBJECT")
    _bounded_structure(obj)
    try: encoded = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError): fail("REQUEST_NOT_JSON")
    if len(encoded) > MAX_SERIALIZED_BYTES: fail("REQUEST_TOO_LARGE")
    if set(obj) - REQUIRED - OPTIONAL: fail("UNKNOWN_FIELD")
    if REQUIRED - set(obj): fail("MISSING_FIELD")
    if obj["schema_version"] != VERSION: fail("UNKNOWN_VERSION")
    for key in ("agent_id", "run_id", "task_id", "action_id", "policy_bundle"): _id(obj[key], "INVALID_ID")
    if obj.get("parent_run_id") is not None: _id(obj["parent_run_id"], "INVALID_PARENT_RUN")
    _enum(obj["phase"], PHASES, "INVALID_PHASE")
    _enum(obj["context_lane"], CONTEXT_LANES, "INVALID_CONTEXT_LANE")
    _enum(obj["reasoning_lane"], REASONING_LANES, "INVALID_REASONING_LANE")
    _enum(obj["model_class"], MODEL_CLASSES, "INVALID_MODEL_CLASS")
    _enum(obj["privacy_class"], PRIVACY_CLASSES, "INVALID_PRIVACY_CLASS")
    caps = obj["capabilities"]
    if not isinstance(caps, list): fail("CAPABILITIES_NOT_ARRAY")
    if len(caps) > 8: fail("TOO_MANY_CAPABILITIES")
    if any(not isinstance(c, str) or c not in CAPABILITIES for c in caps): fail("UNKNOWN_CAPABILITY")
    if len(caps) != len(set(caps)) or caps != sorted(caps): fail("CAPABILITIES_NOT_CANONICAL")
    capset = frozenset(caps)
    if "filesystem:workspace-write" in capset and obj["phase"] != "implement": fail("INVALID_CAPABILITY_COMBINATION")
    if "external:publish" in capset and obj["phase"] != "publish": fail("INVALID_CAPABILITY_COMBINATION")
    if "host:admin" in capset and "deployment:operate" not in capset: fail("INVALID_CAPABILITY_COMBINATION")
    if "sensitive:read" in capset and obj["privacy_class"] != "sensitive": fail("INVALID_CAPABILITY_COMBINATION")
    issued, expires = _time(obj["issued_at"], "INVALID_ISSUED_AT"), _time(obj["expires_at"], "INVALID_EXPIRES_AT")
    if expires <= issued or (expires - issued).total_seconds() > MAX_TTL_SECONDS: fail("TTL_INVALID")
    if not isinstance(obj["nonce"], str) or not NONCE_RE.fullmatch(obj["nonce"]): fail("INVALID_NONCE")
    provenance = _object(obj["provenance"], "PROVENANCE_INVALID")
    if set(provenance) != {"dispatcher_run_id", "sequence"}: fail("PROVENANCE_INVALID")
    _id(provenance["dispatcher_run_id"], "PROVENANCE_INVALID")
    if type(provenance["sequence"]) is not int or not 0 <= provenance["sequence"] <= 2_147_483_647: fail("PROVENANCE_INVALID")
    approval = _object(obj["approval"], "APPROVAL_INVALID")
    if set(approval) != {"state", "action_id", "grant_id"}: fail("APPROVAL_INVALID")
    _enum(approval["state"], {"not-required", "pending", "granted"}, "APPROVAL_INVALID")
    _id(approval["action_id"], "APPROVAL_INVALID")
    if approval["grant_id"] is not None: _id(approval["grant_id"], "APPROVAL_INVALID")
    return encoded

def _validate_trusted_context(trusted: Any) -> None:
    if not isinstance(trusted, TrustedContext): fail("TRUSTED_CONTEXT_INVALID")
    try:
        for value in (trusted.issuer_id, trusted.agent_id, trusted.run_id, trusted.task_id, trusted.action_id, trusted.dispatcher_run_id):
            if not isinstance(value, str) or not ID_RE.fullmatch(value): fail("TRUSTED_CONTEXT_INVALID")
        if trusted.phase not in PHASES or trusted.context_lane not in CONTEXT_LANES or trusted.reasoning_lane not in REASONING_LANES or trusted.privacy_class not in PRIVACY_CLASSES: fail("TRUSTED_CONTEXT_INVALID")
        if type(trusted.sequence) is not int or not 0 <= trusted.sequence <= 2_147_483_647: fail("TRUSTED_CONTEXT_INVALID")
        collections = ((trusted.policy_bundles, 16, None), (trusted.model_classes, 3, MODEL_CLASSES), (trusted.capability_ceiling, 8, CAPABILITIES), (trusted.parent_run_ids, 16, None))
        for values, limit, allowed in collections:
            if not isinstance(values, frozenset) or len(values) > limit: fail("TRUSTED_CONTEXT_INVALID")
            if allowed is not None and not values <= allowed: fail("TRUSTED_CONTEXT_INVALID")
            if allowed is None and any(not isinstance(x, str) or not ID_RE.fullmatch(x) for x in values): fail("TRUSTED_CONTEXT_INVALID")
        if not isinstance(trusted.now, datetime) or trusted.now.tzinfo is None: fail("TRUSTED_CONTEXT_INVALID")
        if type(trusted.max_ttl_seconds) is not int or not 1 <= trusted.max_ttl_seconds <= MAX_TTL_SECONDS: fail("TRUSTED_CONTEXT_INVALID")
        if not isinstance(trusted.seen_nonces, set) or len(trusted.seen_nonces) > 128 or any(not isinstance(x, str) or not NONCE_RE.fullmatch(x) for x in trusted.seen_nonces): fail("TRUSTED_CONTEXT_INVALID")
        if not isinstance(trusted.approval_grants, dict) or len(trusted.approval_grants) > 16: fail("TRUSTED_CONTEXT_INVALID")
        for key, grant in trusted.approval_grants.items():
            if not isinstance(grant, ApprovalGrant) or key != grant.grant_id: fail("TRUSTED_CONTEXT_INVALID")
            for value in (grant.grant_id, grant.issuer_id, grant.agent_id, grant.run_id, grant.task_id, grant.action_id):
                if not isinstance(value, str) or not ID_RE.fullmatch(value): fail("TRUSTED_CONTEXT_INVALID")
            if not isinstance(grant.capabilities, frozenset) or len(grant.capabilities) > 8 or not grant.capabilities <= CAPABILITIES: fail("TRUSTED_CONTEXT_INVALID")
            if not isinstance(grant.expires_at, datetime) or grant.expires_at.tzinfo is None: fail("TRUSTED_CONTEXT_INVALID")
    except (AttributeError, TypeError): fail("TRUSTED_CONTEXT_INVALID")

def load_bounded_json(path: Path, limit: int) -> Any:
    try:
        if path.stat().st_size > limit: fail("INPUT_TOO_LARGE")
        def closed_object(pairs):
            result = {}
            for key, value in pairs:
                if key in result: fail("DUPLICATE_JSON_MEMBER")
                result[key] = value
            return result
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=closed_object)
    except ValidationError: raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc: raise ValidationError("INPUT_ERROR") from exc

def validate_request(request: Any, trusted: TrustedContext, *, consume: bool = False) -> dict[str, Any]:
    _validate_trusted_context(trusted)
    canonical_request_bytes(request)
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
    _enum(obj["phase"], PHASES, "INVALID_PHASE")
    _enum(obj["context_lane"], CONTEXT_LANES, "INVALID_CONTEXT_LANE")
    _enum(obj["reasoning_lane"], REASONING_LANES, "INVALID_REASONING_LANE")
    _enum(obj["model_class"], MODEL_CLASSES, "INVALID_MODEL_CLASS")
    _enum(obj["privacy_class"], PRIVACY_CLASSES, "INVALID_PRIVACY_CLASS")
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
    if obj["phase"] != trusted.phase: fail("PHASE_MISMATCH")
    if obj["context_lane"] != trusted.context_lane: fail("CONTEXT_LANE_MISMATCH")
    if obj["reasoning_lane"] != trusted.reasoning_lane: fail("REASONING_LANE_MISMATCH")
    if obj["privacy_class"] != trusted.privacy_class: fail("PRIVACY_CLASS_MISMATCH")
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
    if provenance["dispatcher_run_id"] != trusted.dispatcher_run_id: fail("DISPATCHER_RUN_MISMATCH")
    if provenance["sequence"] != trusted.sequence: fail("SEQUENCE_MISMATCH")
    approval = _object(obj["approval"], "APPROVAL_INVALID")
    if set(approval) != {"state", "action_id", "grant_id"}: fail("APPROVAL_INVALID")
    if approval["action_id"] != obj["action_id"]: fail("APPROVAL_ACTION_MISMATCH")
    state, grant_id = approval["state"], approval["grant_id"]
    _enum(state, {"not-required", "pending", "granted"}, "APPROVAL_INVALID")
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
    return {"schema_version": VERSION, "decision": "allow", "issuer_id": trusted.issuer_id, "phase": trusted.phase, "context_lane": trusted.context_lane, "reasoning_lane": trusted.reasoning_lane, "privacy_class": trusted.privacy_class, "dispatcher_run_id": trusted.dispatcher_run_id, "sequence": trusted.sequence, "capabilities": list(caps)}


def context_from_json(raw: Any) -> TrustedContext:
    obj = _object(raw, "TRUSTED_CONTEXT_INVALID")
    try: _bounded_structure(obj)
    except ValidationError: fail("TRUSTED_CONTEXT_INVALID")
    required = {"issuer_id","agent_id","run_id","task_id","action_id","phase","context_lane","reasoning_lane","privacy_class","dispatcher_run_id","sequence","policy_bundles","model_classes","capability_ceiling","now"}
    optional = {"parent_run_ids","approval_grants","seen_nonces","max_ttl_seconds"}
    if set(obj) - required - optional or required - set(obj): fail("TRUSTED_CONTEXT_INVALID")
    list_limits = {"policy_bundles":16,"model_classes":3,"capability_ceiling":8,"parent_run_ids":16,"approval_grants":16,"seen_nonces":128}
    for key, limit in list_limits.items():
        value = obj.get(key, [])
        if not isinstance(value, list) or len(value) > limit: fail("TRUSTED_CONTEXT_INVALID")
        if key != "approval_grants":
            try:
                if len(value) != len(set(value)): fail("TRUSTED_CONTEXT_INVALID")
            except TypeError: fail("TRUSTED_CONTEXT_INVALID")
    for key in ("policy_bundles", "parent_run_ids"):
        if any(not isinstance(x, str) or not ID_RE.fullmatch(x) for x in obj.get(key, [])): fail("TRUSTED_CONTEXT_INVALID")
    if any(not isinstance(x, str) or x not in MODEL_CLASSES for x in obj["model_classes"]): fail("TRUSTED_CONTEXT_INVALID")
    if any(not isinstance(x, str) or x not in CAPABILITIES for x in obj["capability_ceiling"]): fail("TRUSTED_CONTEXT_INVALID")
    if any(not isinstance(x, str) or not NONCE_RE.fullmatch(x) for x in obj.get("seen_nonces", [])): fail("TRUSTED_CONTEXT_INVALID")
    if len(obj.get("seen_nonces", [])) != len(set(obj.get("seen_nonces", []))): fail("TRUSTED_CONTEXT_INVALID")
    grants = {}
    for item in obj.get("approval_grants", []):
        g = _object(item, "TRUSTED_CONTEXT_INVALID")
        if set(g) != {"grant_id","issuer_id","agent_id","run_id","task_id","action_id","capabilities","expires_at"}: fail("TRUSTED_CONTEXT_INVALID")
        gid = _id(g.get("grant_id"), "TRUSTED_CONTEXT_INVALID")
        if gid in grants or not isinstance(g["capabilities"], list) or len(g["capabilities"]) > 8 or any(not isinstance(x,str) or x not in CAPABILITIES for x in g["capabilities"]) or len(g["capabilities"]) != len(set(g["capabilities"])): fail("TRUSTED_CONTEXT_INVALID")
        grants[gid] = ApprovalGrant(gid, _id(g["issuer_id"],"TRUSTED_CONTEXT_INVALID"), _id(g["agent_id"],"TRUSTED_CONTEXT_INVALID"), _id(g["run_id"],"TRUSTED_CONTEXT_INVALID"), _id(g["task_id"],"TRUSTED_CONTEXT_INVALID"), _id(g["action_id"],"TRUSTED_CONTEXT_INVALID"), frozenset(g["capabilities"]), _time(g["expires_at"], "TRUSTED_CONTEXT_INVALID"))
    ttl=obj.get("max_ttl_seconds",MAX_TTL_SECONDS)
    if type(ttl) is not int or not 1 <= ttl <= MAX_TTL_SECONDS: fail("TRUSTED_CONTEXT_INVALID")
    trusted=TrustedContext(issuer_id=obj["issuer_id"],agent_id=obj["agent_id"],run_id=obj["run_id"],task_id=obj["task_id"],action_id=obj["action_id"],phase=obj["phase"],context_lane=obj["context_lane"],reasoning_lane=obj["reasoning_lane"],privacy_class=obj["privacy_class"],dispatcher_run_id=obj["dispatcher_run_id"],sequence=obj["sequence"],policy_bundles=frozenset(obj["policy_bundles"]),model_classes=frozenset(obj["model_classes"]),capability_ceiling=frozenset(obj["capability_ceiling"]),now=_time(obj["now"],"TRUSTED_CONTEXT_INVALID"),parent_run_ids=frozenset(obj.get("parent_run_ids",[])),approval_grants=grants,seen_nonces=set(obj.get("seen_nonces",[])),max_ttl_seconds=ttl)
    _validate_trusted_context(trusted)
    return trusted


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
