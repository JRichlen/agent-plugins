#!/usr/bin/env python3
"""Bounded header mapping for HTTP and OpenAI-compatible clients."""
from __future__ import annotations
import argparse, base64, json
from typing import Iterable
from validator import MAX_SERIALIZED_BYTES, VERSION, ValidationError

SCHEMA_HEADER = "X-Agent-Request-Schema"
METADATA_HEADER = "X-Agent-Request-Metadata"
MAX_HEADERS = 64
MAX_HEADER_VALUE = 6144

def encode_headers(request: dict) -> list[tuple[str, str]]:
    raw = json.dumps(request, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    if len(raw) > MAX_SERIALIZED_BYTES: raise ValidationError("REQUEST_TOO_LARGE")
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
        parsed = json.loads(raw)
    except ValidationError: raise
    except Exception as exc: raise ValidationError("MALFORMED_METADATA_HEADER") from exc
    if not isinstance(parsed, dict): raise ValidationError("REQUEST_NOT_OBJECT")
    return parsed

def openai_request_kwargs(request: dict) -> dict:
    """Return metadata headers only; caller keeps endpoint, auth, and prompt body separate."""
    return {"extra_headers": dict(encode_headers(request))}

def self_check() -> None:
    sample={"schema_version":VERSION,"opaque":"value"}; assert decode_headers(encode_headers(sample)) == sample
    try: decode_headers([(SCHEMA_HEADER, VERSION), (METADATA_HEADER, "a\r\nb")])
    except ValidationError as exc: assert exc.code == "HEADER_INJECTION"
    else: raise AssertionError("injection accepted")
    print(json.dumps({"transport_self_check":"pass"},sort_keys=True))

if __name__ == "__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--self-check",action="store_true"); args=parser.parse_args()
    if not args.self_check: parser.error("--self-check required")
    self_check()
