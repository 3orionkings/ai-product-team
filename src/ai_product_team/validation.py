"""JSON Schema (Draft 2020-12 subset) validator and schema loader.

Single responsibility: structural validation of controller records against the schemas in ``schemas/``.
The module implements exactly the keyword subset fixed by ``docs/architecture/controller-contracts.md``
section 2 and refuses every other keyword, so a schema that relies on behaviour this validator does not
implement fails loudly instead of silently accepting instances.

Supported keywords
    ``$schema``, ``$id``, ``title``, ``description``, ``$defs``, ``$ref`` (local ``#`` / ``#/...`` only),
    ``type`` (string or list; ``integer`` is distinct from ``number``), ``properties``, ``required``,
    ``additionalProperties`` (boolean or schema), ``enum``, ``const``, ``items`` (single schema),
    ``minItems``, ``maxItems``, ``uniqueItems``, ``pattern`` (Python ``re.search``), ``minLength``,
    ``maxLength``, ``minimum``, ``maximum``, ``format`` (accepted and not enforced, except ``date-time``
    which must parse as an RFC 3339 timestamp with a zone), ``oneOf``, ``anyOf``, ``allOf``, ``not``,
    ``default`` (ignored) and ``examples`` (ignored).

Error strings
    Every instance error is ``"<json-pointer>: <message>"``. The pointer (RFC 6901) locates the offending
    value in the *instance*; the root instance is rendered as ``"/"``. A missing required property is
    reported at the pointer where it would live (``"/budget/max_steps: 'max_steps' is a required
    property"``); a forbidden additional property is reported at its own pointer.

Schema problems (an unsupported keyword, an unresolvable or non-local ``$ref``, a malformed keyword value)
are not instance errors: they raise :class:`~ai_product_team.errors.ValidationError` immediately so that a
broken schema can never be mistaken for a valid instance.
"""

from __future__ import annotations

import datetime as _dt
import json
import re
import threading
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from ai_product_team.errors import NotFoundError, ValidationError

__all__ = [
    "SCHEMAS_DIR",
    "SCHEMA_SUFFIX",
    "SUPPORTED_KEYWORDS",
    "load_schema",
    "validate",
    "ensure_valid",
    "schema_keyword_errors",
]

#: Directory holding ``<name>.schema.json`` files (repository ``schemas/``). Tests may rebind this.
SCHEMAS_DIR: Path = Path(__file__).resolve().parents[2] / "schemas"
SCHEMA_SUFFIX: str = ".schema.json"

#: The complete keyword subset. Anything else in a schema is an error, never silently ignored.
SUPPORTED_KEYWORDS: frozenset[str] = frozenset(
    {
        "$schema",
        "$id",
        "title",
        "description",
        "$defs",
        "$ref",
        "type",
        "properties",
        "required",
        "additionalProperties",
        "enum",
        "const",
        "items",
        "minItems",
        "maxItems",
        "uniqueItems",
        "pattern",
        "minLength",
        "maxLength",
        "minimum",
        "maximum",
        "format",
        "oneOf",
        "anyOf",
        "allOf",
        "not",
        "default",
        "examples",
    }
)

_TYPE_NAMES: frozenset[str] = frozenset({"null", "boolean", "integer", "number", "string", "array", "object"})
_NAME_RE = re.compile(r"[a-z][a-z0-9-]*")

_SCHEMA_CACHE: dict[str, dict[str, Any]] = {}
_REGEX_CACHE: dict[str, re.Pattern[str]] = {}
_LOCK = threading.Lock()


# --------------------------------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------------------------------


def load_schema(name: str) -> dict[str, Any]:
    """Load and cache ``schemas/<name>.schema.json``.

    The returned dict is the cached object itself and must be treated as read-only. Raises
    :class:`NotFoundError` when no such schema exists and :class:`ValidationError` when the file is not
    valid JSON, is not an object, or uses a keyword outside :data:`SUPPORTED_KEYWORDS`.
    """
    if not isinstance(name, str) or not _NAME_RE.fullmatch(name):
        raise NotFoundError(f"no schema named {name!r}", details={"name": name})
    with _LOCK:
        cached = _SCHEMA_CACHE.get(name)
    if cached is not None:
        return cached
    path = SCHEMAS_DIR / f"{name}{SCHEMA_SUFFIX}"
    if not path.is_file():
        raise NotFoundError(f"no schema named {name!r}", details={"name": name, "path": str(path)})
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(
            f"schema {name!r} could not be read: {exc}", details={"name": name, "path": str(path)}
        ) from exc
    if not isinstance(schema, dict):
        raise ValidationError(
            f"schema {name!r} must be a JSON object", details={"name": name, "path": str(path)}
        )
    problems = schema_keyword_errors(schema)
    if problems:
        raise ValidationError(
            f"schema {name!r} uses unsupported keywords",
            errors=problems,
            details={"name": name, "path": str(path)},
        )
    with _LOCK:
        return _SCHEMA_CACHE.setdefault(name, schema)


def validate(instance: Any, schema: dict[str, Any] | bool, *, root: dict[str, Any] | None = None) -> list[str]:
    """Validate ``instance`` against ``schema`` and return every error as ``"<json-pointer>: <message>"``.

    ``root`` is the document that local ``$ref`` pointers resolve against; it defaults to ``schema``.
    An empty list means the instance is structurally valid. Schema defects raise :class:`ValidationError`.
    """
    if root is None:
        root = schema if isinstance(schema, dict) else {}
    if not isinstance(root, dict):
        raise ValidationError("root schema must be a JSON object", details={"got": _type_name(root)})
    errors: list[str] = []
    _validate(instance, schema, "", _Context(root), errors)
    return errors


def ensure_valid(instance: Any, schema_name: str) -> None:
    """Validate ``instance`` against the named schema; raise :class:`ValidationError` listing all errors."""
    schema = load_schema(schema_name)
    errors = validate(instance, schema)
    if errors:
        raise ValidationError(
            f"{schema_name}: {len(errors)} validation error(s)",
            errors=errors,
            details={"schema": schema_name},
        )


def schema_keyword_errors(schema: Any, pointer: str = "") -> list[str]:
    """Walk a schema and return ``"<schema-pointer>: unsupported keyword 'x'"`` for every foreign keyword.

    The walk is structure-aware: the keys under ``properties`` and ``$defs`` are names, not keywords, and
    the values of ``enum``, ``const``, ``default`` and ``examples`` are data. An empty list means the schema
    uses only the supported subset.
    """
    out: list[str] = []
    _walk_schema(schema, pointer, out)
    return out


# --------------------------------------------------------------------------------------------------
# Schema walking
# --------------------------------------------------------------------------------------------------


def _walk_schema(schema: Any, ptr: str, out: list[str]) -> None:
    if isinstance(schema, bool):
        return
    if not isinstance(schema, dict):
        out.append(_fmt(ptr, f"schema must be an object or boolean, got {_type_name(schema)}"))
        return
    for key, value in schema.items():
        kptr = _join(ptr, key)
        if key not in SUPPORTED_KEYWORDS:
            out.append(_fmt(kptr, f"unsupported keyword {key!r}"))
            continue
        if key in ("properties", "$defs"):
            if isinstance(value, dict):
                for name, sub in value.items():
                    _walk_schema(sub, _join(kptr, name), out)
            else:
                out.append(_fmt(kptr, f"{key!r} must be an object"))
        elif key in ("items", "not"):
            _walk_schema(value, kptr, out)
        elif key == "additionalProperties":
            if not isinstance(value, bool):
                _walk_schema(value, kptr, out)
        elif key in ("oneOf", "anyOf", "allOf"):
            if isinstance(value, list):
                for index, sub in enumerate(value):
                    _walk_schema(sub, _join(kptr, str(index)), out)
            else:
                out.append(_fmt(kptr, f"{key!r} must be an array"))


# --------------------------------------------------------------------------------------------------
# Instance validation
# --------------------------------------------------------------------------------------------------


class _Context:
    """Per-call state: the ``$ref`` root and the set of active ``(ref, instance-pointer)`` pairs."""

    __slots__ = ("root", "active")

    def __init__(self, root: dict[str, Any]) -> None:
        self.root = root
        self.active: set[tuple[str, str]] = set()


def _validate(instance: Any, schema: Any, ptr: str, ctx: _Context, errors: list[str]) -> None:
    if schema is True:
        return
    if schema is False:
        errors.append(_fmt(ptr, "false schema does not allow any value"))
        return
    if not isinstance(schema, dict):
        raise ValidationError(
            f"schema must be an object or boolean, got {_type_name(schema)}",
            details={"instance_pointer": ptr or "/"},
        )
    unsupported = sorted(k for k in schema if k not in SUPPORTED_KEYWORDS)
    if unsupported:
        raise ValidationError(
            f"unsupported schema keyword(s): {unsupported}",
            errors=[_fmt(ptr, f"unsupported schema keyword {k!r}") for k in unsupported],
            details={"keywords": unsupported, "instance_pointer": ptr or "/"},
        )

    if "$ref" in schema:
        ref = schema["$ref"]
        target = _resolve_ref(ref, ctx.root)
        key = (ref, ptr)
        if key in ctx.active:
            raise ValidationError(
                f"circular $ref {ref!r} makes no progress", details={"ref": ref, "instance_pointer": ptr or "/"}
            )
        ctx.active.add(key)
        try:
            _validate(instance, target, ptr, ctx, errors)
        finally:
            ctx.active.discard(key)

    if "type" in schema:
        _check_type(instance, schema["type"], ptr, errors)

    if "enum" in schema:
        choices = schema["enum"]
        if not isinstance(choices, list):
            raise _schema_defect("enum", "must be an array", ptr)
        if not any(_json_equal(instance, c) for c in choices):
            errors.append(_fmt(ptr, f"{_short(instance)} is not one of {choices!r}"))

    if "const" in schema and not _json_equal(instance, schema["const"]):
        errors.append(_fmt(ptr, f"{_short(instance)} is not the constant {schema['const']!r}"))

    if isinstance(instance, dict):
        _check_object(instance, schema, ptr, ctx, errors)
    elif isinstance(instance, list):
        _check_array(instance, schema, ptr, ctx, errors)
    elif isinstance(instance, str):
        _check_string(instance, schema, ptr, errors)
    elif _is_number(instance):
        _check_number(instance, schema, ptr, errors)

    if "allOf" in schema:
        for index, sub in enumerate(_subschema_list(schema, "allOf", ptr)):
            _validate(instance, sub, ptr, ctx, errors)

    if "anyOf" in schema:
        branches = [_collect(instance, sub, ptr, ctx) for sub in _subschema_list(schema, "anyOf", ptr)]
        if not any(not b for b in branches):
            errors.append(_fmt(ptr, "is not valid under any anyOf schema: " + _summarise(branches)))

    if "oneOf" in schema:
        branches = [_collect(instance, sub, ptr, ctx) for sub in _subschema_list(schema, "oneOf", ptr)]
        matches = sum(1 for b in branches if not b)
        if matches == 0:
            errors.append(_fmt(ptr, "is not valid under any oneOf schema: " + _summarise(branches)))
        elif matches > 1:
            errors.append(_fmt(ptr, f"is valid under {matches} oneOf schemas; exactly one is required"))

    if "not" in schema:
        if not _collect(instance, schema["not"], ptr, ctx):
            errors.append(_fmt(ptr, "must not be valid under the 'not' schema"))


def _check_type(instance: Any, declared: Any, ptr: str, errors: list[str]) -> None:
    types = [declared] if isinstance(declared, str) else declared
    if not isinstance(types, list) or not types or not all(isinstance(t, str) for t in types):
        raise _schema_defect("type", "must be a type name or a non-empty array of type names", ptr)
    unknown = [t for t in types if t not in _TYPE_NAMES]
    if unknown:
        raise _schema_defect("type", f"unknown type name(s) {unknown!r}", ptr)
    if not any(_is_type(instance, t) for t in types):
        errors.append(_fmt(ptr, f"{_short(instance)} is not of type {', '.join(repr(t) for t in types)}"))


def _check_object(instance: dict[str, Any], schema: dict[str, Any], ptr: str, ctx: _Context, errors: list[str]) -> None:
    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        raise _schema_defect("properties", "must be an object", ptr)
    required = schema.get("required", [])
    if not isinstance(required, list) or not all(isinstance(r, str) for r in required):
        raise _schema_defect("required", "must be an array of strings", ptr)
    for name in required:
        if name not in instance:
            errors.append(_fmt(_join(ptr, name), f"{name!r} is a required property"))
    for name, sub in properties.items():
        if name in instance:
            _validate(instance[name], sub, _join(ptr, name), ctx, errors)
    if "additionalProperties" in schema:
        extra_schema = schema["additionalProperties"]
        if not isinstance(extra_schema, (bool, dict)):
            raise _schema_defect("additionalProperties", "must be a boolean or a schema", ptr)
        for name, value in instance.items():
            if name in properties:
                continue
            if extra_schema is False:
                errors.append(_fmt(_join(ptr, name), f"additional property {name!r} is not allowed"))
            elif extra_schema is not True:
                _validate(value, extra_schema, _join(ptr, name), ctx, errors)


def _check_array(instance: list[Any], schema: dict[str, Any], ptr: str, ctx: _Context, errors: list[str]) -> None:
    if "items" in schema:
        item_schema = schema["items"]
        if not isinstance(item_schema, (bool, dict)):
            raise _schema_defect("items", "must be a single schema", ptr)
        for index, item in enumerate(instance):
            _validate(item, item_schema, _join(ptr, str(index)), ctx, errors)
    count = len(instance)
    if "minItems" in schema:
        bound = _non_negative_int(schema, "minItems", ptr)
        if count < bound:
            errors.append(_fmt(ptr, f"array has {count} item(s) but minItems is {bound}"))
    if "maxItems" in schema:
        bound = _non_negative_int(schema, "maxItems", ptr)
        if count > bound:
            errors.append(_fmt(ptr, f"array has {count} item(s) but maxItems is {bound}"))
    if "uniqueItems" in schema:
        flag = schema["uniqueItems"]
        if not isinstance(flag, bool):
            raise _schema_defect("uniqueItems", "must be a boolean", ptr)
        if flag and not _all_unique(instance):
            errors.append(_fmt(ptr, "array items are not unique"))


def _check_string(instance: str, schema: dict[str, Any], ptr: str, errors: list[str]) -> None:
    if "pattern" in schema:
        pattern = schema["pattern"]
        if not isinstance(pattern, str):
            raise _schema_defect("pattern", "must be a string", ptr)
        if _regex(pattern, ptr).search(instance) is None:
            errors.append(_fmt(ptr, f"{_short(instance)} does not match pattern {pattern!r}"))
    length = len(instance)
    if "minLength" in schema:
        bound = _non_negative_int(schema, "minLength", ptr)
        if length < bound:
            errors.append(_fmt(ptr, f"{_short(instance)} is shorter than minLength {bound}"))
    if "maxLength" in schema:
        bound = _non_negative_int(schema, "maxLength", ptr)
        if length > bound:
            errors.append(_fmt(ptr, f"{_short(instance)} is longer than maxLength {bound}"))
    if "format" in schema:
        fmt = schema["format"]
        if not isinstance(fmt, str):
            raise _schema_defect("format", "must be a string", ptr)
        if fmt == "date-time" and not _is_date_time(instance):
            errors.append(_fmt(ptr, f"{_short(instance)} is not a valid date-time"))


def _check_number(instance: int | float, schema: dict[str, Any], ptr: str, errors: list[str]) -> None:
    if "minimum" in schema:
        bound = _numeric(schema, "minimum", ptr)
        if instance < bound:
            errors.append(_fmt(ptr, f"{instance!r} is less than minimum {bound!r}"))
    if "maximum" in schema:
        bound = _numeric(schema, "maximum", ptr)
        if instance > bound:
            errors.append(_fmt(ptr, f"{instance!r} is greater than maximum {bound!r}"))


def _collect(instance: Any, schema: Any, ptr: str, ctx: _Context) -> list[str]:
    sub: list[str] = []
    _validate(instance, schema, ptr, ctx, sub)
    return sub


def _subschema_list(schema: dict[str, Any], key: str, ptr: str) -> list[Any]:
    value = schema[key]
    if not isinstance(value, list) or not value:
        raise _schema_defect(key, "must be a non-empty array of schemas", ptr)
    return value


def _summarise(branches: list[list[str]]) -> str:
    parts = []
    for index, branch in enumerate(branches):
        first = branch[0] if branch else "ok"
        parts.append(f"[{index}] {first}")
    return "; ".join(parts)


# --------------------------------------------------------------------------------------------------
# $ref resolution
# --------------------------------------------------------------------------------------------------


def _resolve_ref(ref: Any, root: dict[str, Any]) -> Any:
    if not isinstance(ref, str) or not (ref == "#" or ref.startswith("#/")):
        raise ValidationError(
            f"only local $ref pointers ('#' or '#/...') are supported, got {ref!r}", details={"ref": ref}
        )
    node: Any = root
    if ref == "#":
        return node
    for raw in ref[2:].split("/"):
        token = unquote(raw).replace("~1", "/").replace("~0", "~")
        if isinstance(node, dict) and token in node:
            node = node[token]
        elif isinstance(node, list) and token.isdigit() and int(token) < len(node):
            node = node[int(token)]
        else:
            raise ValidationError(f"unresolvable $ref {ref!r}", details={"ref": ref, "token": token})
    return node


# --------------------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------------------


def _fmt(ptr: str, message: str) -> str:
    return f"{ptr or '/'}: {message}"


def _join(ptr: str, token: str) -> str:
    return f"{ptr}/{token.replace('~', '~0').replace('/', '~1')}"


def _schema_defect(keyword: str, problem: str, ptr: str) -> ValidationError:
    return ValidationError(
        f"schema keyword {keyword!r} {problem}", details={"keyword": keyword, "instance_pointer": ptr or "/"}
    )


def _non_negative_int(schema: dict[str, Any], key: str, ptr: str) -> int:
    value = schema[key]
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise _schema_defect(key, "must be a non-negative integer", ptr)
    return value


def _numeric(schema: dict[str, Any], key: str, ptr: str) -> int | float:
    value = schema[key]
    if not _is_number(value):
        raise _schema_defect(key, "must be a number", ptr)
    return value


def _regex(pattern: str, ptr: str) -> re.Pattern[str]:
    compiled = _REGEX_CACHE.get(pattern)
    if compiled is None:
        try:
            compiled = re.compile(pattern)
        except re.error as exc:
            raise _schema_defect("pattern", f"is not a valid regular expression: {exc}", ptr) from exc
        _REGEX_CACHE[pattern] = compiled
    return compiled


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_type(value: Any, type_name: str) -> bool:
    if type_name == "null":
        return value is None
    if type_name == "boolean":
        return isinstance(value, bool)
    if type_name == "integer":
        return (isinstance(value, int) and not isinstance(value, bool)) or (
            isinstance(value, float) and value.is_integer()
        )
    if type_name == "number":
        return _is_number(value)
    if type_name == "string":
        return isinstance(value, str)
    if type_name == "array":
        return isinstance(value, list)
    return isinstance(value, dict)  # "object"


def _type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _json_equal(a: Any, b: Any) -> bool:
    """JSON equality: booleans never equal numbers, 1 == 1.0, containers compare structurally."""
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    if _is_number(a) and _is_number(b):
        return a == b
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_json_equal(x, y) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_json_equal(a[k], b[k]) for k in a)
    if type(a) is not type(b):
        return False
    return a == b


def _all_unique(items: list[Any]) -> bool:
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if _json_equal(items[i], items[j]):
                return False
    return True


def _is_date_time(value: str) -> bool:
    if "T" not in value and "t" not in value:
        return False
    try:
        parsed = _dt.datetime.fromisoformat(value)
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _short(value: Any, limit: int = 120) -> str:
    text = repr(value)
    return text if len(text) <= limit else text[: limit - 3] + "..."
