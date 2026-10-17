"""Unit tests for ai_product_team.storage (contract section 5, section 13 "test_storage", section 14 addendum).

Covers: create/open and pragmas; synced-path refusal; event append with stale-version conflict; idempotent
replay; version immutability via triggers; set_current event; edges; blobs; backup restores; export/import
round trip equality; integrity_check; migration path with backup; the generic operational-table operations;
and the receipt helpers. Every test works inside tempfile.TemporaryDirectory(); nothing touches the repo.
"""

from __future__ import annotations

import copy
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from ai_product_team import storage as S
from ai_product_team import validation as V
from ai_product_team.errors import ConflictError, NotFoundError, PolicyError, ValidationError
from ai_product_team.ids import sha256_bytes, sha256_json

TS = "2026-10-16T12:00:00Z"

CLAIM = {
    "statement": "Drafts only.",
    "claim_type": "fact",
    "status": "supported",
    "supporting_refs": [],
    "contrary_refs": [],
    "confidence_label": "high",
    "assessed_by": "claim-checker",
}
ARTIFACT = {
    "kind": "context-brief.md",
    "path": "proposals/context-brief.md",
    "content_hash": "cd" * 32,
    "producer_role": "context-analyst",
    "producer_task": "task_demo",
    "write_scope": "proposal-only",
    "implements_refs": [],
    "status": "proposed",
    "access_classification": "synthetic",
}
REQUIREMENT = {
    "statement": "No automatic sending.",
    "owner": "human-owner",
    "acceptance_criteria": ["Send path absent."],
    "protected": True,
    "originating_refs": [],
    "status": "approved",
}
DECISION = {
    "proposal_version_id": "ver_9",
    "outcome": "accepted",
    "selected_option": "A",
    "criteria": ["Fits"],
    "rationale": "Reversible.",
    "dissent": [],
    "authority_basis": {"kind": "delegation", "approval_version_id": "ver_7"},
    "revisit_conditions": [],
    "status": "accepted",
}
RECEIPT = {
    "id": "rcpt_1",
    "task_id": "task_demo",
    "command": ["python3", "-c", "pass"],
    "cwd": "/work",
    "snapshot": {"kind": "git", "commit": "abc123", "dirty_diff_sha256": None, "paths": ["src"]},
    "started_at": TS,
    "ended_at": TS,
    "exit_status": 0,
    "timed_out": False,
    "cancelled": False,
    "stdout_path": "receipts/rcpt_1.out",
    "stderr_path": "receipts/rcpt_1.err",
    "observation_source": "controller",
    "test_ids": [],
    "redactions_applied": 0,
    "proves": "command_exit_status_only",
}


class StoreCase(unittest.TestCase):
    """Base: one temporary directory per test; every opened store is closed on teardown."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self._stores: list[S.CaseStore] = []

    def tearDown(self) -> None:
        for store in self._stores:
            store.close()
        self._tmp.cleanup()

    def track(self, store: S.CaseStore) -> S.CaseStore:
        self._stores.append(store)
        return store

    def make_store(self, name: str = "case", payload: dict | None = None) -> S.CaseStore:
        payload = payload if payload is not None else {"objective": "Test case", "owner": "human-owner", "source_scope": ["docs/"]}
        return self.track(S.CaseStore.create(self.tmp / name, payload))

    def add_claim(self, store: S.CaseStore, **overrides) -> tuple[str, str]:
        node = store.new_node("claim", store.case_id)
        version = store.put_version(node, {**CLAIM, **overrides}, author_role="claim-checker")
        return node, version


# --------------------------------------------------------------------------------------------------
# create / open / pragmas / lifecycle
# --------------------------------------------------------------------------------------------------


class CreateOpen(StoreCase):
    def test_create_lays_out_directory_and_case_row(self):
        store = self.make_store()
        self.assertTrue((self.tmp / "case" / "state.sqlite3").is_file())
        for sub in ("blobs", "receipts", "proposals", "reports", "exports"):
            self.assertTrue((self.tmp / "case" / sub).is_dir(), sub)
        self.assertTrue(store.case_id.startswith("case_"))
        case = store.case()
        self.assertEqual(store.case_id, case["id"])
        self.assertEqual("Test case", case["payload"]["objective"])
        self.assertEqual(0, case["state_version"])
        self.assertEqual(0, store.state_version())
        self.assertEqual(S.SCHEMA_VERSION, store.schema_version())

    def test_create_keeps_supplied_case_id(self):
        store = self.make_store(payload={"id": "case_fixed", "objective": "x"})
        self.assertEqual("case_fixed", store.case_id)

    def test_create_rejects_bad_payloads_and_duplicates(self):
        with self.assertRaises(ValidationError):
            S.CaseStore.create(self.tmp / "bad", ["not", "an", "object"])  # type: ignore[arg-type]
        with self.assertRaises(ValidationError):
            S.CaseStore.create(self.tmp / "bad2", {"id": 7})
        self.make_store("dup")
        with self.assertRaises(ConflictError):
            S.CaseStore.create(self.tmp / "dup", {"objective": "again"})

    def test_pragmas(self):
        store = self.make_store()
        conn = store.connection
        self.assertEqual("wal", conn.execute("PRAGMA journal_mode").fetchone()[0])
        self.assertEqual(1, conn.execute("PRAGMA foreign_keys").fetchone()[0])
        self.assertEqual(5000, conn.execute("PRAGMA busy_timeout").fetchone()[0])

    def test_open_existing_store_sees_same_state(self):
        store = self.make_store()
        store.append_event("case.created", {"x": 1}, actor_role="controller", expected_state_version=0, idempotency_key="k1")
        case_id = store.case_id
        store.close()
        reopened = self.track(S.CaseStore.open(self.tmp / "case"))
        self.assertEqual(case_id, reopened.case_id)
        self.assertEqual(1, reopened.state_version())
        self.assertEqual(["case.created"], [e.type for e in reopened.events()])

    def test_open_missing_store_raises_not_found(self):
        with self.assertRaises(NotFoundError):
            S.CaseStore.open(self.tmp / "nowhere")
        (self.tmp / "empty").mkdir()
        with self.assertRaises(NotFoundError):
            S.CaseStore.open(self.tmp / "empty")

    def test_init_on_missing_directory_raises(self):
        with self.assertRaises(NotFoundError):
            S.CaseStore(self.tmp / "missing")

    def test_close_is_idempotent_and_closed_store_refuses_work(self):
        store = self.make_store()
        store.close()
        store.close()
        with self.assertRaises(ConflictError) as ctx:
            store.state_version()
        self.assertEqual("store_closed", ctx.exception.details["reason"])

    def test_context_manager_closes(self):
        with S.CaseStore.create(self.tmp / "ctx", {"objective": "x"}) as store:
            self.assertEqual(0, store.state_version())
        with self.assertRaises(ConflictError):
            store.state_version()

    def test_ddl_loaded_from_package_resource(self):
        ddl = S.load_ddl()
        self.assertIn("CREATE TABLE IF NOT EXISTS node_versions", ddl)
        self.assertIn("RAISE(ABORT", ddl)

    def test_all_tables_views_indexes_exist(self):
        store = self.make_store()
        names = {
            (r[0], r[1]) for r in store.connection.execute("SELECT type, name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'")
        }
        for table in ("meta", "cases", "runs", "tasks", "dispatches", "nodes", "node_versions", "node_current", "edges", "events", "receipts", "impact_queue", "budgets"):
            self.assertIn(("table", table), names)
        for view in ("proposals", "reviews", "decisions", "approvals", "validations", "challenges", "claims", "requirements", "sources", "artifacts"):
            self.assertIn(("view", view), names)
        for index in ("idx_nodes_case_kind", "idx_edges_to", "idx_edges_from", "idx_events_idempotency", "idx_tasks_run_state"):
            self.assertIn(("index", index), names)
        self.assertIn(("trigger", "trg_node_versions_no_update"), names)
        self.assertIn(("trigger", "trg_node_versions_no_delete"), names)


# --------------------------------------------------------------------------------------------------
# synced / network path refusal
# --------------------------------------------------------------------------------------------------


class SyncedPathRefusal(StoreCase):
    def test_refuses_each_marker_without_creating_anything(self):
        for marker in ("Dropbox", "OneDrive", "Google Drive", "iCloud Drive", "Library/Mobile Documents/com~apple~CloudDocs"):
            target = self.tmp / marker / "project" / ".aipt" / "case"
            with self.assertRaises(PolicyError) as ctx:
                S.CaseStore.create(target, {"objective": "x"})
            self.assertEqual("policy", ctx.exception.code)
            self.assertEqual("synced_or_network_filesystem", ctx.exception.details["reason"])
            self.assertFalse(target.exists(), marker)

    def test_marker_match_is_case_insensitive(self):
        with self.assertRaises(PolicyError):
            S.CaseStore.create(self.tmp / "dropbox" / "case", {"objective": "x"})

    def test_plain_temp_path_is_allowed(self):
        self.assertFalse(S.is_synced_or_network_path(self.tmp / "case"))
        self.make_store()

    def test_import_also_refuses_synced_target(self):
        store = self.make_store()
        store.export(self.tmp / "exp")
        with self.assertRaises(PolicyError):
            S.CaseStore.import_(self.tmp / "exp", self.tmp / "OneDrive" / "case")


# --------------------------------------------------------------------------------------------------
# transactions
# --------------------------------------------------------------------------------------------------


class Transactions(StoreCase):
    def test_begin_immediate_and_rollback_on_exception(self):
        store = self.make_store()
        with self.assertRaises(RuntimeError):
            with store.transaction() as conn:
                self.assertTrue(conn.in_transaction)
                store.insert("runs", {"id": "run_x", "state": "created"})
                raise RuntimeError("boom")
        self.assertFalse(store.connection.in_transaction)
        self.assertIsNone(store.get("runs", "run_x"))

    def test_commit_on_success(self):
        store = self.make_store()
        with store.transaction():
            store.insert("runs", {"id": "run_y", "state": "created"})
        self.assertFalse(store.connection.in_transaction)
        self.assertEqual("created", store.get("runs", "run_y")["state"])

    def test_nested_block_is_a_savepoint(self):
        store = self.make_store()
        with store.transaction():
            store.insert("runs", {"id": "run_outer", "state": "created"})
            try:
                with store.transaction():
                    store.insert("runs", {"id": "run_inner", "state": "created"})
                    raise RuntimeError("inner failure")
            except RuntimeError:
                pass
            self.assertTrue(store.connection.in_transaction)
        self.assertIsNotNone(store.get("runs", "run_outer"))
        self.assertIsNone(store.get("runs", "run_inner"))

    def test_second_writer_blocked_by_immediate_lock_raises_conflict(self):
        store = self.make_store()
        other = sqlite3.connect(str(store.db_path), isolation_level=None)
        other.execute("PRAGMA busy_timeout=100")
        try:
            other.execute("BEGIN IMMEDIATE")
            store.connection.execute("PRAGMA busy_timeout=100")
            with self.assertRaises(ConflictError) as ctx:
                with store.transaction():
                    pass
            self.assertEqual("database_locked", ctx.exception.details["reason"])
        finally:
            other.execute("ROLLBACK")
            other.close()


# --------------------------------------------------------------------------------------------------
# events
# --------------------------------------------------------------------------------------------------


class Events(StoreCase):
    def test_append_increments_state_version_and_assigns_seq(self):
        store = self.make_store()
        e1 = store.append_event("case.created", {"objective": "x"}, actor_role="controller", expected_state_version=0, idempotency_key="k1", payload_refs=[store.case_id])
        e2 = store.append_event("run.started", {"run": "r"}, actor_role="controller", actor_task=None, expected_state_version=1, idempotency_key="k2")
        self.assertEqual((1, 2), (e1.seq, e2.seq))
        self.assertEqual(2, store.state_version())
        self.assertTrue(e1.id.startswith("evt_"))
        self.assertEqual(store.case_id, e1.case_id)
        self.assertEqual((store.case_id,), e1.payload_refs)
        self.assertEqual(sha256_json({"objective": "x"}), e1.payload_sha256)
        self.assertEqual(e1.seq, e1["seq"])
        self.assertEqual([], V.validate(e1.to_dict(), V.load_schema("event")))
        self.assertEqual([e1, e2], store.events())
        self.assertEqual([e2], store.events(since_seq=1))
        self.assertEqual([e1], store.events(type="case.created"))
        self.assertEqual(e2, store.get_event(e2.id))
        with self.assertRaises(NotFoundError):
            store.get_event("evt_missing")

    def test_stale_expected_state_version_conflicts(self):
        store = self.make_store()
        store.append_event("a", {}, actor_role="controller", expected_state_version=0, idempotency_key="k1")
        with self.assertRaises(ConflictError) as ctx:
            store.append_event("b", {}, actor_role="controller", expected_state_version=0, idempotency_key="k2")
        self.assertEqual("conflict", ctx.exception.code)
        self.assertEqual("stale_state_version", ctx.exception.details["reason"])
        self.assertEqual({"expected": 0, "actual": 1}, {k: ctx.exception.details[k] for k in ("expected", "actual")})
        self.assertEqual(1, store.state_version())
        self.assertEqual(1, len(store.events()))

    def test_idempotent_replay_returns_existing_event_without_writing(self):
        store = self.make_store()
        first = store.append_event("task.admitted", {"task": "t1"}, actor_role="controller", expected_state_version=0, idempotency_key="admit:t1")
        replay = store.append_event("task.admitted", {"task": "t1"}, actor_role="controller", expected_state_version=0, idempotency_key="admit:t1")
        self.assertEqual(first, replay)
        self.assertEqual(1, store.state_version())
        self.assertEqual(1, len(store.events()))
        stale_replay = store.append_event("task.admitted", {"task": "t1"}, actor_role="controller", expected_state_version=42, idempotency_key="admit:t1")
        self.assertEqual(first.id, stale_replay.id)

    def test_same_key_different_payload_conflicts(self):
        store = self.make_store()
        store.append_event("task.admitted", {"task": "t1"}, actor_role="controller", expected_state_version=0, idempotency_key="admit:t1")
        with self.assertRaises(ConflictError) as ctx:
            store.append_event("task.admitted", {"task": "t2"}, actor_role="controller", expected_state_version=1, idempotency_key="admit:t1")
        self.assertEqual("idempotency_payload_mismatch", ctx.exception.details["reason"])
        with self.assertRaises(ConflictError):
            store.append_event("task.other", {"task": "t1"}, actor_role="controller", expected_state_version=1, idempotency_key="admit:t1")
        self.assertEqual(1, store.state_version())

    def test_event_validation(self):
        store = self.make_store()
        with self.assertRaises(ValidationError):
            store.append_event("x", ["not", "object"], actor_role="controller", expected_state_version=0, idempotency_key="k")  # type: ignore[arg-type]
        with self.assertRaises(ValidationError):
            store.append_event("x", {}, actor_role="Controller!", expected_state_version=0, idempotency_key="k")
        with self.assertRaises(ValidationError):
            store.append_event("x", {}, actor_role="controller", expected_state_version=0, idempotency_key="")
        self.assertEqual(0, store.state_version())

    def test_events_are_immutable_via_triggers(self):
        store = self.make_store()
        event = store.append_event("a", {}, actor_role="controller", expected_state_version=0, idempotency_key="k1")
        with self.assertRaises(sqlite3.IntegrityError):
            store.connection.execute("UPDATE events SET type='b' WHERE id=?", (event.id,))
        with self.assertRaises(sqlite3.IntegrityError):
            store.connection.execute("DELETE FROM events WHERE id=?", (event.id,))


# --------------------------------------------------------------------------------------------------
# nodes, versions, current
# --------------------------------------------------------------------------------------------------


class Versions(StoreCase):
    def test_new_node_and_put_version(self):
        store = self.make_store()
        node = store.new_node("claim", store.case_id)
        self.assertTrue(node.startswith("node_"))
        self.assertEqual("claim", store.get_node(node)["kind"])
        v1 = store.put_version(node, CLAIM, author_role="claim-checker", author_task="task_1", author_session="sess-1")
        v2 = store.put_version(node, {**CLAIM, "status": "contested"}, author_role="claim-checker")
        self.assertTrue(v1.startswith("ver_"))
        got = store.get_version(v1)
        self.assertEqual(node, got["node_id"])
        self.assertEqual(store.case_id, got["case_id"])
        self.assertEqual("claim", got["kind"])
        self.assertEqual(1, got["seq"])
        self.assertEqual(CLAIM, got["payload"])
        self.assertEqual(sha256_json(CLAIM), got["content_hash"])
        self.assertEqual(("claim-checker", "task_1", "sess-1"), (got["author_role"], got["author_task"], got["author_session"]))
        self.assertEqual(v1, got["version_id"])
        self.assertEqual([v1, v2], [v["id"] for v in store.versions_of(node)])
        self.assertEqual([1, 2], [v["seq"] for v in store.versions_of(node)])
        self.assertIsNone(store.current(node))

    def test_put_version_validates_payload_against_kind_schema(self):
        store = self.make_store()
        node = store.new_node("claim", store.case_id)
        with self.assertRaises(ValidationError) as ctx:
            store.put_version(node, {**CLAIM, "status": "done"}, author_role="claim-checker")
        self.assertTrue(any(err.startswith("/status:") for err in ctx.exception.errors))
        with self.assertRaises(ValidationError):
            store.put_version(node, "not a dict", author_role="claim-checker")  # type: ignore[arg-type]
        with self.assertRaises(ValidationError):
            store.put_version(node, CLAIM, author_role="")
        self.assertEqual([], store.versions_of(node))
        artifact_node = store.new_node("artifact", store.case_id)
        with self.assertRaises(ValidationError):
            store.put_version(artifact_node, CLAIM, author_role="builder")

    def test_new_node_rejects_unknown_kind_and_foreign_case(self):
        store = self.make_store()
        with self.assertRaises(ValidationError):
            store.new_node("widget", store.case_id)
        with self.assertRaises(NotFoundError):
            store.new_node("claim", "case_other")
        with self.assertRaises(NotFoundError):
            store.get_node("node_missing")
        with self.assertRaises(NotFoundError):
            store.get_version("ver_missing")
        with self.assertRaises(NotFoundError):
            store.versions_of("node_missing")
        with self.assertRaises(NotFoundError):
            store.put_version("node_missing", CLAIM, author_role="x")

    def test_node_versions_immutable_via_triggers(self):
        store = self.make_store()
        _node, version = self.add_claim(store)
        with self.assertRaises(sqlite3.IntegrityError) as up:
            store.connection.execute("UPDATE node_versions SET payload = '{}' WHERE id = ?", (version,))
        self.assertIn("immutable", str(up.exception))
        with self.assertRaises(sqlite3.IntegrityError) as de:
            store.connection.execute("DELETE FROM node_versions WHERE id = ?", (version,))
        self.assertIn("immutable", str(de.exception))
        self.assertEqual(CLAIM, store.get_version(version)["payload"])

    def test_set_current_records_event_and_updates_projection(self):
        store = self.make_store()
        node, v1 = self.add_claim(store)
        v2 = store.put_version(node, {**CLAIM, "status": "contested"}, author_role="claim-checker")
        before = store.state_version()
        event = store.set_current(node, v1, status="supported")
        self.assertEqual("node.current_changed", event.type)
        self.assertEqual("controller", event.actor_role)
        self.assertEqual(before + 1, store.state_version())
        self.assertEqual({"node_id": node, "version_id": v1, "status": "supported", "applicability": "current", "kind": "claim"}, {k: store.current(node)[k] for k in ("node_id", "version_id", "status", "applicability", "kind")})
        self.assertIsNone(event.payload["previous_version_id"])
        event2 = store.set_current(node, v2, status="contested", applicability="unestablished", by="lineage-steward", actor_task="task_9")
        self.assertEqual(v1, event2.payload["previous_version_id"])
        self.assertEqual("lineage-steward", event2.actor_role)
        self.assertEqual("task_9", event2.actor_task)
        self.assertEqual((node, v2), tuple(event2.payload_refs))
        current = store.current(node)
        self.assertEqual((v2, "contested", "unestablished"), (current["version_id"], current["status"], current["applicability"]))
        self.assertEqual(2, len(store.events(type="node.current_changed")))
        self.assertEqual(1, store.connection.execute("SELECT COUNT(*) FROM node_current").fetchone()[0])

    def test_set_current_checks_ownership_status_and_applicability(self):
        store = self.make_store()
        node_a, v_a = self.add_claim(store)
        _node_b, v_b = self.add_claim(store)
        with self.assertRaises(ValidationError):
            store.set_current(node_a, v_b, status="supported")
        with self.assertRaises(ValidationError):
            store.set_current(node_a, v_a, status="done")
        with self.assertRaises(ValidationError):
            store.set_current(node_a, v_a, status="")
        with self.assertRaises(ValidationError):
            store.set_current(node_a, v_a, status="supported", applicability="maybe")
        with self.assertRaises(NotFoundError):
            store.set_current(node_a, "ver_missing", status="supported")
        self.assertIsNone(store.current(node_a))
        self.assertEqual(0, store.state_version())
        proposal_node = store.new_node("approval", store.case_id)
        approval = {"granted_by": "delegation", "scope": "x", "allowed_decisions": ["R1"], "allowed_actions": [], "bound_version_id": "ver_1", "limits": None, "expires_at": None, "revoked": False, "provenance": {"channel": "cli", "attested": False}}
        version = store.put_version(proposal_node, approval, author_role="decision-authority")
        store.set_current(proposal_node, version, status="active")
        self.assertEqual("active", store.current(proposal_node)["status"])

    def test_find_current_filters_payload_via_json_extract(self):
        store = self.make_store()
        n1, v1 = self.add_claim(store, statement="A")
        n2, v2 = self.add_claim(store, statement="B", confidence_label="low")
        n3, _v3 = self.add_claim(store, statement="C")
        store.set_current(n1, v1, status="supported")
        store.set_current(n2, v2, status="supported")
        self.assertEqual([n1, n2], [r["node_id"] for r in store.find_current("claim")])
        rows = store.find_current("claim", confidence_label="low")
        self.assertEqual([n2], [r["node_id"] for r in rows])
        self.assertEqual("B", rows[0]["payload"]["statement"])
        self.assertEqual(v2, rows[0]["version_id"])
        self.assertEqual("supported", rows[0]["status"])
        self.assertEqual([], store.find_current("claim", statement="C"))
        self.assertEqual([], store.find_current("claim", statement="A", confidence_label="low"))
        self.assertEqual([n1, n2], [r["node_id"] for r in store.find_current("claim", missing_key=None)])
        self.assertEqual([], store.find_current("requirement"))
        with self.assertRaises(ValidationError):
            store.find_current("gadget")
        with self.assertRaises(ValidationError):
            store.find_current("claim", **{"bad key": 1})

    def test_find_current_handles_artifact_kind_filter_booleans_and_nested_paths(self):
        store = self.make_store()
        art = store.new_node("artifact", store.case_id)
        av = store.put_version(art, ARTIFACT, author_role="context-analyst")
        store.set_current(art, av, status="proposed")
        other = store.new_node("artifact", store.case_id)
        ov = store.put_version(other, {**ARTIFACT, "kind": "design.md"}, author_role="context-analyst")
        store.set_current(other, ov, status="implemented_not_verified")
        self.assertEqual([av], [r["version_id"] for r in store.find_current("artifact", kind="context-brief.md")])
        req = store.new_node("requirement", store.case_id)
        rv = store.put_version(req, REQUIREMENT, author_role="human-owner")
        store.set_current(req, rv, status="approved")
        self.assertEqual([rv], [r["version_id"] for r in store.find_current("requirement", protected=True)])
        self.assertEqual([], store.find_current("requirement", protected=False))
        dec = store.new_node("decision", store.case_id)
        dv = store.put_version(dec, DECISION, author_role="decision-authority")
        store.set_current(dec, dv, status="accepted")
        self.assertEqual([dv], [r["version_id"] for r in store.find_current("decision", authority_basis__kind="delegation")])
        self.assertEqual([], store.find_current("decision", authority_basis__kind="human_input"))

    def test_views_project_current_versions_by_kind(self):
        store = self.make_store()
        node, v1 = self.add_claim(store)
        v2 = store.put_version(node, {**CLAIM, "status": "contested"}, author_role="claim-checker")
        self.assertEqual([], store.connection.execute("SELECT * FROM claims").fetchall())
        store.set_current(node, v2, status="contested")
        rows = store.connection.execute("SELECT node_id, version_id, status, payload, case_id FROM claims").fetchall()
        self.assertEqual(1, len(rows))
        self.assertEqual((node, v2, "contested", store.case_id), (rows[0][0], rows[0][1], rows[0][2], rows[0][4]))
        self.assertEqual("contested", json.loads(rows[0][3])["status"])
        self.assertEqual([], store.connection.execute("SELECT * FROM artifacts").fetchall())
        store.set_current(node, v1, status="supported")
        self.assertEqual(v1, store.connection.execute("SELECT version_id FROM claims").fetchone()[0])


# --------------------------------------------------------------------------------------------------
# edges
# --------------------------------------------------------------------------------------------------


class Edges(StoreCase):
    def test_add_edge_defaults_to_proposed_and_filters(self):
        store = self.make_store()
        _n1, v1 = self.add_claim(store)
        _n2, v2 = self.add_claim(store, statement="B")
        edge = store.add_edge(v1, v2, "depends_on", impact_policy="review", reason="derived", proposed_by="context-analyst")
        self.assertTrue(edge.startswith("edge_"))
        row = store.get_edge(edge)
        self.assertEqual((v1, v2, "depends_on", "review", "derived", "context-analyst", "proposed"), (row["from_version"], row["to_version"], row["relation"], row["impact_policy"], row["reason"], row["proposed_by"], row["status"]))
        self.assertEqual(store.case_id, row["case_id"])
        self.assertEqual([], store.edges_from(v1))
        self.assertEqual([edge], [e["id"] for e in store.edges_from(v1, status=None)])
        self.assertEqual([edge], [e["id"] for e in store.edges_from(v1, status="proposed")])
        self.assertEqual([edge], [e["id"] for e in store.edges_to(v2, "depends_on", status="proposed")])
        self.assertEqual([], store.edges_to(v2, "supports", status="proposed"))
        self.assertEqual([], store.edges_to(v1, status=None))

    def test_set_edge_status(self):
        store = self.make_store()
        _n1, v1 = self.add_claim(store)
        _n2, v2 = self.add_claim(store, statement="B")
        edge = store.add_edge(v1, v2, "supports", reason="cites", proposed_by="claim-checker")
        before = store.state_version()
        updated = store.set_edge_status(edge, "accepted", "lineage-steward")
        self.assertEqual("accepted", updated["status"])
        self.assertEqual("lineage-steward", updated["status_changed_by"])
        self.assertIsNotNone(updated["status_changed_at"])
        self.assertEqual([edge], [e["id"] for e in store.edges_from(v1)])
        self.assertEqual([edge], [e["id"] for e in store.edges_to(v2, "supports")])
        self.assertEqual(before, store.state_version())
        store.set_edge_status(edge, "rejected", "lineage-steward")
        self.assertEqual([], store.edges_from(v1))
        with self.assertRaises(ValidationError):
            store.set_edge_status(edge, "maybe", "x")
        with self.assertRaises(ValidationError):
            store.set_edge_status(edge, "accepted", "")
        with self.assertRaises(NotFoundError):
            store.set_edge_status("edge_missing", "accepted", "x")

    def test_add_edge_validation(self):
        store = self.make_store()
        _n1, v1 = self.add_claim(store)
        _n2, v2 = self.add_claim(store, statement="B")
        with self.assertRaises(ValidationError):
            store.add_edge(v1, v2, "related_to", reason="r", proposed_by="x")
        with self.assertRaises(ValidationError):
            store.add_edge(v1, v2, "supports", status="pending", reason="r", proposed_by="x")
        with self.assertRaises(ValidationError):
            store.add_edge(v1, v2, "depends_on", impact_policy="explode", reason="r", proposed_by="x")
        with self.assertRaises(ValidationError):
            store.add_edge(v1, v2, "supports", reason="", proposed_by="x")
        with self.assertRaises(NotFoundError):
            store.add_edge(v1, "ver_missing", "supports", reason="r", proposed_by="x")
        with self.assertRaises(ValidationError):
            store.edges_from(v1, relation="nope", status=None)
        self.assertEqual(0, store.connection.execute("SELECT COUNT(*) FROM edges").fetchone()[0])
        with self.assertRaises(NotFoundError):
            store.get_edge("edge_missing")

    def test_edges_ordered_by_insertion(self):
        store = self.make_store()
        _n1, v1 = self.add_claim(store)
        targets = [self.add_claim(store, statement=s)[1] for s in ("B", "C", "D")]
        ids = [store.add_edge(v1, t, "supports", reason="r", proposed_by="x", status="accepted") for t in targets]
        self.assertEqual(ids, [e["id"] for e in store.edges_from(v1)])
        self.assertEqual(targets, [e["to_version"] for e in store.edges_from(v1, "supports")])


# --------------------------------------------------------------------------------------------------
# blobs
# --------------------------------------------------------------------------------------------------


class Blobs(StoreCase):
    def test_put_get_blob_content_addressed(self):
        store = self.make_store()
        data = b"hello blob"
        digest = store.put_blob(data)
        self.assertEqual(sha256_bytes(data), digest)
        self.assertEqual(self.tmp / "case" / "blobs" / digest, store.blob_path(digest))
        self.assertTrue(store.blob_path(digest).is_file())
        self.assertTrue(store.has_blob(digest))
        self.assertEqual(data, store.get_blob(digest))
        self.assertEqual(digest, store.put_blob(bytearray(data)))
        self.assertEqual([digest], store.list_blobs())
        self.assertEqual(1, len(list((self.tmp / "case" / "blobs").iterdir())))

    def test_blob_errors(self):
        store = self.make_store()
        with self.assertRaises(ValidationError):
            store.put_blob("text")  # type: ignore[arg-type]
        with self.assertRaises(ValidationError):
            store.blob_path("../etc/passwd")
        with self.assertRaises(ValidationError):
            store.blob_path("ABCD")
        missing = "0" * 64
        self.assertFalse(store.has_blob(missing))
        self.assertEqual(store.blobs_dir / missing, store.blob_path(missing))
        with self.assertRaises(NotFoundError):
            store.get_blob(missing)
        digest = store.put_blob(b"x")
        store.blob_path(digest).write_bytes(b"tampered")
        with self.assertRaises(ConflictError) as ctx:
            store.get_blob(digest)
        self.assertEqual("blob_hash_mismatch", ctx.exception.details["reason"])


# --------------------------------------------------------------------------------------------------
# operational tables
# --------------------------------------------------------------------------------------------------


class OperationalTables(StoreCase):
    def test_insert_get_with_json_columns_and_extra_keys(self):
        store = self.make_store()
        run_id = store.insert("runs", {"workflow_id": "W02", "mode": "standard", "state": "created", "budget": {"max_worker_tasks": 3}, "limitations": [], "custom_flag": True, "nested": {"a": [1, 2]}})
        self.assertTrue(run_id.startswith("run_"))
        row = store.get("runs", run_id)
        self.assertEqual(run_id, row["id"])
        self.assertEqual(store.case_id, row["case_id"])
        self.assertEqual({"max_worker_tasks": 3}, row["budget"])
        self.assertEqual([], row["limitations"])
        self.assertIs(True, row["custom_flag"])
        self.assertEqual({"a": [1, 2]}, row["nested"])
        self.assertIsNotNone(row["created_at"])
        self.assertNotIn("extra_json", row)
        self.assertIsNone(store.get("runs", "run_missing"))

    def test_insert_minting_and_key_rules(self):
        store = self.make_store()
        task_id = store.insert("tasks", {"run_id": "run_1", "role_id": "context-analyst", "state": "planned", "dependencies": ["task_0"], "attempt": 1})
        self.assertTrue(task_id.startswith("task_"))
        self.assertTrue(store.insert("dispatches", {"task_id": task_id}).startswith("disp_"))
        self.assertTrue(store.insert("impact_queue", {"affected_version": "ver_1", "state": "review_required"}).startswith("imp_"))
        self.assertEqual("run_1", store.insert("budgets", {"run_id": "run_1", "used_tasks": 0, "running": 0}))
        self.assertEqual("b2", store.insert("budgets", {"id": "b2", "run_id": "run_2"}))
        with self.assertRaises(ValidationError):
            store.insert("budgets", {"used_tasks": 0})
        with self.assertRaises(ValidationError):
            store.insert("runs", {"id": ""})
        with self.assertRaises(ValidationError):
            store.insert("runs", {"extra_json": {}})
        with self.assertRaises(ValidationError):
            store.insert("runs", {"bad key": 1})
        with self.assertRaises(ValidationError):
            store.insert("runs", ["row"])  # type: ignore[arg-type]
        with self.assertRaises(ConflictError) as ctx:
            store.insert("tasks", {"id": task_id, "state": "planned"})
        self.assertEqual("duplicate_key", ctx.exception.details["reason"])

    def test_only_six_tables_allowed(self):
        store = self.make_store()
        self.assertEqual(("runs", "tasks", "dispatches", "receipts", "impact_queue", "budgets"), S.OPERATIONAL_TABLES)
        self.assertEqual(set(S.OPERATIONAL_TABLES), set(S.JSON_COLUMNS))
        for table in ("cases", "nodes", "node_versions", "events", "meta", "edges", "sqlite_master", "runs; DROP TABLE runs"):
            with self.assertRaises(ValueError):
                store.insert(table, {"id": "x"})
            with self.assertRaises(ValueError):
                store.get(table, "x")
            with self.assertRaises(ValueError):
                store.query(table)
            with self.assertRaises(ValueError):
                store.update(table, "x", {})

    def test_update_with_expected(self):
        store = self.make_store()
        task_id = store.insert("tasks", {"run_id": "run_1", "state": "ready", "attempt": 1, "flag": "a"})
        updated = store.update("tasks", task_id, {"state": "admitted", "snapshot": {"kind": "git"}, "flag": "b", "note": "x"}, expected={"state": "ready", "flag": "a"})
        self.assertEqual(("admitted", {"kind": "git"}, "b", "x"), (updated["state"], updated["snapshot"], updated["flag"], updated["note"]))
        self.assertEqual(updated, store.get("tasks", task_id))
        with self.assertRaises(ConflictError) as ctx:
            store.update("tasks", task_id, {"state": "running"}, expected={"state": "ready"})
        self.assertEqual("expected_mismatch", ctx.exception.details["reason"])
        self.assertEqual({"state": "admitted"}, ctx.exception.details["actual"])
        self.assertEqual("admitted", store.get("tasks", task_id)["state"])
        store.update("tasks", task_id, {"state": "running"}, expected={"state": "admitted", "note": "x", "snapshot": {"kind": "git"}})
        self.assertEqual("running", store.get("tasks", task_id)["state"])
        with self.assertRaises(NotFoundError):
            store.update("tasks", "task_missing", {"state": "x"})
        with self.assertRaises(ValidationError):
            store.update("tasks", task_id, {"id": "task_other"})
        with self.assertRaises(ValidationError):
            store.update("tasks", task_id, {"extra_json": "{}"})
        store.update("tasks", task_id, {"id": task_id, "attempt": 2})
        self.assertEqual(2, store.get("tasks", task_id)["attempt"])

    def test_update_expected_compares_booleans_from_extra(self):
        store = self.make_store()
        run_id = store.insert("runs", {"state": "created", "paused": False})
        store.update("runs", run_id, {"paused": True}, expected={"paused": False})
        self.assertIs(True, store.get("runs", run_id)["paused"])
        with self.assertRaises(ConflictError):
            store.update("runs", run_id, {"paused": False}, expected={"paused": False})

    def test_query_by_columns_and_extra_keys_in_rowid_order(self):
        store = self.make_store()
        ids = [store.insert("tasks", {"run_id": "run_1", "state": s, "stage_id": f"s{i}", "tag": "x" if i % 2 else "y"}) for i, s in enumerate(["ready", "ready", "accepted"])]
        store.insert("tasks", {"run_id": "run_2", "state": "ready"})
        self.assertEqual(ids[:2], [r["id"] for r in store.query("tasks", run_id="run_1", state="ready")])
        self.assertEqual(ids, [r["id"] for r in store.query("tasks", run_id="run_1")])
        self.assertEqual([ids[1]], [r["id"] for r in store.query("tasks", run_id="run_1", tag="x")])
        self.assertEqual(4, len(store.query("tasks")))
        self.assertEqual([ids[2]], [r["id"] for r in store.query("tasks", state="accepted")])
        self.assertEqual(1, len(store.query("tasks", tag=None)))
        self.assertEqual(4, len(store.query("tasks", role_id=None)))
        self.assertEqual([], store.query("tasks", state="running"))
        with self.assertRaises(ValidationError):
            store.query("tasks", **{"state = 'x' OR 1": 1})

    def test_query_json_column_equality(self):
        store = self.make_store()
        a = store.insert("runs", {"budget": {"max": 3}})
        store.insert("runs", {"budget": {"max": 4}})
        self.assertEqual([a], [r["id"] for r in store.query("runs", budget={"max": 3})])


# --------------------------------------------------------------------------------------------------
# receipts
# --------------------------------------------------------------------------------------------------


class Receipts(StoreCase):
    def test_put_receipt_validates_and_stores(self):
        store = self.make_store()
        self.assertEqual("rcpt_1", store.put_receipt(RECEIPT))
        self.assertEqual(RECEIPT, store.get_receipt("rcpt_1"))
        self.assertEqual([RECEIPT], store.receipts_for_task("task_demo"))
        self.assertEqual([], store.receipts_for_task("task_other"))
        self.assertIsNone(store.get_receipt("rcpt_missing"))
        row = store.get("receipts", "rcpt_1")
        self.assertEqual(("task_demo", 0, "controller", store.case_id), (row["task_id"], row["exit_status"], row["observation_source"], row["case_id"]))
        self.assertEqual(RECEIPT, row["payload"])
        second = {**RECEIPT, "id": "rcpt_2", "exit_status": None, "timed_out": True, "ended_at": None}
        store.put_receipt(second)
        self.assertEqual([RECEIPT, second], store.receipts_for_task("task_demo"))
        self.assertEqual([second], [r["payload"] for r in store.query("receipts", exit_status=None)])

    def test_put_receipt_rejects_invalid_and_conflicting(self):
        store = self.make_store()
        bad = dict(RECEIPT)
        del bad["snapshot"]
        with self.assertRaises(ValidationError) as ctx:
            store.put_receipt(bad)
        self.assertTrue(any("snapshot" in err for err in ctx.exception.errors))
        with self.assertRaises(ValidationError):
            store.put_receipt({**RECEIPT, "observation_source": "guessed"})
        with self.assertRaises(ValidationError):
            store.put_receipt({**RECEIPT, "proves": "everything"})
        with self.assertRaises(ValidationError):
            store.put_receipt("rcpt")  # type: ignore[arg-type]
        self.assertEqual([], store.query("receipts"))
        store.put_receipt(RECEIPT)
        self.assertEqual("rcpt_1", store.put_receipt(copy.deepcopy(RECEIPT)))
        self.assertEqual(1, len(store.query("receipts")))
        with self.assertRaises(ConflictError) as conflict:
            store.put_receipt({**RECEIPT, "exit_status": 1})
        self.assertEqual("receipt_payload_mismatch", conflict.exception.details["reason"])


# --------------------------------------------------------------------------------------------------
# backup, export/import, integrity, migrations
# --------------------------------------------------------------------------------------------------


def populate(store: S.CaseStore) -> dict:
    """Write a representative slice of every record type and return the ids for later comparison."""
    store.append_event("case.created", {"objective": "x"}, actor_role="controller", expected_state_version=0, idempotency_key="case.created")
    claim_node = store.new_node("claim", store.case_id)
    c1 = store.put_version(claim_node, CLAIM, author_role="claim-checker", author_session="sess-1")
    c2 = store.put_version(claim_node, {**CLAIM, "status": "contested"}, author_role="claim-checker")
    store.set_current(claim_node, c2, status="contested")
    req_node = store.new_node("requirement", store.case_id)
    r1 = store.put_version(req_node, REQUIREMENT, author_role="human-owner")
    store.set_current(req_node, r1, status="approved")
    art_node = store.new_node("artifact", store.case_id)
    a1 = store.put_version(art_node, ARTIFACT, author_role="context-analyst", author_task="task_demo")
    store.set_current(art_node, a1, status="proposed")
    e1 = store.add_edge(a1, r1, "implements", reason="claims to implement", proposed_by="context-analyst")
    e2 = store.add_edge(a1, c2, "depends_on", impact_policy="review", reason="derived", proposed_by="context-analyst", status="accepted")
    store.set_edge_status(e1, "accepted", "lineage-steward")
    blobs = [store.put_blob(b"first blob"), store.put_blob(b"second blob \x00\xff")]
    run_id = store.insert("runs", {"workflow_id": "W02", "mode": "standard", "state": "executing", "budget": {"max_worker_tasks": 3}, "host": "codex"})
    task_id = store.insert("tasks", {"run_id": run_id, "role_id": "context-analyst", "state": "running", "dependencies": [], "attempt": 1, "custom": {"k": True}})
    disp = store.insert("dispatches", {"task_id": task_id, "run_id": run_id, "host": "codex", "native_child_id": "child-1", "execution_mode": "native", "observed_by": "native"})
    store.put_receipt({**RECEIPT, "task_id": task_id})
    imp = store.insert("impact_queue", {"affected_version": a1, "changed_version": c2, "impact_policy": "review", "state": "review_required", "path": [c2, a1]})
    store.insert("budgets", {"run_id": run_id, "mode": "standard", "max_worker_tasks": 3, "used_tasks": 1, "running": 1})
    return {"claim_node": claim_node, "versions": [c1, c2, r1, a1], "edges": [e1, e2], "blobs": blobs, "run": run_id, "task": task_id, "disp": disp, "imp": imp}


def snapshot(store: S.CaseStore) -> dict:
    """Everything that must survive backup/export/import, as plain JSON-comparable data."""
    conn = store.connection
    tables = {}
    for table in ("meta", "cases", "nodes", "node_versions", "node_current", "edges", "events", "runs", "tasks", "dispatches", "receipts", "impact_queue", "budgets"):
        tables[table] = [dict(r) for r in conn.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()]
    return {"tables": tables, "events": [e.to_dict() for e in store.events()], "blobs": store.list_blobs(), "state_version": store.state_version()}


class Backup(StoreCase):
    def test_backup_restores_consistent_snapshot(self):
        store = self.make_store()
        ids = populate(store)
        before = snapshot(store)
        dest = store.backup(self.tmp / "bk" / "state.sqlite3")
        self.assertEqual(self.tmp / "bk" / "state.sqlite3", dest)
        store.append_event("after.backup", {}, actor_role="controller", expected_state_version=store.state_version(), idempotency_key="after")
        restored = self.track(S.CaseStore.open(self.tmp / "bk"))
        after = snapshot(restored)
        self.assertEqual(before["tables"], after["tables"])
        self.assertEqual(before["events"], after["events"])
        self.assertEqual(before["state_version"], after["state_version"])
        self.assertEqual(ids["versions"][1], restored.current(ids["claim_node"])["version_id"])
        self.assertEqual(before["state_version"] + 1, store.state_version())
        self.assertEqual("ok", sqlite3.connect(str(dest)).execute("PRAGMA integrity_check").fetchone()[0])
        self.assertEqual([p for p in restored.integrity_check() if not p.startswith("blobs")], [])

    def test_backup_overwrites_stale_file_and_refuses_live_db(self):
        store = self.make_store()
        target = self.tmp / "bk.sqlite3"
        target.write_bytes(b"garbage")
        store.backup(target)
        self.assertEqual("ok", sqlite3.connect(str(target)).execute("PRAGMA integrity_check").fetchone()[0])
        with self.assertRaises(PolicyError):
            store.backup(store.db_path)

    def test_backup_refused_inside_open_transaction(self):
        store = self.make_store()
        populate(store)
        with store.transaction():
            store.insert("runs", {"id": "run_uncommitted", "state": "created"})
            with self.assertRaises(ConflictError) as ctx:
                store.backup(self.tmp / "mid.sqlite3")
            self.assertEqual("transaction_open", ctx.exception.details["reason"])
        self.assertFalse((self.tmp / "mid.sqlite3").exists())
        self.assertIsNotNone(store.get("runs", "run_uncommitted"))
        store.backup(self.tmp / "after.sqlite3")
        copy_conn = sqlite3.connect(str(self.tmp / "after.sqlite3"))
        try:
            self.assertEqual(1, copy_conn.execute("SELECT COUNT(*) FROM runs WHERE id='run_uncommitted'").fetchone()[0])
        finally:
            copy_conn.close()


class ExportImport(StoreCase):
    def test_round_trip_preserves_every_id_version_edge_event_and_blob(self):
        store = self.make_store()
        ids = populate(store)
        original = snapshot(store)
        manifest = store.export(self.tmp / "exp")
        self.assertEqual(store.case_id, manifest["case_id"])
        self.assertEqual(S.SCHEMA_VERSION, manifest["schema_version"])
        self.assertEqual(2, manifest["blobs"]["count"])
        self.assertEqual(4, manifest["tables"]["node_versions"]["rows"])
        self.assertEqual(sorted(ids["blobs"]), manifest["blobs"]["sha256"])
        for table in ("meta", "cases", "runs", "tasks", "dispatches", "nodes", "node_versions", "node_current", "edges", "events", "receipts", "impact_queue", "budgets"):
            self.assertTrue((self.tmp / "exp" / f"{table}.jsonl").is_file(), table)
        self.assertEqual(manifest, json.loads((self.tmp / "exp" / "manifest.json").read_text()))
        lines = (self.tmp / "exp" / "node_versions.jsonl").read_text().splitlines()
        self.assertEqual(ids["versions"], [json.loads(line)["id"] for line in lines])
        self.assertEqual(CLAIM, json.loads(lines[0])["payload"])

        imported = self.track(S.CaseStore.import_(self.tmp / "exp", self.tmp / "imported"))
        self.assertEqual(store.case_id, imported.case_id)
        copy_ = snapshot(imported)
        self.assertEqual(original, copy_)
        self.assertEqual([], imported.integrity_check())
        for version in ids["versions"]:
            self.assertEqual(store.get_version(version), imported.get_version(version))
        for edge in ids["edges"]:
            self.assertEqual(store.get_edge(edge), imported.get_edge(edge))
        for digest in ids["blobs"]:
            self.assertEqual(store.get_blob(digest), imported.get_blob(digest))
        self.assertEqual(store.get("tasks", ids["task"]), imported.get("tasks", ids["task"]))
        self.assertEqual(store.receipts_for_task(ids["task"]), imported.receipts_for_task(ids["task"]))
        self.assertEqual(store.current(ids["claim_node"]), imported.current(ids["claim_node"]))
        self.assertEqual(store.find_current("artifact", kind="context-brief.md"), imported.find_current("artifact", kind="context-brief.md"))
        re_export = imported.export(self.tmp / "exp2")
        self.assertEqual({t: v["sha256"] for t, v in manifest["tables"].items()}, {t: v["sha256"] for t, v in re_export["tables"].items()})
        self.assertEqual(manifest["blobs"], re_export["blobs"])
        imported.append_event("post.import", {}, actor_role="controller", expected_state_version=imported.state_version(), idempotency_key="post")
        self.assertEqual(original["state_version"] + 1, imported.state_version())

    def test_import_refusals(self):
        store = self.make_store()
        populate(store)
        store.export(self.tmp / "exp")
        with self.assertRaises(NotFoundError):
            S.CaseStore.import_(self.tmp / "nope", self.tmp / "target")
        self.make_store("occupied")
        with self.assertRaises(ConflictError):
            S.CaseStore.import_(self.tmp / "exp", self.tmp / "occupied")
        manifest_path = self.tmp / "exp" / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest_path.write_text(json.dumps({**manifest, "schema_version": S.SCHEMA_VERSION + 1}))
        with self.assertRaises(ValidationError) as ctx:
            S.CaseStore.import_(self.tmp / "exp", self.tmp / "target2")
        self.assertEqual("schema_version_mismatch", ctx.exception.details["reason"])
        manifest_path.write_text(json.dumps({**manifest, "format": "other"}))
        with self.assertRaises(ValidationError):
            S.CaseStore.import_(self.tmp / "exp", self.tmp / "target3")
        manifest_path.write_text(json.dumps(manifest))
        digest = manifest["blobs"]["sha256"][0]
        (self.tmp / "exp" / "blobs" / digest).write_bytes(b"corrupted")
        with self.assertRaises(ConflictError) as blob_ctx:
            S.CaseStore.import_(self.tmp / "exp", self.tmp / "target4")
        self.assertEqual("blob_hash_mismatch", blob_ctx.exception.details["reason"])
        self.assertFalse((self.tmp / "target2" / "state.sqlite3").exists())

    def test_import_rejects_unknown_columns(self):
        store = self.make_store()
        populate(store)
        store.export(self.tmp / "exp")
        path = self.tmp / "exp" / "runs.jsonl"
        row = json.loads(path.read_text().splitlines()[0])
        row["not_a_column"] = 1
        path.write_text(json.dumps(row) + "\n")
        with self.assertRaises(ValidationError):
            S.CaseStore.import_(self.tmp / "exp", self.tmp / "target")


class Integrity(StoreCase):
    def test_clean_store_passes(self):
        store = self.make_store()
        populate(store)
        self.assertEqual([], store.integrity_check())

    def test_detects_tampering(self):
        store = self.make_store()
        ids = populate(store)
        store.blob_path(ids["blobs"][0]).write_bytes(b"tampered")
        store.connection.execute("UPDATE cases SET state_version = state_version + 5")
        problems = store.integrity_check()
        self.assertTrue(any(p.startswith("blobs:") for p in problems), problems)
        self.assertTrue(any("state_version" in p for p in problems), problems)
        store.connection.execute("UPDATE cases SET state_version = state_version - 5")
        other_node = store.new_node("claim", store.case_id)
        other_version = store.put_version(other_node, CLAIM, author_role="claim-checker")
        store.connection.execute("UPDATE node_current SET version_id = ? WHERE node_id = ?", (other_version, ids["claim_node"]))
        problems = store.integrity_check()
        self.assertTrue(any(p.startswith("node_current:") and "of node" in p for p in problems), problems)
        store.connection.execute("PRAGMA foreign_keys=OFF")
        store.connection.execute("INSERT INTO nodes(id, case_id, kind, created_at) VALUES ('node_orphan', 'case_ghost', 'claim', 'now')")
        store.connection.execute("PRAGMA foreign_keys=ON")
        problems = store.integrity_check()
        self.assertTrue(any(p.startswith("foreign_key_check:") for p in problems), problems)


class Migrations(StoreCase):
    def setUp(self) -> None:
        super().setUp()
        self._saved = (S.SCHEMA_VERSION, list(S.MIGRATIONS))

    def tearDown(self) -> None:
        S.SCHEMA_VERSION, S.MIGRATIONS = self._saved[0], list(self._saved[1])
        super().tearDown()

    def test_open_newer_schema_raises(self):
        store = self.make_store()
        store.connection.execute("UPDATE meta SET value = ? WHERE key = 'schema_version'", (str(S.SCHEMA_VERSION + 1),))
        store.close()
        with self.assertRaises(ConflictError) as ctx:
            S.CaseStore.open(self.tmp / "case")
        self.assertEqual("schema_version_unsupported", ctx.exception.details["reason"])

    def test_migration_applies_after_backup_in_one_transaction(self):
        store = self.make_store()
        ids = populate(store)
        before = snapshot(store)
        store.close()
        S.SCHEMA_VERSION = 3
        S.MIGRATIONS = [
            (1, 2, ["ALTER TABLE runs ADD COLUMN migrated_flag TEXT", "UPDATE runs SET migrated_flag = 'v2'"]),
            (2, 3, "CREATE TABLE migration_marker (id INTEGER PRIMARY KEY)"),
        ]
        migrated = self.track(S.CaseStore.open(self.tmp / "case"))
        self.assertEqual(3, migrated.schema_version())
        self.assertEqual("v2", migrated.get("runs", ids["run"])["migrated_flag"])
        self.assertIsNotNone(migrated.connection.execute("SELECT name FROM sqlite_master WHERE name='migration_marker'").fetchone())
        backups = sorted((self.tmp / "case" / "backups").glob("pre-migration-v1-*.sqlite3"))
        self.assertEqual(1, len(backups))
        backup_conn = sqlite3.connect(str(backups[0]))
        try:
            self.assertEqual("1", backup_conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0])
            self.assertNotIn("migrated_flag", [r[1] for r in backup_conn.execute("PRAGMA table_info(runs)").fetchall()])
            self.assertEqual(len(before["events"]), backup_conn.execute("SELECT COUNT(*) FROM events").fetchone()[0])
        finally:
            backup_conn.close()
        after = snapshot(migrated)
        self.assertEqual(before["events"], after["events"])
        self.assertEqual(before["tables"]["node_versions"], after["tables"]["node_versions"])
        self.assertEqual(before["tables"]["edges"], after["tables"]["edges"])
        self.assertEqual(before["blobs"], after["blobs"])
        self.assertEqual([], migrated.integrity_check())
        migrated.close()
        reopened = self.track(S.CaseStore.open(self.tmp / "case"))
        self.assertEqual(3, reopened.schema_version())
        self.assertEqual(1, len(list((self.tmp / "case" / "backups").glob("pre-migration-*.sqlite3"))))

    def test_failed_migration_rolls_back_but_keeps_backup(self):
        store = self.make_store()
        populate(store)
        store.close()
        S.SCHEMA_VERSION = 2
        S.MIGRATIONS = [(1, 2, ["ALTER TABLE runs ADD COLUMN ok_col TEXT", "INSERT INTO no_such_table VALUES (1)"])]
        with self.assertRaises(sqlite3.OperationalError):
            S.CaseStore.open(self.tmp / "case")
        self.assertEqual(1, len(list((self.tmp / "case" / "backups").glob("pre-migration-v1-*.sqlite3"))))
        raw = sqlite3.connect(str(self.tmp / "case" / "state.sqlite3"))
        try:
            self.assertEqual("1", raw.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0])
            self.assertNotIn("ok_col", [r[1] for r in raw.execute("PRAGMA table_info(runs)").fetchall()])
        finally:
            raw.close()

    def test_missing_migration_path_is_a_conflict(self):
        store = self.make_store()
        store.close()
        S.SCHEMA_VERSION = 2
        S.MIGRATIONS = []
        with self.assertRaises(ConflictError) as ctx:
            S.CaseStore.open(self.tmp / "case")
        self.assertEqual("no_migration_path", ctx.exception.details["reason"])
        self.assertEqual([], list((self.tmp / "case" / "backups").glob("*.sqlite3")))

    def test_new_store_is_created_at_current_version(self):
        store = self.make_store()
        self.assertEqual(S.SCHEMA_VERSION, int(store.connection.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0]))


if __name__ == "__main__":
    unittest.main()
