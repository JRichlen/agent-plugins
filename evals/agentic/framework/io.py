"""evals.agentic.framework.io — JSON load/dump plus the stdlib JSON-Schema subset
validator (core lane, contract §3.2).

Fails closed: any schema keyword outside SUPPORTED_KEYWORDS raises
UnsupportedKeyword at schema-load time, not at validation time and not silently.
"""
from __future__ import annotations

import functools
import hashlib
import json
import os
import pathlib
import re
from collections.abc import Iterator, Mapping
from fractions import Fraction
from typing import Any

from .contract import ContractError, SchemaError, UnsupportedKeyword, ValidationError

__all__ = [
    "SUPPORTED_KEYWORDS", "SCHEMA_NAMES",
    "repo_root", "schema_dir", "Schema", "load_schema",
    "load_json", "dump_json", "load_and_validate",
    "read_jsonl", "append_jsonl", "sha256_file",
    # re-exported per contract §2.5
    "ContractError", "SchemaError", "ValidationError", "UnsupportedKeyword",
]

SUPPORTED_KEYWORDS: frozenset[str] = frozenset({
    "$schema", "$id", "title", "description", "examples", "$comment", "$defs", "$ref",
    "type", "enum", "const", "required", "properties", "patternProperties",
    "additionalProperties", "propertyNames", "minProperties", "maxProperties",
    "dependentRequired", "items", "minItems", "maxItems", "uniqueItems",
    "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf",
    "minLength", "maxLength", "pattern", "format",
    "oneOf", "anyOf", "allOf", "not", "if", "then", "else",
})

SCHEMA_NAMES: tuple[str, ...] = (
    "usage", "judgement", "coverage", "card", "run-manifest",
    "attempt", "event", "capability",
)

_DRAFT = "https://json-schema.org/draft/2020-12/schema"
_ALLOWED_TYPES = frozenset({"object", "array", "string", "integer", "number", "boolean", "null"})
_ALLOWED_FORMATS = frozenset({"date-time", "uuid"})
_DATE_TIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$")
_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
_REF_RE = re.compile(r"^#/\$defs/([^/]+)$")


def repo_root() -> pathlib.Path:
    """Walk up from this file's own location looking for .claude-plugin/marketplace.json.

    NEVER from os.getcwd() -- see the counterfeit-tier rationale in contract §3.2.
    """
    here = pathlib.Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / ".claude-plugin" / "marketplace.json").is_file():
            return candidate
    raise ContractError(
        "repo_root: no ancestor directory of io.py contains .claude-plugin/marketplace.json"
    )


def schema_dir() -> pathlib.Path:
    return repo_root() / "evals" / "agentic" / "schemas"


# ---------------------------------------------------------------------------
# Compile-time keyword/regex/type/format validation (fail closed).
# ---------------------------------------------------------------------------

def _check_type_value(t: Any) -> None:
    candidates = t if isinstance(t, list) else [t]
    for c in candidates:
        if not isinstance(c, str) or c not in _ALLOWED_TYPES:
            raise SchemaError(f"unsupported 'type' value: {c!r}")


@functools.lru_cache(maxsize=None)
def _compile_pattern(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern)


def _try_compile(pattern: str) -> None:
    try:
        _compile_pattern(pattern)
    except re.error as exc:
        raise SchemaError(f"bad regex {pattern!r}: {exc}") from exc


def _walk(node: Any, defs: Mapping[str, Any]) -> None:
    if not isinstance(node, Mapping):
        raise SchemaError(f"schema node must be a JSON object, got {type(node)!r}")

    for key in node:
        if key not in SUPPORTED_KEYWORDS:
            raise UnsupportedKeyword(f"unsupported keyword: {key!r}")

    if "$ref" in node:
        ref = node["$ref"]
        m = _REF_RE.match(ref) if isinstance(ref, str) else None
        if not m:
            raise SchemaError(
                f"unsupported $ref form: {ref!r} (only local '#/$defs/<name>' is supported)"
            )
        if m.group(1) not in defs:
            raise SchemaError(f"$ref target not found: {ref!r}")

    if "pattern" in node:
        _try_compile(node["pattern"])

    if "format" in node:
        if node["format"] not in _ALLOWED_FORMATS:
            raise UnsupportedKeyword(f"unsupported format: {node['format']!r}")

    if "type" in node:
        _check_type_value(node["type"])

    if "additionalProperties" in node:
        if not isinstance(node["additionalProperties"], bool):
            raise UnsupportedKeyword(
                "additionalProperties: subschema form is unsupported (boolean only)"
            )

    if "if" in node and "then" not in node:
        raise UnsupportedKeyword("'if' without 'then' is unsupported")

    if "patternProperties" in node:
        for pat, sub in node["patternProperties"].items():
            _try_compile(pat)
            _walk(sub, defs)

    if "properties" in node:
        for sub in node["properties"].values():
            _walk(sub, defs)

    for key in ("items", "propertyNames", "not", "then", "else", "if"):
        if key in node:
            _walk(node[key], defs)

    for key in ("oneOf", "anyOf", "allOf"):
        if key in node:
            for sub in node[key]:
                _walk(sub, defs)

    if "$defs" in node:
        for sub in node["$defs"].values():
            _walk(sub, defs)


def _check_root(raw: Any) -> None:
    if not isinstance(raw, Mapping):
        raise SchemaError("schema document must be a JSON object")
    val = raw.get("$schema")
    if val is None:
        raise SchemaError("schema document is missing the required '$schema' keyword")
    if val != _DRAFT:
        raise SchemaError(f"unsupported $schema: {val!r} (must be {_DRAFT!r})")


# ---------------------------------------------------------------------------
# Runtime instance validation.
# ---------------------------------------------------------------------------

def _json_type_name(instance: Any) -> str:
    if isinstance(instance, bool):
        return "boolean"
    if isinstance(instance, Mapping):
        return "object"
    if isinstance(instance, list):
        return "array"
    if isinstance(instance, str):
        return "string"
    if isinstance(instance, int):
        return "integer"
    if isinstance(instance, float):
        return "number"
    if instance is None:
        return "null"
    return type(instance).__name__


def _matches_single_type(instance: Any, t: str) -> bool:
    if t == "object":
        return isinstance(instance, Mapping)
    if t == "array":
        return isinstance(instance, list)
    if t == "string":
        return isinstance(instance, str)
    if t == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if t == "number":
        return isinstance(instance, (int, float)) and not isinstance(instance, bool)
    if t == "boolean":
        return isinstance(instance, bool)
    if t == "null":
        return instance is None
    return False


def _type_matches(instance: Any, type_spec: Any) -> bool:
    candidates = type_spec if isinstance(type_spec, list) else [type_spec]
    return any(_matches_single_type(instance, t) for t in candidates)


def _is_number(instance: Any) -> bool:
    return isinstance(instance, (int, float)) and not isinstance(instance, bool)


def _json_eq(a: Any, b: Any) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a == b
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_json_eq(x, y) for x, y in zip(a, b))
    if isinstance(a, Mapping) and isinstance(b, Mapping):
        return set(a.keys()) == set(b.keys()) and all(_json_eq(a[k], b[k]) for k in a)
    return a == b


def _to_fraction(x: Any) -> Fraction:
    if isinstance(x, int) and not isinstance(x, bool):
        return Fraction(x)
    return Fraction(str(x))


def _format_ok(fmt: str, instance: str) -> bool:
    if fmt == "date-time":
        return bool(_DATE_TIME_RE.match(instance))
    if fmt == "uuid":
        return bool(_UUID_RE.match(instance))
    return True


def _iter_errors(
    schema: Mapping[str, Any],
    instance: Any,
    pointer: str,
    defs: Mapping[str, Any],
    schema_id: str,
) -> Iterator[ValidationError]:
    for key, value in schema.items():
        if key == "$ref":
            m = _REF_RE.match(value)
            target = defs[m.group(1)]  # existence already checked at load time
            yield from _iter_errors(target, instance, pointer, defs, schema_id)

        elif key == "type":
            if not _type_matches(instance, value):
                yield ValidationError(
                    pointer, "type", schema_id,
                    f"expected type {value!r}, got {_json_type_name(instance)!r}",
                )

        elif key == "enum":
            if not any(_json_eq(instance, opt) for opt in value):
                yield ValidationError(pointer, "enum", schema_id, f"{instance!r} is not one of {value!r}")

        elif key == "const":
            if not _json_eq(instance, value):
                yield ValidationError(pointer, "const", schema_id, f"{instance!r} != {value!r}")

        elif key == "required":
            if isinstance(instance, Mapping):
                for name in value:
                    if name not in instance:
                        yield ValidationError(
                            f"{pointer}/{name}", "required", schema_id,
                            f"missing required property {name!r}",
                        )

        elif key == "properties":
            if isinstance(instance, Mapping):
                for name, sub in value.items():
                    if name in instance:
                        yield from _iter_errors(sub, instance[name], f"{pointer}/{name}", defs, schema_id)

        elif key == "patternProperties":
            if isinstance(instance, Mapping):
                for pat, sub in value.items():
                    compiled = _compile_pattern(pat)
                    for name in instance:
                        if compiled.search(name):
                            yield from _iter_errors(sub, instance[name], f"{pointer}/{name}", defs, schema_id)

        elif key == "additionalProperties":
            if isinstance(instance, Mapping) and value is False:
                props = schema.get("properties", {})
                pattern_keys = list(schema.get("patternProperties", {}).keys())
                compiled_pats = [_compile_pattern(p) for p in pattern_keys]
                for name in instance:
                    matched = name in props or any(p.search(name) for p in compiled_pats)
                    if not matched:
                        yield ValidationError(
                            f"{pointer}/{name}", "additionalProperties", schema_id,
                            f"property {name!r} is not allowed",
                        )

        elif key == "propertyNames":
            if isinstance(instance, Mapping):
                for name in instance:
                    yield from _iter_errors(value, name, f"{pointer}/{name}", defs, schema_id)

        elif key == "minProperties":
            if isinstance(instance, Mapping) and len(instance) < value:
                yield ValidationError(pointer, "minProperties", schema_id,
                                       f"object has {len(instance)} properties, need >= {value}")

        elif key == "maxProperties":
            if isinstance(instance, Mapping) and len(instance) > value:
                yield ValidationError(pointer, "maxProperties", schema_id,
                                       f"object has {len(instance)} properties, need <= {value}")

        elif key == "dependentRequired":
            if isinstance(instance, Mapping):
                for trigger, reqs in value.items():
                    if trigger in instance:
                        for name in reqs:
                            if name not in instance:
                                yield ValidationError(
                                    f"{pointer}/{name}", "dependentRequired", schema_id,
                                    f"required by presence of {trigger!r}",
                                )

        elif key == "items":
            if isinstance(instance, list):
                for i, item in enumerate(instance):
                    yield from _iter_errors(value, item, f"{pointer}/{i}", defs, schema_id)

        elif key == "minItems":
            if isinstance(instance, list) and len(instance) < value:
                yield ValidationError(pointer, "minItems", schema_id,
                                       f"array has {len(instance)} items, need >= {value}")

        elif key == "maxItems":
            if isinstance(instance, list) and len(instance) > value:
                yield ValidationError(pointer, "maxItems", schema_id,
                                       f"array has {len(instance)} items, need <= {value}")

        elif key == "uniqueItems":
            if value and isinstance(instance, list):
                seen: set[bytes] = set()
                for i, item in enumerate(instance):
                    canon = json.dumps(item, sort_keys=True, separators=(",", ":")).encode("utf-8")
                    if canon in seen:
                        yield ValidationError(f"{pointer}/{i}", "uniqueItems", schema_id, "duplicate item")
                    seen.add(canon)

        elif key == "minimum":
            if _is_number(instance) and instance < value:
                yield ValidationError(pointer, "minimum", schema_id, f"{instance} < minimum {value}")

        elif key == "maximum":
            if _is_number(instance) and instance > value:
                yield ValidationError(pointer, "maximum", schema_id, f"{instance} > maximum {value}")

        elif key == "exclusiveMinimum":
            if _is_number(instance) and instance <= value:
                yield ValidationError(pointer, "exclusiveMinimum", schema_id,
                                       f"{instance} <= exclusiveMinimum {value}")

        elif key == "exclusiveMaximum":
            if _is_number(instance) and instance >= value:
                yield ValidationError(pointer, "exclusiveMaximum", schema_id,
                                       f"{instance} >= exclusiveMaximum {value}")

        elif key == "multipleOf":
            if _is_number(instance) and _to_fraction(instance) % _to_fraction(value) != 0:
                yield ValidationError(pointer, "multipleOf", schema_id, f"{instance} is not a multiple of {value}")

        elif key == "minLength":
            if isinstance(instance, str) and len(instance) < value:
                yield ValidationError(pointer, "minLength", schema_id, f"length {len(instance)} < {value}")

        elif key == "maxLength":
            if isinstance(instance, str) and len(instance) > value:
                yield ValidationError(pointer, "maxLength", schema_id, f"length {len(instance)} > {value}")

        elif key == "pattern":
            if isinstance(instance, str) and not _compile_pattern(value).search(instance):
                yield ValidationError(pointer, "pattern", schema_id, f"{instance!r} does not match {value!r}")

        elif key == "format":
            if isinstance(instance, str) and not _format_ok(value, instance):
                yield ValidationError(pointer, "format", schema_id, f"{instance!r} is not a valid {value}")

        elif key in ("oneOf", "anyOf"):
            sub_error_lists = [list(_iter_errors(sub, instance, pointer, defs, schema_id)) for sub in value]
            matches = sum(1 for errs in sub_error_lists if not errs)
            if key == "oneOf" and matches != 1:
                yield ValidationError(pointer, "oneOf", schema_id,
                                       f"expected exactly one matching subschema, got {matches}")
            elif key == "anyOf" and matches < 1:
                yield ValidationError(pointer, "anyOf", schema_id, "no subschema matched")

        elif key == "allOf":
            for sub in value:
                yield from _iter_errors(sub, instance, pointer, defs, schema_id)

        elif key == "not":
            sub_errors = list(_iter_errors(value, instance, pointer, defs, schema_id))
            if not sub_errors:
                yield ValidationError(pointer, "not", schema_id, "instance matched the 'not' subschema")

        elif key == "if":
            if_errors = list(_iter_errors(value, instance, pointer, defs, schema_id))
            if not if_errors:
                if "then" in schema:
                    yield from _iter_errors(schema["then"], instance, pointer, defs, schema_id)
            elif "else" in schema:
                yield from _iter_errors(schema["else"], instance, pointer, defs, schema_id)

        elif key in ("then", "else"):
            continue  # applied only via "if", above

        elif key in ("$schema", "$id", "title", "description", "examples", "$comment", "$defs"):
            continue  # annotations / containers, not validated

        else:  # pragma: no cover — Schema() already rejected anything else at load time
            raise UnsupportedKeyword(f"unsupported keyword encountered during validation: {key!r}")


class Schema:
    """A compiled JSON Schema (stdlib subset, contract §3.2)."""

    def __init__(self, id: str, raw: Mapping[str, Any]) -> None:  # noqa: A002
        _check_root(raw)
        self.id = id
        self.raw = raw
        self._defs: Mapping[str, Any] = raw.get("$defs", {})
        _walk(raw, self._defs)

    def validate(self, instance: Any) -> None:
        for err in self.iter_errors(instance):
            raise err

    def iter_errors(self, instance: Any) -> Iterator[ValidationError]:
        yield from _iter_errors(self.raw, instance, "", self._defs, self.id)


_SCHEMA_CACHE: dict[str, Schema] = {}


def load_schema(name: str) -> Schema:
    if name in _SCHEMA_CACHE:
        return _SCHEMA_CACHE[name]
    if name not in SCHEMA_NAMES:
        raise SchemaError(f"load_schema: {name!r} is not a known schema name; SCHEMA_NAMES={SCHEMA_NAMES!r}")
    path = schema_dir() / f"{name}.schema.json"
    if not path.is_file():
        raise SchemaError(f"load_schema: schema file not found: {path}")
    raw = load_json(path)
    schema_id = raw.get("$id", name) if isinstance(raw, Mapping) else name
    schema = Schema(id=schema_id, raw=raw)
    _SCHEMA_CACHE[name] = schema
    return schema


def load_json(path: str | os.PathLike[str]) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def dump_json(path: str | os.PathLike[str], obj: Any, *, canonical: bool = True) -> None:
    path = pathlib.Path(path)
    tmp = pathlib.Path(str(path) + ".tmp")
    if canonical:
        text = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    else:
        text = json.dumps(obj, indent=2, ensure_ascii=False)
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def load_and_validate(path: str | os.PathLike[str], schema: str) -> dict[str, Any]:
    instance = load_json(path)
    load_schema(schema).validate(instance)
    return instance


def read_jsonl(path: str | os.PathLike[str]) -> Iterator[dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def append_jsonl(path: str | os.PathLike[str], obj: Mapping[str, Any]) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        line = (json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
        os.write(fd, line)
    finally:
        os.close(fd)


def sha256_file(path: str | os.PathLike[str]) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
