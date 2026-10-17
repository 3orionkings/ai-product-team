"""Identifier, hash and timestamp helpers shared by every controller module.

Ids are ``<prefix>_<26 lowercase base32 chars>`` from 16 random bytes. Hashes are SHA-256 hex digests;
JSON is hashed in canonical form (sorted keys, compact separators, UTF-8 preserved). ``now()`` is the
single clock; tests may monkeypatch ``_clock``.
"""

from __future__ import annotations

import base64
import datetime as _dt
import hashlib
import json
import os
from typing import Any, Callable

PREFIXES: frozenset[str] = frozenset(
    {"case", "run", "task", "disp", "node", "ver", "edge", "evt", "rcpt", "imp", "wo", "plan", "chal"}
)


def new_id(prefix: str) -> str:
    """Return a fresh id for the given prefix. Unknown prefixes raise ``ValueError``."""
    if prefix not in PREFIXES:
        raise ValueError(f"unknown id prefix: {prefix!r}")
    raw = base64.b32encode(os.urandom(16)).decode("ascii").lower().rstrip("=")
    return f"{prefix}_{raw}"


def canonical_json(obj: Any) -> str:
    """Serialise ``obj`` deterministically for hashing and comparison."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_bytes(data: bytes) -> str:
    """Hex SHA-256 of raw bytes."""
    return hashlib.sha256(data).hexdigest()


def sha256_json(obj: Any) -> str:
    """Hex SHA-256 of the canonical JSON form of ``obj``."""
    return sha256_bytes(canonical_json(obj).encode("utf-8"))


def sha256_file(path: str | os.PathLike[str]) -> str:
    """Hex SHA-256 of a file's contents, streamed."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _default_clock() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


_clock: Callable[[], _dt.datetime] = _default_clock


def now() -> str:
    """Current UTC time as ISO-8601 with millisecond precision and a ``Z`` suffix."""
    t = _clock().astimezone(_dt.timezone.utc)
    return t.strftime("%Y-%m-%dT%H:%M:%S.") + f"{t.microsecond // 1000:03d}Z"


def parse_time(value: str) -> _dt.datetime:
    """Parse an ISO-8601 timestamp (with ``Z`` or offset) into an aware datetime."""
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return _dt.datetime.fromisoformat(value)
