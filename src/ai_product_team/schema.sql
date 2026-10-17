-- ai_product_team case store DDL (schema_version 1).
-- Loaded by storage.py via importlib.resources; executed once by CaseStore.create() and import_().
-- Rules it enforces structurally:
--   * node_versions and events are append-only: triggers RAISE(ABORT) on UPDATE and DELETE.
--   * node_current is the only mutable projection over node_versions.
--   * every record belongs to the single case of the store (cases.id).
-- Divergence V01: the per-kind record tables of the architecture are SQL views over node_versions.

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cases (
    id            TEXT PRIMARY KEY,
    payload       TEXT NOT NULL,                 -- JSON: objective, protected_constraints, source_scope, owner, roots ...
    state_version INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL
);

-- ---------------------------------------------------------------------------------------------
-- Operational tables (generic insert/update/get/query; unknown keys live in extra_json)
-- ---------------------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS runs (
    id             TEXT PRIMARY KEY,
    case_id        TEXT NOT NULL REFERENCES cases(id),
    workflow_id    TEXT,
    workflow_name  TEXT,
    mode           TEXT,
    state          TEXT,
    risk_tier      TEXT,
    host           TEXT,
    host_version   TEXT,
    package_version TEXT,
    execution_mode TEXT,
    started_at     TEXT,
    ended_at       TEXT,
    created_at     TEXT,
    budget         TEXT,                         -- JSON
    limitations    TEXT,                         -- JSON
    extra_json     TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS tasks (
    id            TEXT PRIMARY KEY,
    case_id       TEXT NOT NULL REFERENCES cases(id),
    run_id        TEXT,
    role_id       TEXT,
    stage_id      TEXT,
    state         TEXT,
    attempt       INTEGER,
    write_scope   TEXT,
    risk_tier     TEXT,
    created_at    TEXT,
    updated_at    TEXT,
    dependencies  TEXT,                          -- JSON
    input_refs    TEXT,                          -- JSON
    output_paths  TEXT,                          -- JSON
    snapshot      TEXT,                          -- JSON
    envelope      TEXT,                          -- JSON
    extra_json    TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_tasks_run_state ON tasks(run_id, state);

CREATE TABLE IF NOT EXISTS dispatches (
    id              TEXT PRIMARY KEY,
    case_id         TEXT NOT NULL REFERENCES cases(id),
    run_id          TEXT,
    task_id         TEXT,
    host            TEXT,
    native_child_id TEXT,
    execution_mode  TEXT,
    observed_by     TEXT,
    started_at      TEXT,
    ended_at        TEXT,
    created_at      TEXT,
    metadata        TEXT,                        -- JSON
    extra_json      TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_dispatches_task ON dispatches(task_id);

CREATE TABLE IF NOT EXISTS receipts (
    id                 TEXT PRIMARY KEY,
    case_id            TEXT NOT NULL REFERENCES cases(id),
    task_id            TEXT,
    exit_status        INTEGER,
    observation_source TEXT,
    started_at         TEXT,
    ended_at           TEXT,
    created_at         TEXT,
    payload            TEXT,                     -- JSON: the full validated receipt record
    extra_json         TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_receipts_task ON receipts(task_id);

CREATE TABLE IF NOT EXISTS impact_queue (
    id               TEXT PRIMARY KEY,
    case_id          TEXT NOT NULL REFERENCES cases(id),
    affected_version TEXT,
    changed_version  TEXT,
    impact_policy    TEXT,
    state            TEXT,
    reason           TEXT,
    created_at       TEXT,
    resolved_at      TEXT,
    path             TEXT,                       -- JSON
    extra_json       TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_impact_queue_state ON impact_queue(state);

CREATE TABLE IF NOT EXISTS budgets (
    id                   TEXT PRIMARY KEY,
    case_id              TEXT NOT NULL REFERENCES cases(id),
    run_id               TEXT,
    mode                 TEXT,
    max_worker_tasks     INTEGER,
    concurrent_workers   INTEGER,
    max_challenge_rounds INTEGER,
    used_tasks           INTEGER,
    running              INTEGER,
    used_rounds          INTEGER,
    wallclock_limit_s    INTEGER,
    created_at           TEXT,
    updated_at           TEXT,
    extra_json           TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_budgets_run ON budgets(run_id);

-- ---------------------------------------------------------------------------------------------
-- Versioned records
-- ---------------------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS nodes (
    id         TEXT PRIMARY KEY,
    case_id    TEXT NOT NULL REFERENCES cases(id),
    kind       TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_nodes_case_kind ON nodes(case_id, kind);

CREATE TABLE IF NOT EXISTS node_versions (
    id             TEXT PRIMARY KEY,
    node_id        TEXT NOT NULL REFERENCES nodes(id),
    seq            INTEGER NOT NULL,
    kind           TEXT NOT NULL,
    payload        TEXT NOT NULL,                -- canonical JSON validated against schemas/<kind>.schema.json
    content_hash   TEXT NOT NULL,                -- sha256 of the canonical payload
    author_role    TEXT NOT NULL,
    author_task    TEXT,
    author_session TEXT,
    created_at     TEXT NOT NULL,
    UNIQUE (node_id, seq)
);

CREATE TRIGGER IF NOT EXISTS trg_node_versions_no_update
BEFORE UPDATE ON node_versions
BEGIN
    SELECT RAISE(ABORT, 'node_versions is immutable: UPDATE refused');
END;

CREATE TRIGGER IF NOT EXISTS trg_node_versions_no_delete
BEFORE DELETE ON node_versions
BEGIN
    SELECT RAISE(ABORT, 'node_versions is immutable: DELETE refused');
END;

CREATE TABLE IF NOT EXISTS node_current (
    node_id       TEXT PRIMARY KEY REFERENCES nodes(id),
    version_id    TEXT NOT NULL REFERENCES node_versions(id),
    kind          TEXT NOT NULL,
    status        TEXT NOT NULL,
    applicability TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_node_current_kind ON node_current(kind, status);

CREATE TABLE IF NOT EXISTS edges (
    id                TEXT PRIMARY KEY,
    case_id           TEXT NOT NULL REFERENCES cases(id),
    from_version      TEXT NOT NULL REFERENCES node_versions(id),
    to_version        TEXT NOT NULL REFERENCES node_versions(id),
    relation          TEXT NOT NULL,
    impact_policy     TEXT,
    reason            TEXT NOT NULL,
    proposed_by       TEXT NOT NULL,
    status            TEXT NOT NULL,
    created_at        TEXT NOT NULL,
    status_changed_by TEXT,
    status_changed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_edges_to   ON edges(to_version, relation, status);
CREATE INDEX IF NOT EXISTS idx_edges_from ON edges(from_version, relation, status);

-- ---------------------------------------------------------------------------------------------
-- Events: immutable sequence per case; idempotency_key deduplicates replays
-- ---------------------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS events (
    id                     TEXT PRIMARY KEY,
    case_id                TEXT NOT NULL REFERENCES cases(id),
    seq                    INTEGER NOT NULL,
    type                   TEXT NOT NULL,
    actor_role             TEXT NOT NULL,
    actor_task             TEXT,
    expected_state_version INTEGER NOT NULL,
    payload_refs           TEXT NOT NULL,        -- JSON array of ids
    payload                TEXT NOT NULL,        -- canonical JSON object
    payload_sha256         TEXT NOT NULL,
    created_at             TEXT NOT NULL,
    idempotency_key        TEXT NOT NULL,
    UNIQUE (case_id, seq)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_events_idempotency ON events(idempotency_key);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(case_id, type);

CREATE TRIGGER IF NOT EXISTS trg_events_no_update
BEFORE UPDATE ON events
BEGIN
    SELECT RAISE(ABORT, 'events are immutable: UPDATE refused');
END;

CREATE TRIGGER IF NOT EXISTS trg_events_no_delete
BEFORE DELETE ON events
BEGIN
    SELECT RAISE(ABORT, 'events are immutable: DELETE refused');
END;

-- ---------------------------------------------------------------------------------------------
-- Per-kind views over node_versions JOIN node_current (divergence V01)
-- ---------------------------------------------------------------------------------------------

CREATE VIEW IF NOT EXISTS proposals AS
    SELECT n.case_id, c.node_id, c.version_id, c.status, c.applicability, v.seq, v.payload, v.content_hash,
           v.author_role, v.author_task, v.author_session, v.created_at
    FROM node_versions v JOIN node_current c ON c.version_id = v.id JOIN nodes n ON n.id = v.node_id
    WHERE v.kind = 'proposal';

CREATE VIEW IF NOT EXISTS reviews AS
    SELECT n.case_id, c.node_id, c.version_id, c.status, c.applicability, v.seq, v.payload, v.content_hash,
           v.author_role, v.author_task, v.author_session, v.created_at
    FROM node_versions v JOIN node_current c ON c.version_id = v.id JOIN nodes n ON n.id = v.node_id
    WHERE v.kind = 'review';

CREATE VIEW IF NOT EXISTS decisions AS
    SELECT n.case_id, c.node_id, c.version_id, c.status, c.applicability, v.seq, v.payload, v.content_hash,
           v.author_role, v.author_task, v.author_session, v.created_at
    FROM node_versions v JOIN node_current c ON c.version_id = v.id JOIN nodes n ON n.id = v.node_id
    WHERE v.kind = 'decision';

CREATE VIEW IF NOT EXISTS approvals AS
    SELECT n.case_id, c.node_id, c.version_id, c.status, c.applicability, v.seq, v.payload, v.content_hash,
           v.author_role, v.author_task, v.author_session, v.created_at
    FROM node_versions v JOIN node_current c ON c.version_id = v.id JOIN nodes n ON n.id = v.node_id
    WHERE v.kind = 'approval';

CREATE VIEW IF NOT EXISTS validations AS
    SELECT n.case_id, c.node_id, c.version_id, c.status, c.applicability, v.seq, v.payload, v.content_hash,
           v.author_role, v.author_task, v.author_session, v.created_at
    FROM node_versions v JOIN node_current c ON c.version_id = v.id JOIN nodes n ON n.id = v.node_id
    WHERE v.kind = 'validation';

CREATE VIEW IF NOT EXISTS challenges AS
    SELECT n.case_id, c.node_id, c.version_id, c.status, c.applicability, v.seq, v.payload, v.content_hash,
           v.author_role, v.author_task, v.author_session, v.created_at
    FROM node_versions v JOIN node_current c ON c.version_id = v.id JOIN nodes n ON n.id = v.node_id
    WHERE v.kind = 'challenge';

CREATE VIEW IF NOT EXISTS claims AS
    SELECT n.case_id, c.node_id, c.version_id, c.status, c.applicability, v.seq, v.payload, v.content_hash,
           v.author_role, v.author_task, v.author_session, v.created_at
    FROM node_versions v JOIN node_current c ON c.version_id = v.id JOIN nodes n ON n.id = v.node_id
    WHERE v.kind = 'claim';

CREATE VIEW IF NOT EXISTS requirements AS
    SELECT n.case_id, c.node_id, c.version_id, c.status, c.applicability, v.seq, v.payload, v.content_hash,
           v.author_role, v.author_task, v.author_session, v.created_at
    FROM node_versions v JOIN node_current c ON c.version_id = v.id JOIN nodes n ON n.id = v.node_id
    WHERE v.kind = 'requirement';

CREATE VIEW IF NOT EXISTS sources AS
    SELECT n.case_id, c.node_id, c.version_id, c.status, c.applicability, v.seq, v.payload, v.content_hash,
           v.author_role, v.author_task, v.author_session, v.created_at
    FROM node_versions v JOIN node_current c ON c.version_id = v.id JOIN nodes n ON n.id = v.node_id
    WHERE v.kind = 'source';

CREATE VIEW IF NOT EXISTS artifacts AS
    SELECT n.case_id, c.node_id, c.version_id, c.status, c.applicability, v.seq, v.payload, v.content_hash,
           v.author_role, v.author_task, v.author_session, v.created_at
    FROM node_versions v JOIN node_current c ON c.version_id = v.id JOIN nodes n ON n.id = v.node_id
    WHERE v.kind = 'artifact';
