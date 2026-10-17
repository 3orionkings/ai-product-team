"""Authoritative per-case persistence: SQLite state, content-addressed blobs, events, versions and edges.

Single responsibility: durable, transactional storage of controller records for one case directory. The
store checks structure (schemas, enumerations, references, state versions, idempotency) and never judges
the content it stores. It implements ``docs/architecture/controller-contracts.md`` section 5 and the
section 14 addendum on operational tables and receipts.

Layout of a case directory::

    <case_dir>/state.sqlite3      authoritative state (WAL, foreign keys on, busy_timeout 5000 ms)
    <case_dir>/blobs/<sha256>     content-addressed immutable blobs
    <case_dir>/receipts/          stdout/stderr of executed commands (written by receipts.py)
    <case_dir>/proposals/         proposal-only write scope for workers
    <case_dir>/reports/           derived reports
    <case_dir>/exports/           default export location
    <case_dir>/backups/           automatic pre-migration backups

Invariants
    * A store is refused under Dropbox, OneDrive, Google Drive, iCloud or a network mount (PolicyError).
    * Every write runs inside :meth:`CaseStore.transaction` (``BEGIN IMMEDIATE``; rollback on exception).
    * ``node_versions`` and ``events`` are append-only; SQLite triggers abort UPDATE and DELETE.
    * ``append_event`` enforces the optimistic ``expected_state_version`` check and idempotency keys.
    * ``node_current`` is the only mutable projection; ``set_current`` records ``node.current_changed``.
    * Backups use ``sqlite3.Connection.backup``, never a file copy. Export/import round-trips every id,
      version, edge, event and blob hash. Schema migrations run in one transaction after a backup.
"""

from __future__ import annotations

import contextlib
import dataclasses
import importlib.resources
import json
import os
import re
import shutil
import sqlite3
from pathlib import Path
from typing import Any, Iterator, Sequence

from ai_product_team.errors import ConflictError, NotFoundError, PolicyError, ValidationError
from ai_product_team.ids import new_id, now, sha256_bytes, sha256_json
from ai_product_team.validation import ensure_valid

__all__ = [
    "SCHEMA_VERSION",
    "MIGRATIONS",
    "NODE_KINDS",
    "RELATIONS",
    "EDGE_STATUSES",
    "IMPACT_POLICIES",
    "APPLICABILITIES",
    "STATUS_ENUMS",
    "OPERATIONAL_TABLES",
    "JSON_COLUMNS",
    "SYNCED_PATH_MARKERS",
    "Event",
    "CaseStore",
    "load_ddl",
    "is_synced_or_network_path",
]

# --------------------------------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------------------------------

#: Current DDL version written to ``meta.schema_version`` by :meth:`CaseStore.create`.
SCHEMA_VERSION: int = 1

#: Ordered migrations ``(from_version, to_version, statements)``. ``statements`` is one SQL statement or a
#: sequence of statements; they run inside a single transaction after an automatic backup. Empty in M1.
MIGRATIONS: list[tuple[int, int, str | Sequence[str]]] = []

NODE_KINDS: frozenset[str] = frozenset(
    {"source", "claim", "requirement", "proposal", "decision", "artifact", "validation", "challenge", "review", "approval"}
)
RELATIONS: frozenset[str] = frozenset(
    {"supports", "contradicts", "implements", "verifies", "derived_from", "supersedes", "depends_on"}
)
EDGE_STATUSES: frozenset[str] = frozenset({"proposed", "accepted", "rejected"})
IMPACT_POLICIES: frozenset[str] = frozenset({"review", "invalidate_applicability", "none"})
APPLICABILITIES: frozenset[str] = frozenset({"current", "historical", "invalidated", "unestablished"})

#: Status vocabularies fixed by contract section 3 for the kinds that have one. Other kinds accept any
#: non-empty status string in :meth:`CaseStore.set_current`.
STATUS_ENUMS: dict[str, frozenset[str]] = {
    "claim": frozenset({"proposed", "supported", "contested", "unsupported", "superseded"}),
    "requirement": frozenset({"proposed", "approved", "retired", "superseded"}),
    "decision": frozenset(
        {"proposed", "under_review", "accepted", "rejected", "deferred", "human_required", "review_required", "superseded"}
    ),
    "artifact": frozenset(
        {"proposed", "implemented_not_verified", "verified_for_scope", "changes_required", "revalidation_required", "archived"}
    ),
    "validation": frozenset({"passed", "failed", "blocked", "not_run"}),
    "challenge": frozenset({"open", "answered", "upheld", "withdrawn", "unresolved"}),
}

#: The only tables the generic row operations accept (contract section 14 addendum).
OPERATIONAL_TABLES: tuple[str, ...] = ("runs", "tasks", "dispatches", "receipts", "impact_queue", "budgets")

#: Per-table JSON-typed columns, (de)serialised automatically by insert/update/get/query and export/import.
JSON_COLUMNS: dict[str, tuple[str, ...]] = {
    "runs": ("budget", "limitations"),
    "tasks": ("dependencies", "input_refs", "output_paths", "snapshot", "envelope"),
    "dispatches": ("metadata",),
    "receipts": ("payload",),
    "impact_queue": ("path",),
    "budgets": (),
}

#: Path components that mark a synced or cloud-mirrored folder (matched case-insensitively).
SYNCED_PATH_MARKERS: tuple[str, ...] = (
    "dropbox",
    "onedrive",
    "google drive",
    "googledrive",
    "icloud",
    "com~apple~clouddocs",
    "mobile documents",
)

#: Filesystem types treated as network mounts when ``/proc/mounts`` is readable (Linux best effort).
_NETWORK_FS_TYPES: frozenset[str] = frozenset(
    {"nfs", "nfs4", "cifs", "smbfs", "smb3", "afpfs", "webdav", "davfs", "fuse.sshfs", "9p", "ncpfs", "coda"}
)

# Every physical table, in dependency order (parents before children) for export and import.
_ALL_TABLES: tuple[str, ...] = (
    "meta",
    "cases",
    "runs",
    "tasks",
    "dispatches",
    "nodes",
    "node_versions",
    "node_current",
    "edges",
    "events",
    "receipts",
    "impact_queue",
    "budgets",
)

# JSON columns of the core tables (the operational ones come from JSON_COLUMNS). Used by export/import.
_CORE_JSON_COLUMNS: dict[str, tuple[str, ...]] = {
    "cases": ("payload",),
    "node_versions": ("payload",),
    "events": ("payload_refs", "payload"),
}

# Catch-all column holding keys the operational tables have no dedicated column for.
_EXTRA = "extra_json"

# Id prefix minted when an operational row arrives without an ``id``. ``budgets`` falls back to ``run_id``.
_TABLE_ID_PREFIX: dict[str, str] = {
    "runs": "run",
    "tasks": "task",
    "dispatches": "disp",
    "receipts": "rcpt",
    "impact_queue": "imp",
}

_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_EXPORT_FORMAT = "aipt-case-export"
_EXPORT_FORMAT_VERSION = 1


# --------------------------------------------------------------------------------------------------
# Public helpers
# --------------------------------------------------------------------------------------------------


def load_ddl() -> str:
    """Return the DDL text of ``schema.sql`` packaged next to this module."""
    return importlib.resources.files("ai_product_team").joinpath("schema.sql").read_text(encoding="utf-8")


def is_synced_or_network_path(path: Path) -> bool:
    """Best-effort check that ``path`` lives under a sync folder or a network mount.

    Matches any resolved path component against :data:`SYNCED_PATH_MARKERS`, then (Linux only) looks up
    the longest mount-point prefix in ``/proc/mounts`` and flags network filesystem types. It never raises
    for a missing path: the deepest existing ancestor is what gets resolved.
    """
    resolved = _resolve_lenient(Path(path))
    lowered = [part.lower() for part in resolved.parts]
    for part in lowered:
        for marker in SYNCED_PATH_MARKERS:
            if marker in part:
                return True
    return _on_network_mount(resolved)


# --------------------------------------------------------------------------------------------------
# Event record
# --------------------------------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class Event:
    """One immutable, sequenced event as stored in the ``events`` table.

    ``payload`` is the full event payload object and ``payload_sha256`` its canonical hash, which is what
    idempotent replays are compared against. Supports ``event["field"]`` for dict-style access.
    """

    id: str
    seq: int
    case_id: str
    type: str
    actor_role: str
    actor_task: str | None
    expected_state_version: int
    payload_refs: tuple[str, ...]
    payload: dict[str, Any]
    payload_sha256: str
    created_at: str
    idempotency_key: str

    def to_dict(self) -> dict[str, Any]:
        """Return the event as the JSON object described by ``schemas/event.schema.json``."""
        data = dataclasses.asdict(self)
        data["payload_refs"] = list(self.payload_refs)
        return data

    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]


# --------------------------------------------------------------------------------------------------
# CaseStore
# --------------------------------------------------------------------------------------------------


class CaseStore:
    """SQLite-backed store for one case directory. Use :meth:`create` or :meth:`open`, not ``__init__``."""

    SUBDIRS: tuple[str, ...] = ("blobs", "receipts", "proposals", "reports", "exports", "backups")

    def __init__(self, case_dir: Path) -> None:
        """Attach to the case directory and open ``state.sqlite3`` with the mandated pragmas.

        The directory must already exist; :meth:`create` makes it (after the synced-path policy check)
        and :meth:`open` verifies the database exists before constructing. Direct construction neither
        initialises the schema nor checks its version.
        """
        self.case_dir: Path = Path(case_dir)
        if not self.case_dir.is_dir():
            raise NotFoundError(f"case directory does not exist: {self.case_dir}", details={"case_dir": str(self.case_dir)})
        self.db_path: Path = self.case_dir / "state.sqlite3"
        self.blobs_dir: Path = self.case_dir / "blobs"
        self._depth: int = 0
        self._case_id: str | None = None
        self._conn: sqlite3.Connection = sqlite3.connect(str(self.db_path), isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._apply_pragmas()

    # ---------------------------------------------------------------------------------------------
    # Lifecycle
    # ---------------------------------------------------------------------------------------------

    @classmethod
    def create(cls, case_dir: Path, case_payload: dict[str, Any]) -> "CaseStore":
        """Create a new store at ``case_dir`` holding the case described by ``case_payload``.

        ``case_payload`` is a JSON object; a missing ``id`` is minted with prefix ``case``. Refuses with
        :class:`PolicyError` (``details.reason == "synced_or_network_filesystem"``) under a synced or
        network path, and with :class:`ConflictError` when a database already exists there.
        """
        case_dir = Path(case_dir)
        cls._refuse_synced(case_dir)
        if not isinstance(case_payload, dict):
            raise ValidationError("case_payload must be a JSON object", errors=["/: case payload is not an object"])
        payload = dict(case_payload)
        case_id = payload.get("id")
        if case_id is None:
            case_id = new_id("case")
            payload["id"] = case_id
        if not isinstance(case_id, str) or not case_id:
            raise ValidationError("case id must be a non-empty string", errors=["/id: case id is not a non-empty string"])
        if (case_dir / "state.sqlite3").exists():
            raise ConflictError(f"a case store already exists at {case_dir}", details={"case_dir": str(case_dir)})
        _ensure_dirs(case_dir, cls.SUBDIRS)
        store = cls(case_dir)
        try:
            store._conn.executescript(load_ddl())
            with store.transaction():
                store._conn.execute(
                    "INSERT INTO meta(key, value) VALUES ('schema_version', ?), ('created_at', ?), ('case_id', ?)",
                    (str(SCHEMA_VERSION), now(), case_id),
                )
                store._conn.execute(
                    "INSERT INTO cases(id, payload, state_version, created_at) VALUES (?, ?, 0, ?)",
                    (case_id, _dumps(payload), now()),
                )
        except Exception:
            store.close()
            raise
        store._case_id = case_id
        return store

    @classmethod
    def open(cls, case_dir: Path) -> "CaseStore":
        """Open an existing store, migrating an older schema (after a backup) and refusing a newer one."""
        case_dir = Path(case_dir)
        db_path = case_dir / "state.sqlite3"
        if not db_path.is_file():
            raise NotFoundError(f"no case store at {case_dir}", details={"case_dir": str(case_dir)})
        _ensure_dirs(case_dir, cls.SUBDIRS)
        store = cls(case_dir)
        try:
            found = store._read_schema_version()
            if found > SCHEMA_VERSION:
                raise ConflictError(
                    f"store schema version {found} is newer than supported version {SCHEMA_VERSION}",
                    details={"reason": "schema_version_unsupported", "found": found, "supported": SCHEMA_VERSION},
                )
            if found < SCHEMA_VERSION:
                store._migrate(found)
            store._case_id = store._load_case_id()
        except Exception:
            store.close()
            raise
        return store

    def close(self) -> None:
        """Roll back any open transaction and close the connection. Safe to call twice."""
        conn = getattr(self, "_conn", None)
        if conn is None:
            return
        try:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        conn.close()
        self._conn = None  # type: ignore[assignment]
        self._depth = 0

    def __enter__(self) -> "CaseStore":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    @property
    def connection(self) -> sqlite3.Connection:
        """The underlying connection, for read-only inspection by reports and tests."""
        return self._require_conn()

    @property
    def case_id(self) -> str:
        """Id of the single case this store holds."""
        if self._case_id is None:
            self._case_id = self._load_case_id()
        return self._case_id

    def case(self) -> dict[str, Any]:
        """Return ``{"id", "payload", "state_version", "created_at"}`` for the store's case."""
        row = self._require_conn().execute("SELECT * FROM cases WHERE id = ?", (self.case_id,)).fetchone()
        if row is None:
            raise NotFoundError("case row missing", details={"case_id": self.case_id})
        return {
            "id": row["id"],
            "payload": json.loads(row["payload"]),
            "state_version": int(row["state_version"]),
            "created_at": row["created_at"],
        }

    def schema_version(self) -> int:
        """Return ``meta.schema_version`` of the open database."""
        return self._read_schema_version()

    # ---------------------------------------------------------------------------------------------
    # Transactions
    # ---------------------------------------------------------------------------------------------

    @contextlib.contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Run the block in one write transaction (``BEGIN IMMEDIATE``), rolling back on any exception.

        Re-entrant: a nested block becomes a ``SAVEPOINT`` so a caught inner failure cannot leave partial
        writes in the outer transaction. A lock that outlasts ``busy_timeout`` raises :class:`ConflictError`.
        """
        conn = self._require_conn()
        if self._depth == 0:
            try:
                conn.execute("BEGIN IMMEDIATE")
            except sqlite3.OperationalError as exc:
                raise ConflictError(f"could not start transaction: {exc}", details={"reason": "database_locked"}) from exc
            self._depth = 1
            try:
                yield conn
            except BaseException:
                self._depth = 0
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
                raise
            else:
                self._depth = 0
                conn.execute("COMMIT")
        else:
            name = f"sp_{self._depth}"
            conn.execute(f"SAVEPOINT {name}")
            self._depth += 1
            try:
                yield conn
            except BaseException:
                self._depth -= 1
                conn.execute(f"ROLLBACK TO {name}")
                conn.execute(f"RELEASE {name}")
                raise
            else:
                self._depth -= 1
                conn.execute(f"RELEASE {name}")

    # ---------------------------------------------------------------------------------------------
    # State version and events
    # ---------------------------------------------------------------------------------------------

    def state_version(self) -> int:
        """Current optimistic state version of the case (one increment per appended event)."""
        row = self._require_conn().execute("SELECT state_version FROM cases WHERE id = ?", (self.case_id,)).fetchone()
        if row is None:
            raise NotFoundError("case row missing", details={"case_id": self.case_id})
        return int(row["state_version"])

    def append_event(
        self,
        type: str,
        payload: dict[str, Any],
        *,
        actor_role: str,
        actor_task: str | None = None,
        expected_state_version: int,
        idempotency_key: str,
        payload_refs: Sequence[str] = (),
    ) -> Event:
        """Append an event, enforcing the state-version check and idempotency.

        A replay (same ``idempotency_key``, same ``type`` and identical payload hash) returns the stored
        event without writing. The same key with a different type or payload raises :class:`ConflictError`
        (``details.reason == "idempotency_payload_mismatch"``). Otherwise ``expected_state_version`` must
        equal :meth:`state_version` or :class:`ConflictError` (``reason == "stale_state_version"``) is
        raised; on success the state version increments and the event gets the next ``seq``.
        """
        if not isinstance(payload, dict):
            raise ValidationError("event payload must be a JSON object", errors=["/payload: not an object"])
        if not isinstance(idempotency_key, str) or not idempotency_key:
            raise ValidationError("idempotency_key must be a non-empty string", errors=["/idempotency_key: empty"])
        payload_hash = sha256_json(payload)
        refs = [str(r) for r in payload_refs]
        with self.transaction() as conn:
            existing = conn.execute("SELECT * FROM events WHERE idempotency_key = ?", (idempotency_key,)).fetchone()
            if existing is not None:
                if existing["payload_sha256"] == payload_hash and existing["type"] == type:
                    return _row_to_event(existing)
                raise ConflictError(
                    f"idempotency key {idempotency_key!r} was already used with a different payload",
                    details={
                        "reason": "idempotency_payload_mismatch",
                        "idempotency_key": idempotency_key,
                        "existing_event_id": existing["id"],
                        "existing_type": existing["type"],
                    },
                )
            current = self.state_version()
            if expected_state_version != current:
                raise ConflictError(
                    f"stale state version: expected {expected_state_version}, store is at {current}",
                    details={"reason": "stale_state_version", "expected": expected_state_version, "actual": current},
                )
            seq_row = conn.execute("SELECT COALESCE(MAX(seq), 0) AS m FROM events WHERE case_id = ?", (self.case_id,)).fetchone()
            seq = int(seq_row["m"]) + 1
            record: dict[str, Any] = {
                "id": new_id("evt"),
                "seq": seq,
                "case_id": self.case_id,
                "type": type,
                "actor_role": actor_role,
                "actor_task": actor_task,
                "expected_state_version": expected_state_version,
                "payload_refs": refs,
                "payload": payload,
                "payload_sha256": payload_hash,
                "created_at": now(),
                "idempotency_key": idempotency_key,
            }
            ensure_valid(record, "event")
            try:
                conn.execute(
                    "INSERT INTO events(id, case_id, seq, type, actor_role, actor_task, expected_state_version, payload_refs,"
                    " payload, payload_sha256, created_at, idempotency_key) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        record["id"],
                        record["case_id"],
                        seq,
                        type,
                        actor_role,
                        actor_task,
                        expected_state_version,
                        _dumps(refs),
                        _dumps(payload),
                        payload_hash,
                        record["created_at"],
                        idempotency_key,
                    ),
                )
                conn.execute("UPDATE cases SET state_version = ? WHERE id = ?", (current + 1, self.case_id))
            except sqlite3.IntegrityError as exc:
                raise _translate_integrity(exc, "events") from exc
            return Event(
                id=record["id"],
                seq=seq,
                case_id=self.case_id,
                type=type,
                actor_role=actor_role,
                actor_task=actor_task,
                expected_state_version=expected_state_version,
                payload_refs=tuple(refs),
                payload=json.loads(_dumps(payload)),
                payload_sha256=payload_hash,
                created_at=record["created_at"],
                idempotency_key=idempotency_key,
            )

    def events(self, *, since_seq: int = 0, type: str | None = None) -> list[Event]:
        """Return events with ``seq > since_seq`` (optionally of one ``type``) in sequence order."""
        conn = self._require_conn()
        if type is None:
            rows = conn.execute("SELECT * FROM events WHERE case_id = ? AND seq > ? ORDER BY seq", (self.case_id, since_seq))
        else:
            rows = conn.execute(
                "SELECT * FROM events WHERE case_id = ? AND seq > ? AND type = ? ORDER BY seq", (self.case_id, since_seq, type)
            )
        return [_row_to_event(r) for r in rows.fetchall()]

    def get_event(self, event_id: str) -> Event:
        """Return one event by id or raise :class:`NotFoundError`."""
        row = self._require_conn().execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        if row is None:
            raise NotFoundError(f"no event {event_id!r}", details={"event_id": event_id})
        return _row_to_event(row)

    # ---------------------------------------------------------------------------------------------
    # Nodes and versions
    # ---------------------------------------------------------------------------------------------

    def new_node(self, kind: str, case_id: str) -> str:
        """Create a node of ``kind`` (one of :data:`NODE_KINDS`) for ``case_id`` and return its id."""
        self._check_kind(kind)
        if case_id != self.case_id:
            raise NotFoundError(f"unknown case {case_id!r}; this store holds {self.case_id!r}", details={"case_id": case_id})
        node_id = new_id("node")
        with self.transaction() as conn:
            conn.execute("INSERT INTO nodes(id, case_id, kind, created_at) VALUES (?,?,?,?)", (node_id, case_id, kind, now()))
        return node_id

    def get_node(self, node_id: str) -> dict[str, Any]:
        """Return ``{"id", "case_id", "kind", "created_at"}`` for a node or raise :class:`NotFoundError`."""
        row = self._require_conn().execute("SELECT * FROM nodes WHERE id = ?", (node_id,)).fetchone()
        if row is None:
            raise NotFoundError(f"no node {node_id!r}", details={"node_id": node_id})
        return dict(row)

    def put_version(
        self,
        node_id: str,
        payload: dict[str, Any],
        *,
        author_role: str,
        author_task: str | None = None,
        author_session: str | None = None,
    ) -> str:
        """Append an immutable version of ``node_id`` after validating ``payload`` against the kind's schema.

        ``content_hash`` is the SHA-256 of the canonical payload. The new version does not become current;
        call :meth:`set_current` for that. Returns the version id.
        """
        node = self.get_node(node_id)
        kind = node["kind"]
        if not isinstance(payload, dict):
            raise ValidationError(f"{kind} payload must be a JSON object", errors=["/: payload is not an object"])
        ensure_valid(payload, kind)
        if not isinstance(author_role, str) or not author_role:
            raise ValidationError("author_role must be a non-empty string", errors=["/author_role: empty"])
        text = _dumps(payload)
        content_hash = sha256_bytes(text.encode("utf-8"))
        version_id = new_id("ver")
        with self.transaction() as conn:
            seq_row = conn.execute("SELECT COALESCE(MAX(seq), 0) AS m FROM node_versions WHERE node_id = ?", (node_id,)).fetchone()
            seq = int(seq_row["m"]) + 1
            try:
                conn.execute(
                    "INSERT INTO node_versions(id, node_id, seq, kind, payload, content_hash, author_role, author_task,"
                    " author_session, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (version_id, node_id, seq, kind, text, content_hash, author_role, author_task, author_session, now()),
                )
            except sqlite3.IntegrityError as exc:
                raise _translate_integrity(exc, "node_versions") from exc
        return version_id

    def get_version(self, version_id: str) -> dict[str, Any]:
        """Return a version row with its decoded ``payload`` or raise :class:`NotFoundError`.

        Keys: ``id``, ``version_id`` (alias), ``node_id``, ``case_id``, ``kind``, ``seq``, ``payload``,
        ``content_hash``, ``author_role``, ``author_task``, ``author_session``, ``created_at``.
        """
        row = self._require_conn().execute(
            "SELECT v.*, n.case_id FROM node_versions v JOIN nodes n ON n.id = v.node_id WHERE v.id = ?", (version_id,)
        ).fetchone()
        if row is None:
            raise NotFoundError(f"no version {version_id!r}", details={"version_id": version_id})
        return _row_to_version(row)

    def versions_of(self, node_id: str) -> list[dict[str, Any]]:
        """Return every version of ``node_id`` in ``seq`` order (same shape as :meth:`get_version`)."""
        self.get_node(node_id)
        rows = self._require_conn().execute(
            "SELECT v.*, n.case_id FROM node_versions v JOIN nodes n ON n.id = v.node_id WHERE v.node_id = ? ORDER BY v.seq",
            (node_id,),
        ).fetchall()
        return [_row_to_version(r) for r in rows]

    def set_current(
        self,
        node_id: str,
        version_id: str,
        *,
        status: str,
        applicability: str = "current",
        by: str = "controller",
        actor_task: str | None = None,
    ) -> Event:
        """Point ``node_current`` at ``version_id`` with ``status``/``applicability`` and record the change.

        The version must belong to the node. ``status`` is checked against :data:`STATUS_ENUMS` for kinds
        that have a fixed vocabulary and must be non-empty otherwise. Emits a ``node.current_changed``
        event (actor ``by``) whose payload carries the previous and new version ids; returns that event.
        """
        version = self.get_version(version_id)
        if version["node_id"] != node_id:
            raise ValidationError(
                f"version {version_id!r} does not belong to node {node_id!r}",
                errors=["/version_id: version belongs to a different node"],
                details={"node_id": node_id, "version_id": version_id, "owner": version["node_id"]},
            )
        kind = version["kind"]
        self._check_status(kind, status)
        if applicability not in APPLICABILITIES:
            raise ValidationError(
                f"unknown applicability {applicability!r}",
                errors=[f"/applicability: {applicability!r} is not one of {sorted(APPLICABILITIES)}"],
            )
        with self.transaction() as conn:
            previous = conn.execute("SELECT version_id, status, applicability FROM node_current WHERE node_id = ?", (node_id,)).fetchone()
            stamp = now()
            if previous is None:
                conn.execute(
                    "INSERT INTO node_current(node_id, version_id, kind, status, applicability, updated_at) VALUES (?,?,?,?,?,?)",
                    (node_id, version_id, kind, status, applicability, stamp),
                )
            else:
                conn.execute(
                    "UPDATE node_current SET version_id = ?, kind = ?, status = ?, applicability = ?, updated_at = ? WHERE node_id = ?",
                    (version_id, kind, status, applicability, stamp, node_id),
                )
            sv = self.state_version()
            payload = {
                "node_id": node_id,
                "version_id": version_id,
                "kind": kind,
                "status": status,
                "applicability": applicability,
                "previous_version_id": previous["version_id"] if previous else None,
                "previous_status": previous["status"] if previous else None,
                "previous_applicability": previous["applicability"] if previous else None,
            }
            return self.append_event(
                "node.current_changed",
                payload,
                actor_role=by,
                actor_task=actor_task,
                expected_state_version=sv,
                idempotency_key=f"node.current_changed:{node_id}:{version_id}:{sv + 1}",
                payload_refs=[node_id, version_id],
            )

    def current(self, node_id: str) -> dict[str, Any] | None:
        """Return ``{node_id, version_id, status, applicability, kind, updated_at}`` or ``None`` if unset."""
        row = self._require_conn().execute("SELECT * FROM node_current WHERE node_id = ?", (node_id,)).fetchone()
        return dict(row) if row is not None else None

    def find_current(self, kind: str, /, **filters: Any) -> list[dict[str, Any]]:
        """Return current versions of ``kind`` whose payload matches every filter via ``json_extract``.

        Each filter key is a payload key; ``a__b`` addresses the nested path ``$.a.b``. ``None`` matches a
        missing or null value. Each result merges the ``node_current`` row with its version (``payload``,
        ``content_hash``, author fields), ordered by node creation.
        """
        self._check_kind(kind)
        clauses = ["c.kind = ?"]
        params: list[Any] = [kind]
        for key, value in filters.items():
            path = _json_path(key)
            if value is None:
                clauses.append(f"json_extract(v.payload, '{path}') IS NULL")
            else:
                clauses.append(f"json_extract(v.payload, '{path}') = ?")
                params.append(_bind_value(value))
        sql = (
            "SELECT c.node_id, c.version_id, c.status, c.applicability, c.kind, c.updated_at, v.seq, v.payload, v.content_hash,"
            " v.author_role, v.author_task, v.author_session, v.created_at, n.case_id"
            " FROM node_current c JOIN node_versions v ON v.id = c.version_id JOIN nodes n ON n.id = c.node_id"
            " WHERE " + " AND ".join(clauses) + " ORDER BY n.rowid"
        )
        rows = self._require_conn().execute(sql, params).fetchall()
        out = []
        for row in rows:
            record = dict(row)
            record["payload"] = json.loads(record["payload"])
            out.append(record)
        return out

    # ---------------------------------------------------------------------------------------------
    # Edges
    # ---------------------------------------------------------------------------------------------

    def add_edge(
        self,
        from_version: str,
        to_version: str,
        relation: str,
        *,
        impact_policy: str | None = None,
        reason: str,
        proposed_by: str,
        status: str = "proposed",
    ) -> str:
        """Add a typed edge between two existing versions and return its id.

        ``relation``, ``status`` and ``impact_policy`` (when given) are checked against their enumerations;
        the ``depends_on``/``impact_policy`` pairing rule belongs to ``lineage.py``.
        """
        if relation not in RELATIONS:
            raise ValidationError(f"unknown relation {relation!r}", errors=[f"/relation: {relation!r} is not one of {sorted(RELATIONS)}"])
        if status not in EDGE_STATUSES:
            raise ValidationError(f"unknown edge status {status!r}", errors=[f"/status: {status!r} is not one of {sorted(EDGE_STATUSES)}"])
        if impact_policy is not None and impact_policy not in IMPACT_POLICIES:
            raise ValidationError(
                f"unknown impact_policy {impact_policy!r}",
                errors=[f"/impact_policy: {impact_policy!r} is not one of {sorted(IMPACT_POLICIES)}"],
            )
        if not isinstance(reason, str) or not reason:
            raise ValidationError("edge reason must be a non-empty string", errors=["/reason: empty"])
        if not isinstance(proposed_by, str) or not proposed_by:
            raise ValidationError("proposed_by must be a non-empty string", errors=["/proposed_by: empty"])
        self.get_version(from_version)
        self.get_version(to_version)
        edge_id = new_id("edge")
        with self.transaction() as conn:
            try:
                conn.execute(
                    "INSERT INTO edges(id, case_id, from_version, to_version, relation, impact_policy, reason, proposed_by, status,"
                    " created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (edge_id, self.case_id, from_version, to_version, relation, impact_policy, reason, proposed_by, status, now()),
                )
            except sqlite3.IntegrityError as exc:
                raise _translate_integrity(exc, "edges") from exc
        return edge_id

    def get_edge(self, edge_id: str) -> dict[str, Any]:
        """Return one edge row as a dict or raise :class:`NotFoundError`."""
        row = self._require_conn().execute("SELECT * FROM edges WHERE id = ?", (edge_id,)).fetchone()
        if row is None:
            raise NotFoundError(f"no edge {edge_id!r}", details={"edge_id": edge_id})
        return dict(row)

    def set_edge_status(self, edge_id: str, status: str, by: str) -> dict[str, Any]:
        """Set an edge's status (``proposed``/``accepted``/``rejected``) recording who changed it."""
        if status not in EDGE_STATUSES:
            raise ValidationError(f"unknown edge status {status!r}", errors=[f"/status: {status!r} is not one of {sorted(EDGE_STATUSES)}"])
        if not isinstance(by, str) or not by:
            raise ValidationError("by must be a non-empty string", errors=["/by: empty"])
        self.get_edge(edge_id)
        with self.transaction() as conn:
            conn.execute(
                "UPDATE edges SET status = ?, status_changed_by = ?, status_changed_at = ? WHERE id = ?",
                (status, by, now(), edge_id),
            )
        return self.get_edge(edge_id)

    def edges_from(self, version_id: str, relation: str | None = None, status: str | None = "accepted") -> list[dict[str, Any]]:
        """Edges whose ``from_version`` is ``version_id``; ``status=None`` means any status."""
        return self._edges("from_version", version_id, relation, status)

    def edges_to(self, version_id: str, relation: str | None = None, status: str | None = "accepted") -> list[dict[str, Any]]:
        """Edges whose ``to_version`` is ``version_id``; ``status=None`` means any status."""
        return self._edges("to_version", version_id, relation, status)

    # ---------------------------------------------------------------------------------------------
    # Blobs
    # ---------------------------------------------------------------------------------------------

    def put_blob(self, data: bytes) -> str:
        """Store ``data`` under ``blobs/<sha256>`` (atomic write, idempotent) and return the hex digest."""
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise ValidationError("blob data must be bytes", errors=["/: not bytes"])
        raw = bytes(data)
        digest = sha256_bytes(raw)
        target = self.blobs_dir / digest
        if target.exists():
            return digest
        self.blobs_dir.mkdir(parents=True, exist_ok=True)
        tmp = self.blobs_dir / f".{digest}.{os.getpid()}.tmp"
        with open(tmp, "wb") as fh:
            fh.write(raw)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, target)
        return digest

    def blob_path(self, sha256: str) -> Path:
        """Return the path of blob ``sha256`` (the file may not exist; see :meth:`has_blob`)."""
        if not isinstance(sha256, str) or not _SHA256_RE.match(sha256):
            raise ValidationError(f"invalid blob hash {sha256!r}", errors=["/sha256: not a 64-char lowercase hex digest"])
        return self.blobs_dir / sha256

    def has_blob(self, sha256: str) -> bool:
        """True when the blob file exists."""
        return self.blob_path(sha256).is_file()

    def get_blob(self, sha256: str) -> bytes:
        """Return the blob bytes, verifying the content hash, or raise :class:`NotFoundError`."""
        path = self.blob_path(sha256)
        if not path.is_file():
            raise NotFoundError(f"no blob {sha256}", details={"sha256": sha256})
        data = path.read_bytes()
        if sha256_bytes(data) != sha256:
            raise ConflictError(f"blob {sha256} content does not match its hash", details={"reason": "blob_hash_mismatch", "sha256": sha256})
        return data

    def list_blobs(self) -> list[str]:
        """Sorted hashes of every blob on disk."""
        if not self.blobs_dir.is_dir():
            return []
        return sorted(p.name for p in self.blobs_dir.iterdir() if p.is_file() and _SHA256_RE.match(p.name))

    # ---------------------------------------------------------------------------------------------
    # Operational tables (generic row operations)
    # ---------------------------------------------------------------------------------------------

    def insert(self, table: str, row: dict[str, Any]) -> str:
        """Insert ``row`` into one of :data:`OPERATIONAL_TABLES` and return its key (``id``).

        Keys without a dedicated column are kept in the table's JSON catch-all and come back transparently
        from :meth:`get`/:meth:`query`. A missing ``id`` is minted (``budgets`` falls back to ``run_id``);
        a missing ``case_id`` defaults to the store's case; a missing ``created_at`` is stamped. Duplicate
        keys raise :class:`ConflictError`.
        """
        self._check_table(table)
        if not isinstance(row, dict):
            raise ValidationError("row must be a dict", errors=["/: not an object"])
        data = dict(row)
        if _EXTRA in data:
            raise ValidationError(f"{_EXTRA!r} is reserved", errors=[f"/{_EXTRA}: reserved column"])
        key = data.get("id")
        if key is None:
            if table in _TABLE_ID_PREFIX:
                key = new_id(_TABLE_ID_PREFIX[table])
            elif isinstance(data.get("run_id"), str) and data["run_id"]:
                key = data["run_id"]
            else:
                raise ValidationError(f"{table} row needs an 'id' (or 'run_id')", errors=["/id: 'id' is a required property"])
            data["id"] = key
        if not isinstance(key, str) or not key:
            raise ValidationError("row id must be a non-empty string", errors=["/id: not a non-empty string"])
        columns = self._columns(table)
        if "case_id" in columns and data.get("case_id") is None:
            data["case_id"] = self.case_id
        if "created_at" in columns and data.get("created_at") is None:
            data["created_at"] = now()
        promoted, extra = _split_row(table, columns, data)
        names = list(promoted) + [_EXTRA]
        values = [promoted[n] for n in promoted] + [_dumps(extra)]
        with self.transaction() as conn:
            try:
                conn.execute(
                    f"INSERT INTO {table}({', '.join(names)}) VALUES ({', '.join('?' for _ in names)})",
                    values,
                )
            except sqlite3.IntegrityError as exc:
                raise _translate_integrity(exc, table, key) from exc
        return key

    def update(self, table: str, key: str, changes: dict[str, Any], *, expected: dict[str, Any] | None = None) -> dict[str, Any]:
        """Apply ``changes`` to row ``key`` of an operational table and return the updated row.

        With ``expected``, every listed field must still equal the stored value (compared on the flattened
        row) or :class:`ConflictError` (``reason == "expected_mismatch"``) is raised and nothing changes.
        Changing ``id`` is refused. Missing rows raise :class:`NotFoundError`.
        """
        self._check_table(table)
        if not isinstance(changes, dict):
            raise ValidationError("changes must be a dict", errors=["/: not an object"])
        if "id" in changes and changes["id"] != key:
            raise ValidationError("a row's id cannot be changed", errors=["/id: immutable"])
        if _EXTRA in changes:
            raise ValidationError(f"{_EXTRA!r} is reserved", errors=[f"/{_EXTRA}: reserved column"])
        columns = self._columns(table)
        with self.transaction() as conn:
            raw = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (key,)).fetchone()
            if raw is None:
                raise NotFoundError(f"no {table} row {key!r}", details={"table": table, "key": key})
            current = _flatten_row(table, raw)
            if expected:
                mismatches = {k: current.get(k) for k, v in expected.items() if not _json_eq(current.get(k), v)}
                if mismatches:
                    raise ConflictError(
                        f"{table} row {key!r} no longer matches expected values",
                        details={"reason": "expected_mismatch", "table": table, "key": key, "expected": dict(expected), "actual": mismatches},
                    )
            extra = json.loads(raw[_EXTRA]) if raw[_EXTRA] else {}
            sets: list[str] = []
            params: list[Any] = []
            json_cols = JSON_COLUMNS[table]
            for name, value in changes.items():
                if name == "id":
                    continue
                if name in columns:
                    sets.append(f"{name} = ?")
                    params.append(_dumps(value) if name in json_cols else _bind_value(value))
                else:
                    _check_ident(name)
                    extra[name] = value
            sets.append(f"{_EXTRA} = ?")
            params.append(_dumps(extra))
            params.append(key)
            try:
                conn.execute(f"UPDATE {table} SET {', '.join(sets)} WHERE id = ?", params)
            except sqlite3.IntegrityError as exc:
                raise _translate_integrity(exc, table, key) from exc
            updated = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (key,)).fetchone()
        return _flatten_row(table, updated)

    def get(self, table: str, key: str) -> dict[str, Any] | None:
        """Return the flattened row ``key`` of an operational table, or ``None`` when absent."""
        self._check_table(table)
        row = self._require_conn().execute(f"SELECT * FROM {table} WHERE id = ?", (key,)).fetchone()
        return _flatten_row(table, row) if row is not None else None

    def query(self, table: str, **equals: Any) -> list[dict[str, Any]]:
        """Return rows of an operational table matching every ``column == value`` filter, in rowid order.

        Filters may name dedicated columns or keys kept in the JSON catch-all; ``None`` matches NULL/missing.
        """
        self._check_table(table)
        columns = self._columns(table)
        clauses: list[str] = []
        params: list[Any] = []
        for name, value in equals.items():
            _check_ident(name)
            if name in columns:
                expr = name
                bound = _dumps(value) if name in JSON_COLUMNS[table] and value is not None else _bind_value(value)
            else:
                expr = f"json_extract({_EXTRA}, '$.{name}')"
                bound = _bind_value(value)
            if value is None:
                clauses.append(f"{expr} IS NULL")
            else:
                clauses.append(f"{expr} = ?")
                params.append(bound)
        sql = f"SELECT * FROM {table}"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY rowid"
        rows = self._require_conn().execute(sql, params).fetchall()
        return [_flatten_row(table, r) for r in rows]

    # ---------------------------------------------------------------------------------------------
    # Receipts
    # ---------------------------------------------------------------------------------------------

    def put_receipt(self, payload: dict[str, Any]) -> str:
        """Validate ``payload`` against the ``receipt`` schema and store it; return its id.

        Storing the identical receipt again is a no-op returning the same id; a different payload under an
        existing id raises :class:`ConflictError`.
        """
        if not isinstance(payload, dict):
            raise ValidationError("receipt must be a JSON object", errors=["/: not an object"])
        ensure_valid(payload, "receipt")
        receipt_id = payload["id"]
        with self.transaction():
            existing = self.get("receipts", receipt_id)
            if existing is not None:
                if sha256_json(existing.get("payload")) == sha256_json(payload):
                    return receipt_id
                raise ConflictError(
                    f"receipt {receipt_id!r} already exists with a different payload",
                    details={"reason": "receipt_payload_mismatch", "receipt_id": receipt_id},
                )
            self.insert(
                "receipts",
                {
                    "id": receipt_id,
                    "task_id": payload["task_id"],
                    "exit_status": payload["exit_status"],
                    "observation_source": payload["observation_source"],
                    "started_at": payload["started_at"],
                    "ended_at": payload["ended_at"],
                    "payload": payload,
                },
            )
        return receipt_id

    def get_receipt(self, receipt_id: str) -> dict[str, Any] | None:
        """Return the stored receipt payload for ``receipt_id`` or ``None``."""
        row = self.get("receipts", receipt_id)
        if row is None:
            return None
        return row.get("payload") if isinstance(row.get("payload"), dict) else row

    def receipts_for_task(self, task_id: str) -> list[dict[str, Any]]:
        """Return the receipt payloads recorded for ``task_id`` in insertion order."""
        out = []
        for row in self.query("receipts", task_id=task_id):
            out.append(row["payload"] if isinstance(row.get("payload"), dict) else row)
        return out

    # ---------------------------------------------------------------------------------------------
    # Operations: backup, export, import, integrity
    # ---------------------------------------------------------------------------------------------

    def backup(self, dest: Path) -> Path:
        """Write a consistent copy of the database to ``dest`` with ``sqlite3.Connection.backup``.

        ``dest`` is the target database file (its parent is created). Refuses to overwrite the live
        database, and refuses (:class:`ConflictError`, ``reason == "transaction_open"``) while this store
        has a write transaction open: a backup snapshots committed state only, and SQLite's backup step
        would otherwise spin on the uncommitted pages. Returns ``dest``.
        """
        conn = self._require_conn()
        if self._depth > 0 or conn.in_transaction:
            raise ConflictError(
                "backup refused while a write transaction is open; commit or roll back first",
                details={"reason": "transaction_open", "case_dir": str(self.case_dir)},
            )
        dest = Path(dest)
        if dest.exists() and dest.resolve() == self.db_path.resolve():
            raise PolicyError("backup destination is the live database", details={"reason": "backup_overwrites_live_db"})
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            dest.unlink()
        target = sqlite3.connect(str(dest))
        try:
            self._require_conn().backup(target)
        finally:
            target.close()
        return dest

    def export(self, dest_dir: Path) -> dict[str, Any]:
        """Export every table as ``<table>.jsonl`` plus ``blobs/`` into ``dest_dir`` and return the manifest.

        Rows are written in rowid order with JSON columns decoded. The manifest (also written as
        ``manifest.json``) lists row counts and content hashes per table and every blob hash.
        """
        dest_dir = Path(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        conn = self._require_conn()
        tables: dict[str, Any] = {}
        for table in _ALL_TABLES:
            json_cols = set(_json_columns_of(table))
            rows = conn.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
            lines = []
            for row in rows:
                record = dict(row)
                for col in json_cols:
                    if record.get(col) is not None:
                        record[col] = json.loads(record[col])
                lines.append(_dumps(record))
            text = "".join(line + "\n" for line in lines)
            (dest_dir / f"{table}.jsonl").write_text(text, encoding="utf-8")
            tables[table] = {"rows": len(lines), "sha256": sha256_bytes(text.encode("utf-8"))}
        blob_dir = dest_dir / "blobs"
        blob_dir.mkdir(exist_ok=True)
        blobs = []
        for digest in self.list_blobs():
            shutil.copyfile(self.blobs_dir / digest, blob_dir / digest)
            blobs.append(digest)
        manifest = {
            "format": _EXPORT_FORMAT,
            "format_version": _EXPORT_FORMAT_VERSION,
            "schema_version": self.schema_version(),
            "case_id": self.case_id,
            "state_version": self.state_version(),
            "exported_at": now(),
            "tables": tables,
            "blobs": {"count": len(blobs), "sha256": blobs},
        }
        (dest_dir / "manifest.json").write_text(_dumps(manifest) + "\n", encoding="utf-8")
        return manifest

    @classmethod
    def import_(cls, src_dir: Path, case_dir: Path) -> "CaseStore":
        """Rebuild a store at ``case_dir`` from an :meth:`export` directory, preserving every id and hash.

        Requires a manifest with the current ``schema_version``; blob files must match their names. Rows
        are inserted in dependency order inside one transaction.
        """
        src_dir = Path(src_dir)
        case_dir = Path(case_dir)
        manifest_path = src_dir / "manifest.json"
        if not manifest_path.is_file():
            raise NotFoundError(f"no manifest.json in {src_dir}", details={"src_dir": str(src_dir)})
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValidationError(f"manifest unreadable: {exc}", errors=["/manifest.json: unreadable"]) from exc
        if not isinstance(manifest, dict) or manifest.get("format") != _EXPORT_FORMAT:
            raise ValidationError("not an aipt case export", errors=["/format: unexpected export format"])
        found = manifest.get("schema_version")
        if found != SCHEMA_VERSION:
            raise ValidationError(
                f"export schema version {found!r} does not match supported version {SCHEMA_VERSION}",
                errors=["/schema_version: unsupported"],
                details={"reason": "schema_version_mismatch", "found": found, "supported": SCHEMA_VERSION},
            )
        cls._refuse_synced(case_dir)
        if (case_dir / "state.sqlite3").exists():
            raise ConflictError(f"a case store already exists at {case_dir}", details={"case_dir": str(case_dir)})
        _ensure_dirs(case_dir, cls.SUBDIRS)
        store = cls(case_dir)
        try:
            store._conn.executescript(load_ddl())
            with store.transaction() as conn:
                for table in _ALL_TABLES:
                    path = src_dir / f"{table}.jsonl"
                    if not path.is_file():
                        continue
                    json_cols = set(_json_columns_of(table))
                    columns = store._columns(table)
                    with open(path, "r", encoding="utf-8") as fh:
                        for line_no, line in enumerate(fh, 1):
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                record = json.loads(line)
                            except json.JSONDecodeError as exc:
                                raise ValidationError(
                                    f"{table}.jsonl line {line_no} is not JSON", errors=[f"/{table}.jsonl/{line_no}: {exc}"]
                                ) from exc
                            names = [n for n in record if n in columns]
                            unknown = [n for n in record if n not in columns]
                            if unknown:
                                raise ValidationError(
                                    f"{table}.jsonl line {line_no} has unknown columns {unknown}",
                                    errors=[f"/{table}.jsonl/{line_no}: unknown columns {unknown}"],
                                )
                            values = [
                                (_dumps(record[n]) if n in json_cols and record[n] is not None else record[n]) for n in names
                            ]
                            verb = "INSERT OR REPLACE" if table == "meta" else "INSERT"
                            conn.execute(
                                f"{verb} INTO {table}({', '.join(names)}) VALUES ({', '.join('?' for _ in names)})", values
                            )
            blob_src = src_dir / "blobs"
            if blob_src.is_dir():
                for entry in sorted(blob_src.iterdir()):
                    if not entry.is_file() or not _SHA256_RE.match(entry.name):
                        continue
                    data = entry.read_bytes()
                    if sha256_bytes(data) != entry.name:
                        raise ConflictError(
                            f"blob {entry.name} content does not match its hash", details={"reason": "blob_hash_mismatch", "sha256": entry.name}
                        )
                    store.put_blob(data)
            store._case_id = store._load_case_id()
        except Exception:
            store.close()
            raise
        return store

    def integrity_check(self) -> list[str]:
        """Return every integrity problem found; an empty list means the store is consistent.

        Runs ``PRAGMA integrity_check`` and ``PRAGMA foreign_key_check``, then referential checks: the case
        row exists and its ``state_version`` equals the event count; event ``seq`` is contiguous from 1;
        version ``seq`` is contiguous per node; ``node_current`` points at a version of its own node with
        matching ``kind``; every version's ``content_hash`` matches its payload; every blob file matches
        its name.
        """
        conn = self._require_conn()
        problems: list[str] = []
        for row in conn.execute("PRAGMA integrity_check").fetchall():
            if row[0] != "ok":
                problems.append(f"integrity_check: {row[0]}")
        for row in conn.execute("PRAGMA foreign_key_check").fetchall():
            problems.append(f"foreign_key_check: table {row[0]} rowid {row[1]} references {row[2]}")
        case = conn.execute("SELECT * FROM cases").fetchall()
        if len(case) != 1:
            problems.append(f"cases: expected exactly one row, found {len(case)}")
        else:
            events = conn.execute("SELECT seq FROM events WHERE case_id = ? ORDER BY seq", (case[0]["id"],)).fetchall()
            if int(case[0]["state_version"]) != len(events):
                problems.append(f"cases: state_version {case[0]['state_version']} != event count {len(events)}")
            for index, row in enumerate(events, 1):
                if int(row["seq"]) != index:
                    problems.append(f"events: seq gap at position {index} (found {row['seq']})")
                    break
        for node in conn.execute("SELECT id FROM nodes").fetchall():
            seqs = [int(r["seq"]) for r in conn.execute("SELECT seq FROM node_versions WHERE node_id = ? ORDER BY seq", (node["id"],)).fetchall()]
            if seqs != list(range(1, len(seqs) + 1)):
                problems.append(f"node_versions: non-contiguous seq for node {node['id']}: {seqs}")
        for cur in conn.execute("SELECT * FROM node_current").fetchall():
            ver = conn.execute("SELECT node_id, kind FROM node_versions WHERE id = ?", (cur["version_id"],)).fetchone()
            if ver is None:
                problems.append(f"node_current: {cur['node_id']} points at missing version {cur['version_id']}")
            else:
                if ver["node_id"] != cur["node_id"]:
                    problems.append(f"node_current: {cur['node_id']} points at version {cur['version_id']} of node {ver['node_id']}")
                if ver["kind"] != cur["kind"]:
                    problems.append(f"node_current: {cur['node_id']} kind {cur['kind']} != version kind {ver['kind']}")
        for ver in conn.execute("SELECT id, payload, content_hash FROM node_versions").fetchall():
            if sha256_bytes(ver["payload"].encode("utf-8")) != ver["content_hash"]:
                problems.append(f"node_versions: content_hash mismatch for {ver['id']}")
        for evt in conn.execute("SELECT id, payload, payload_sha256 FROM events").fetchall():
            if sha256_json(json.loads(evt["payload"])) != evt["payload_sha256"]:
                problems.append(f"events: payload_sha256 mismatch for {evt['id']}")
        for digest in self.list_blobs():
            if sha256_bytes((self.blobs_dir / digest).read_bytes()) != digest:
                problems.append(f"blobs: content of {digest} does not match its name")
        return problems

    # ---------------------------------------------------------------------------------------------
    # Internals
    # ---------------------------------------------------------------------------------------------

    @classmethod
    def _refuse_synced(cls, case_dir: Path) -> None:
        if is_synced_or_network_path(case_dir):
            raise PolicyError(
                f"refusing to create a case store under a synced or network filesystem: {case_dir}",
                details={"reason": "synced_or_network_filesystem", "case_dir": str(case_dir)},
            )

    def _require_conn(self) -> sqlite3.Connection:
        conn = getattr(self, "_conn", None)
        if conn is None:
            raise ConflictError("case store is closed", details={"reason": "store_closed", "case_dir": str(self.case_dir)})
        return conn

    def _apply_pragmas(self) -> None:
        conn = self._conn
        mode = conn.execute("PRAGMA journal_mode=WAL").fetchone()[0]
        if str(mode).lower() != "wal":
            conn.close()
            raise PolicyError(
                f"filesystem does not support WAL (journal_mode={mode}); refusing to use it for authoritative state",
                details={"reason": "wal_unsupported", "journal_mode": mode, "case_dir": str(self.case_dir)},
            )
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=5000")

    def _read_schema_version(self) -> int:
        conn = self._require_conn()
        has_meta = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='meta'").fetchone()
        if has_meta is None:
            raise NotFoundError("database has no meta table; not a case store", details={"case_dir": str(self.case_dir)})
        row = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        if row is None:
            raise NotFoundError("meta.schema_version missing", details={"case_dir": str(self.case_dir)})
        try:
            return int(row["value"])
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"meta.schema_version is not an integer: {row['value']!r}", errors=["/meta/schema_version: not an integer"]) from exc

    def _load_case_id(self) -> str:
        rows = self._require_conn().execute("SELECT id FROM cases ORDER BY rowid").fetchall()
        if len(rows) != 1:
            raise NotFoundError(f"store must hold exactly one case, found {len(rows)}", details={"case_dir": str(self.case_dir)})
        return rows[0]["id"]

    def _migrate(self, found: int) -> None:
        chain: list[tuple[int, int, str | Sequence[str]]] = []
        version = found
        while version < SCHEMA_VERSION:
            step = next((m for m in MIGRATIONS if m[0] == version), None)
            if step is None:
                raise ConflictError(
                    f"no migration from schema version {version}",
                    details={"reason": "no_migration_path", "found": found, "stuck_at": version, "supported": SCHEMA_VERSION},
                )
            chain.append(step)
            version = step[1]
        stamp = now().replace(":", "").replace("-", "").replace(".", "")
        self.backup(self.case_dir / "backups" / f"pre-migration-v{found}-{stamp}.sqlite3")
        with self.transaction() as conn:
            for _frm, to, statements in chain:
                for statement in ([statements] if isinstance(statements, str) else statements):
                    conn.execute(statement)
                conn.execute("INSERT OR REPLACE INTO meta(key, value) VALUES ('schema_version', ?)", (str(to),))

    def _columns(self, table: str) -> tuple[str, ...]:
        rows = self._require_conn().execute(f"PRAGMA table_info({table})").fetchall()
        return tuple(r["name"] for r in rows)

    def _check_kind(self, kind: str) -> None:
        if kind not in NODE_KINDS:
            raise ValidationError(f"unknown node kind {kind!r}", errors=[f"/kind: {kind!r} is not one of {sorted(NODE_KINDS)}"])

    def _check_status(self, kind: str, status: str) -> None:
        if not isinstance(status, str) or not status:
            raise ValidationError("status must be a non-empty string", errors=["/status: empty"])
        allowed = STATUS_ENUMS.get(kind)
        if allowed is not None and status not in allowed:
            raise ValidationError(
                f"status {status!r} is not valid for kind {kind!r}",
                errors=[f"/status: {status!r} is not one of {sorted(allowed)}"],
                details={"kind": kind, "status": status},
            )

    def _check_table(self, table: str) -> None:
        if table not in OPERATIONAL_TABLES:
            raise ValueError(f"{table!r} is not an operational table; allowed: {list(OPERATIONAL_TABLES)}")

    def _edges(self, column: str, version_id: str, relation: str | None, status: str | None) -> list[dict[str, Any]]:
        if relation is not None and relation not in RELATIONS:
            raise ValidationError(f"unknown relation {relation!r}", errors=[f"/relation: {relation!r} is not one of {sorted(RELATIONS)}"])
        if status is not None and status not in EDGE_STATUSES:
            raise ValidationError(f"unknown edge status {status!r}", errors=[f"/status: {status!r} is not one of {sorted(EDGE_STATUSES)}"])
        clauses = [f"{column} = ?"]
        params: list[Any] = [version_id]
        if relation is not None:
            clauses.append("relation = ?")
            params.append(relation)
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        rows = self._require_conn().execute(f"SELECT * FROM edges WHERE {' AND '.join(clauses)} ORDER BY rowid", params).fetchall()
        return [dict(r) for r in rows]


# --------------------------------------------------------------------------------------------------
# Module-private helpers
# --------------------------------------------------------------------------------------------------


def _dumps(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _ensure_dirs(case_dir: Path, subdirs: Sequence[str]) -> None:
    case_dir.mkdir(parents=True, exist_ok=True)
    for name in subdirs:
        (case_dir / name).mkdir(exist_ok=True)


def _resolve_lenient(path: Path) -> Path:
    try:
        return path.resolve()
    except OSError:
        return Path(os.path.abspath(path))


def _on_network_mount(resolved: Path) -> bool:
    mounts = Path("/proc/mounts")
    if not mounts.is_file():
        return False
    try:
        text = mounts.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    best: tuple[int, str] | None = None
    target = str(resolved)
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        mount_point = parts[1].replace("\\040", " ")
        fs_type = parts[2].lower()
        if target == mount_point or target.startswith(mount_point.rstrip("/") + "/") or mount_point == "/":
            if best is None or len(mount_point) > best[0]:
                best = (len(mount_point), fs_type)
    return best is not None and best[1] in _NETWORK_FS_TYPES


def _check_ident(name: str) -> None:
    if not isinstance(name, str) or not _IDENT_RE.match(name):
        raise ValidationError(f"invalid column or key name {name!r}", errors=[f"/{name}: not an identifier"])


def _json_path(key: str) -> str:
    parts = key.split("__")
    for part in parts:
        _check_ident(part)
    return "$." + ".".join(parts)


def _bind_value(value: Any) -> Any:
    if isinstance(value, bool):
        return 1 if value else 0
    if value is None or isinstance(value, (int, float, str, bytes)):
        return value
    return _dumps(value)


def _json_eq(a: Any, b: Any) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return (a in (0, 1, True, False)) and (b in (0, 1, True, False)) and bool(a) == bool(b)
    return a == b


def _split_row(table: str, columns: Sequence[str], data: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    json_cols = JSON_COLUMNS[table]
    promoted: dict[str, Any] = {}
    extra: dict[str, Any] = {}
    for name, value in data.items():
        if name in columns:
            promoted[name] = _dumps(value) if name in json_cols and value is not None else _bind_value(value)
        else:
            _check_ident(name)
            extra[name] = value
    return promoted, extra


def _flatten_row(table: str, row: sqlite3.Row) -> dict[str, Any]:
    record = dict(row)
    extra_text = record.pop(_EXTRA, None)
    for col in JSON_COLUMNS[table]:
        if record.get(col) is not None:
            record[col] = json.loads(record[col])
    extra = json.loads(extra_text) if extra_text else {}
    for name, value in extra.items():
        record.setdefault(name, value)
    return record


def _json_columns_of(table: str) -> tuple[str, ...]:
    if table in JSON_COLUMNS:
        return JSON_COLUMNS[table] + (_EXTRA,)
    return _CORE_JSON_COLUMNS.get(table, ())


def _row_to_event(row: sqlite3.Row) -> Event:
    return Event(
        id=row["id"],
        seq=int(row["seq"]),
        case_id=row["case_id"],
        type=row["type"],
        actor_role=row["actor_role"],
        actor_task=row["actor_task"],
        expected_state_version=int(row["expected_state_version"]),
        payload_refs=tuple(json.loads(row["payload_refs"])),
        payload=json.loads(row["payload"]),
        payload_sha256=row["payload_sha256"],
        created_at=row["created_at"],
        idempotency_key=row["idempotency_key"],
    )


def _row_to_version(row: sqlite3.Row) -> dict[str, Any]:
    record = dict(row)
    record["payload"] = json.loads(record["payload"])
    record["version_id"] = record["id"]
    return record


def _translate_integrity(exc: sqlite3.IntegrityError, table: str, key: str | None = None) -> Exception:
    message = str(exc)
    details: dict[str, Any] = {"table": table, "sqlite": message}
    if key is not None:
        details["key"] = key
    if "UNIQUE" in message or "PRIMARY KEY" in message:
        details["reason"] = "duplicate_key"
        return ConflictError(f"{table}: duplicate key ({message})", details=details)
    if "FOREIGN KEY" in message:
        details["reason"] = "missing_reference"
        return NotFoundError(f"{table}: a referenced row does not exist ({message})", details=details)
    if "immutable" in message:
        details["reason"] = "immutable_table"
        return PolicyError(f"{table}: {message}", details=details)
    return ValidationError(f"{table}: {message}", errors=[f"/: {message}"], details=details)
