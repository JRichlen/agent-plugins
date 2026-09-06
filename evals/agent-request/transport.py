#!/usr/bin/env python3
"""Bounded header mapping for HTTP and OpenAI-compatible clients."""
from __future__ import annotations
import argparse, base64, json
from typing import Iterable
from validator import MAX_SERIALIZED_BYTES, VERSION, ValidationError, canonical_request_bytes

SCHEMA_HEADER = "X-Agent-Request-Schema"
METADATA_HEADER = "X-Agent-Request-Metadata"
MAX_HEADERS = 64
MAX_HEADER_VALUE = 6144

def encode_headers(request: dict) -> list[tuple[str, str]]:
    raw = canonical_request_bytes(request)
    value = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    if len(value) > MAX_HEADER_VALUE: raise ValidationError("HEADER_TOO_LARGE")
    return [(SCHEMA_HEADER, VERSION), (METADATA_HEADER, value)]

def decode_headers(headers: Iterable[tuple[str, str]]) -> dict:
    rows = list(headers)
    if len(rows) > MAX_HEADERS: raise ValidationError("TOO_MANY_HEADERS")
    found: dict[str, str] = {}
    for name, value in rows:
        if not isinstance(name, str) or not isinstance(value, str) or "\r" in name+value or "\n" in name+value: raise ValidationError("HEADER_INJECTION")
        key = name.lower()
        if key in {SCHEMA_HEADER.lower(), METADATA_HEADER.lower()}:
            if key in found: raise ValidationError("DUPLICATE_METADATA_HEADER")
            if len(value) > MAX_HEADER_VALUE: raise ValidationError("HEADER_TOO_LARGE")
            found[key] = value
    if found.get(SCHEMA_HEADER.lower()) != VERSION: raise ValidationError("UNKNOWN_VERSION")
    value = found.get(METADATA_HEADER.lower())
    if value is None: raise ValidationError("MISSING_METADATA_HEADER")
    try:
        raw = base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
        if len(raw) > MAX_SERIALIZED_BYTES: raise ValidationError("REQUEST_TOO_LARGE")
        def closed_object(pairs):
            result = {}
            for key, item in pairs:
                if key in result: raise ValidationError("DUPLICATE_JSON_MEMBER")
                result[key] = item
            return result
        parsed = json.loads(raw, object_pairs_hook=closed_object)
        canonical = canonical_request_bytes(parsed)
        if raw != canonical: raise ValidationError("NONCANONICAL_METADATA")
    except ValidationError: raise
    except Exception as exc: raise ValidationError("MALFORMED_METADATA_HEADER") from exc
    if not isinstance(parsed, dict): raise ValidationError("REQUEST_NOT_OBJECT")
    return parsed

def openai_request_kwargs(request: dict) -> dict:
    """Return metadata headers only; caller keeps endpoint, auth, and prompt body separate."""
    return {"extra_headers": dict(encode_headers(request))}

def self_check() -> None:
    sample={"schema_version":VERSION,"agent_id":"agent_sample_001","run_id":"run_sample_001","task_id":"task_sample_001","action_id":"action_sample_001","phase":"review","context_lane":"normal","reasoning_lane":"medium","model_class":"local-general","privacy_class":"internal","capabilities":["scm:read"],"approval":{"state":"not-required","action_id":"action_sample_001","grant_id":None},"policy_bundle":"policy_sample_001","issued_at":"2026-01-01T00:00:00Z","expires_at":"2026-01-01T00:04:00Z","nonce":"nonce_sample_0001","provenance":{"dispatcher_run_id":"run_dispatch_001","sequence":1}}; assert decode_headers(encode_headers(sample)) == sample
    try: decode_headers([(SCHEMA_HEADER, VERSION), (METADATA_HEADER, "a\r\nb")])
    except ValidationError as exc: assert exc.code == "HEADER_INJECTION"
    else: raise AssertionError("injection accepted")
    print(json.dumps({"transport_self_check":"pass"},sort_keys=True))

if __name__ == "__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--self-check",action="store_true"); args=parser.parse_args()
    if not args.self_check: parser.error("--self-check required")
    self_check()
