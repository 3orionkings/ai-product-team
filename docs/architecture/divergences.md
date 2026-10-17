# Divergences from the v0.1 design package

Each entry: what the spec says, what was built, why, and where it is recorded. Builder-level layout choices are recorded here without a stop for approval, per `06_IMPLEMENTATION_PLAN_AND_ACCEPTANCE.md` §1. Changes to the catalog or to protected authority rules would require owner review and none have been made.

| # | Spec | Built | Why |
|---|---|---|---|
| V01 | Architecture §6.2 lists separate relational tables `proposals`, `reviews`, `decisions`, `approvals`, `validations`, `challenges`. | One immutable `node_versions` table with a `kind` column and per-kind JSON Schema validation, plus SQL views named after each kind. | One versioning and edge mechanism for every record type; views keep the named query surface. Semantics (immutability, version binding, typed relations) are unchanged. |
| V02 | Architecture §6.2 lists an `installation_manifests` table. | The installer writes `.aipt/install-manifest.json` in the target project (as §4 also specifies) and keeps no database table. | A target project may have no case database yet; the manifest must exist independently of runtime state. |
| V03 | Workflow stage for W11 "Respond" names `proposal-owner [existing role]`. | `role_binding: runtime` in `registry/workflows.json`; the controller resolves it to the author role of the frozen proposal version. | Keeps the catalog at exactly 64 (FR-001). |
